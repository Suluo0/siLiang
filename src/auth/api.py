"""
Auth API — 注册 / 登录 / 续期 / 改密 / CAPTCHA / 邮箱验证
"""
import uuid
import re
import base64
import hashlib
import io
import logging
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.auth.jwt import create_tokens, decode_token
from src.auth.hash import hash_password_async, verify_password_async
from src.models.user import User
from src.models.captcha import Captcha, hash_verification_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response ──

class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_answer: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    captcha_id: str
    captcha_answer: str
    email_code: str

    @field_validator("password")
    @classmethod
    def pw(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'\d', v):
            raise ValueError("密码需包含字母和数字")
        return v

    @field_validator("username")
    @classmethod
    def uname(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 6:
            raise ValueError("用户名至少 6 个字符")
        if not v[0].isalpha():
            raise ValueError("用户名必须以字母开头")
        return v

    @field_validator("email")
    @classmethod
    def em(cls, v: str) -> str:
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v.strip()):
            raise ValueError("邮箱格式不正确")
        return v.strip()


class SendCodeRequest(BaseModel):
    email: str
    captcha_id: str
    captcha_answer: str

    @field_validator("email")
    @classmethod
    def em(cls, v: str) -> str:
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v.strip()):
            raise ValueError("邮箱格式不正确")
        return v.strip()


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def pw(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("新密码至少 8 位")
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'\d', v):
            raise ValueError("新密码需包含字母和数字")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool = False
    email_verified: bool = False
    created_at: str | None
    topic_credits: int = 0
    agent_credits: int = 0
    target_position: str | None = None
    learning_preference: str | None = None
    experience_level: str | None = None
    today_target: int = 0


# ── 工具 ──

async def _verify_captcha(captcha_id: str, answer: str) -> Captcha:
    from datetime import timedelta
    from tortoise.expressions import F

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    digest = hash_verification_code(answer, "captcha")
    updated = await Captcha.filter(
        id=captcha_id, purpose="captcha", used=False,
        created_at__gte=cutoff, code_hash=digest, attempts__lt=5,
    ).update(used=True)
    if updated != 1:
        await Captcha.filter(id=captcha_id, used=False).update(attempts=F("attempts") + 1)
        raise HTTPException(status_code=400, detail="验证码无效或已过期")
    return await Captcha.get(id=captcha_id)


async def _consume_email_code(email: str, code: str) -> None:
    from datetime import timedelta

    target = email.strip().lower()
    digest = hash_verification_code(code, "email", target)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    challenge = await Captcha.filter(
        purpose="email", target=target, code_hash=digest,
        used=False, created_at__gte=cutoff,
    ).order_by("-created_at").first()
    if not challenge or await Captcha.filter(id=challenge.id, used=False).update(used=True) != 1:
        raise HTTPException(status_code=400, detail="邮箱验证码无效或已过期")


async def _login_user(user: User) -> TokenResponse:
    await User.filter(id=user.id).update(last_login=datetime.now(timezone.utc))
    tokens = create_tokens(str(user.id), user.token_version)
    return TokenResponse(**tokens)


# ═══════════════════════════════════════
#  CAPTCHA — 4 位数字
# ═══════════════════════════════════════

@router.get("/captcha")
async def get_captcha():
    code = "".join(secrets.choice("0123456789") for _ in range(4))
    c = await Captcha.issue(id=str(uuid.uuid4()), code=code)
    return {"captcha_id": str(c.id), "captcha_image": _generate_captcha_image(code)}


