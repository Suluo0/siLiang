"""
Auth API — 注册 / 登录 / 续期 / 个人信息 / 改密
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator

from src.auth.jwt import create_tokens, decode_token
from src.auth.hash import hash_password, verify_password
from src.auth.deps import get_current_active_user
from src.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response Models ──

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("用户名至少 2 个字符")
        return v.strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("新密码至少 6 位")
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
    created_at: str | None
    topic_credits: int = 0
    agent_credits: int = 0


# ── Endpoints ──

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """注册——直接签发 token（邮箱验证暂时跳过）"""
    existing = await User.filter(email=req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="邮箱已注册")

    existing_name = await User.filter(username=req.username).first()
    if existing_name:
        raise HTTPException(status_code=409, detail="用户名已被使用")

    user = await User.create(
        id=str(uuid.uuid4()),
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        token_version=0,
    )

    # 创建配额: 20 题 + 5 次对话
    from src.models.user_quota import UserQuota
    await UserQuota.create(id=str(uuid.uuid4()), user=user,
                           topic_credits=20, agent_credits=5)

    tokens = create_tokens(str(user.id), user.token_version)
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """登录——邮箱 + 密码 → JWT token pair"""
    user = await User.filter(email=req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    user.last_login = datetime.now(timezone.utc)
    await user.save()

    tokens = create_tokens(str(user.id), user.token_version)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    """用 refresh_token 换新的 access_token"""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的 refresh token")

    user = await User.filter(id=payload["sub"], is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    if user.token_version != payload.get("ver", 0):
        raise HTTPException(status_code=401, detail="Token 版本不匹配")

    tokens = create_tokens(str(user.id), user.token_version)
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_active_user)):
    """获取当前用户信息 + 配额"""
    from src.models.user_quota import UserQuota
    quota = await UserQuota.filter(user=user).first()
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        topic_credits=quota.topic_credits if quota else 0,
        agent_credits=quota.agent_credits if quota else 0,
    )


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest,
                          user: User = Depends(get_current_active_user)):
    """修改密码——旧密码验证 → 更新 hash + token_version（所有旧 token 失效）"""
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    user.password_hash = hash_password(req.new_password)
    user.token_version += 1
    await user.save()

    return {"message": "密码已修改，所有旧 token 已失效"}
