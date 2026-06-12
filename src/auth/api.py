"""
Auth API — 注册 / 登录 / 续期 / 改密 / CAPTCHA / 邮箱验证
"""
import uuid, random, re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.auth.jwt import create_tokens, decode_token
from src.auth.hash import hash_password, verify_password
from src.models.user import User
from src.models.captcha import Captcha

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
    c = await Captcha.filter(id=captcha_id).first()
    if not c:
        raise HTTPException(status_code=400, detail="验证码不存在")
    if c.used:
        raise HTTPException(status_code=400, detail="验证码已被使用")
    if c.is_expired():
        raise HTTPException(status_code=400, detail="验证码已过期")
    if c.code != answer.strip():
        raise HTTPException(status_code=400, detail="验证码错误")
    c.used = True
    await c.save()
    return c


async def _login_user(user: User) -> TokenResponse:
    user.last_login = datetime.now(timezone.utc)
    await user.save()
    tokens = create_tokens(str(user.id), user.token_version)
    return TokenResponse(**tokens)


# ═══════════════════════════════════════
#  CAPTCHA — 4 位数字
# ═══════════════════════════════════════

@router.get("/captcha")
async def get_captcha():
    code = f"{random.randint(0, 9999):04d}"
    c = await Captcha.create(id=str(uuid.uuid4()), code=code)
    return {"captcha_id": str(c.id), "captcha_text": code}


# ═══════════════════════════════════════
#  登录 — 用户名 + 密码 + CAPTCHA
# ═══════════════════════════════════════

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    await _verify_captcha(req.captcha_id, req.captcha_answer)

    user = await User.filter(username=req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    # 新设备登录 → token_version + 1 → 旧设备 token 失效
    user.token_version += 1
    await user.save()
    return await _login_user(user)


# ═══════════════════════════════════════
#  发送邮箱验证码
# ═══════════════════════════════════════

@router.post("/send-code")
async def send_verification_code(req: SendCodeRequest):
    await _verify_captcha(req.captcha_id, req.captcha_answer)

    code = f"{random.randint(100000, 999999)}"
    # 存入 Captcha 表，等注册时校验
    await Captcha.create(id=str(uuid.uuid4()), code=code)

    await _send_email(req.email, code)
    return {"message": "验证码已发送，5 分钟内有效"}


# ═══════════════════════════════════════
#  注册 — CAPTCHA + 邮箱验证码
# ═══════════════════════════════════════

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    # 1. 图形验证码
    await _verify_captcha(req.captcha_id, req.captcha_answer)

    # 2. 邮箱验证码（从 Captcha 表查最近未使用的）
    email_c = await Captcha.filter(code=req.email_code, used=False).order_by("-created_at").first()
    if not email_c:
        raise HTTPException(status_code=400, detail="邮箱验证码错误")
    if email_c.is_expired():
        raise HTTPException(status_code=400, detail="邮箱验证码已过期")
    email_c.used = True
    await email_c.save()

    # 3. 去重
    if await User.filter(email=req.email).exists():
        raise HTTPException(status_code=409, detail="邮箱已注册")
    if await User.filter(username=req.username).exists():
        raise HTTPException(status_code=409, detail="用户名已被使用")

    # 4. 创建
    user = await User.create(
        id=str(uuid.uuid4()), username=req.username, email=req.email,
        password_hash=hash_password(req.password), token_version=0,
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
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
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
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    user.password_hash = hash_password(req.new_password)
    user.token_version += 1
    await user.save()
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
    from src.utils.mail import send
    send(to, "TopicSystem 邮箱验证", f"您的 TopicSystem 验证码: {code}，5 分钟有效。")
    print(f"[CODE] {code} → {to}")