# ═══════════════════════════════════════
#  登录 — 用户名 + 密码 + CAPTCHA
# ═══════════════════════════════════════

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request):
    await _verify_captcha(req.captcha_id, req.captcha_answer)

    from datetime import timedelta
    target = hashlib.sha256(
        f"{request.client.host if request.client else 'unknown'}:{req.username.lower()}".encode()
    ).hexdigest()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    if await Captcha.filter(purpose="login_attempt", target=target, created_at__gte=cutoff).count() >= 5:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁")
    await Captcha.issue(
        id=str(uuid.uuid4()), code=secrets.token_hex(16),
        purpose="login_attempt", target=target,
    )

    user = await User.filter(username=req.username).first()
    if not user or not await verify_password_async(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    # 新设备登录 → token_version + 1 → 旧设备 token 失效
    from tortoise.expressions import F
    await User.filter(id=user.id).update(token_version=F("token_version") + 1)
    user.token_version += 1
    return await _login_user(user)


# ═══════════════════════════════════════
#  发送邮箱验证码
# ═══════════════════════════════════════

@router.post("/send-code")
async def send_verification_code(req: SendCodeRequest):
    await _verify_captcha(req.captcha_id, req.captcha_answer)

    from datetime import timedelta
    target = req.email.strip().lower()
    now = datetime.now(timezone.utc)
    recent = Captcha.filter(purpose="email", target=target)
    if await recent.filter(created_at__gte=now - timedelta(minutes=1)).exists():
        raise HTTPException(status_code=429, detail="验证码发送过于频繁")
    if await recent.filter(created_at__gte=now - timedelta(days=1)).count() >= 10:
        raise HTTPException(status_code=429, detail="今日验证码发送次数已用尽")
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    await Captcha.issue(id=str(uuid.uuid4()), code=code, purpose="email", target=target)

    await _send_email(req.email, code)
    return {"message": "验证码已发送，5 分钟内有效"}


# ═══════════════════════════════════════
#  注册 — CAPTCHA + 邮箱验证码
# ═══════════════════════════════════════

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    # 1. 图形验证码
    await _verify_captcha(req.captcha_id, req.captcha_answer)

    # 2. 邮箱码必须绑定当前注册邮箱，并原子消费。
    await _consume_email_code(req.email, req.email_code)

    # 3. 去重
    if await User.filter(email=req.email).exists():
        raise HTTPException(status_code=409, detail="邮箱已注册")
    if await User.filter(username=req.username).exists():
        raise HTTPException(status_code=409, detail="用户名已被使用")

    # 4. 创建
    user = await User.create(
        id=str(uuid.uuid4()), username=req.username, email=req.email,
        password_hash=await hash_password_async(req.password), token_version=0,
    )

    from src.models.user_quota import UserQuota
    await UserQuota.create(id=str(uuid.uuid4()), user=user,
                           topic_credits=20, agent_credits=5)
    return await _login_user(user)


# ═══════════════════════════════════════
#  Refresh / Me / ChangePassword
# ═══════════════════════════════════════

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    payload = decode_token(req.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="无效的 refresh token")
    user = await User.filter(id=payload["sub"], is_active=True).first()
    if not user or user.token_version != payload.get("ver", 0):
        raise HTTPException(status_code=401, detail="Token 已失效")
    return await _login_user(user)


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request):
    """获取当前用户（中间件已鉴权）"""
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="未登录")
    user = await User.filter(id=uid).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    from src.models.user_quota import UserQuota
    quota = await UserQuota.filter(user=user).first()
    return UserResponse(
        id=str(user.id), username=user.username, email=user.email,
        is_active=user.is_active, is_admin=user.is_superuser,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat() if user.created_at else None,
        topic_credits=quota.topic_credits if quota else 0,
        agent_credits=quota.agent_credits if quota else 0,
        target_position=user.target_position,
        learning_preference=user.learning_preference,
        experience_level=user.experience_level,
        today_target=user.today_target or 0,
    )


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, request: Request):
    """修改密码（中间件已鉴权）"""
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="未登录")
    user = await User.filter(id=uid).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not await verify_password_async(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    from tortoise.expressions import F
    await User.filter(id=user.id).update(
        password_hash=await hash_password_async(req.new_password),
        token_version=F("token_version") + 1,
    )
    return {"message": "密码已修改"}


@router.post("/preferences")
async def update_preferences(request: Request = None):
    """更新用户偏好"""
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401)
    body = await request.json()
    user = await User.filter(id=uid).first()
    if not user:
        raise HTTPException(status_code=404)
    for field in ("target_position", "learning_preference", "experience_level", "today_target"):
        if field in body:
            if field == "today_target":
                setattr(user, field, int(body[field]))
            else:
                setattr(user, field, body[field])
    user.preferences_filled = True
    await user.save()
    return {"target_position": user.target_position,
            "learning_preference": user.learning_preference,
            "experience_level": user.experience_level,
            "today_target": user.today_target}


# ═══════════════════════════════════════
#  邮件
# ═══════════════════════════════════════

async def _send_email(to: str, code: str):
    from src.utils.mail import send_async
    await send_async(to, "TopicSystem 邮箱验证", f"您的 TopicSystem 验证码: {code}，5 分钟有效。")
    logger.debug("verification email dispatched to %s", to)


def _generate_captcha_image(code: str) -> str:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 120, 40
    image = Image.new("RGB", (width, height), color=(242, 246, 252))
    draw = ImageDraw.Draw(image)
    for _ in range(8):
        draw.line(
            [(secrets.randbelow(width), secrets.randbelow(height)),
             (secrets.randbelow(width), secrets.randbelow(height))],
            fill=(120 + secrets.randbelow(80), 120 + secrets.randbelow(80), 120 + secrets.randbelow(80)),
        )
    font = ImageFont.load_default(size=24)
    for index, char in enumerate(code):
        draw.text((10 + index * 27, 6), char, font=font, fill=(20, 50, 90))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
