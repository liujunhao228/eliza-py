"""
认证 API 路由

处理用户登录、注册和邀请码验证。
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt, JWTError

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    UserLogin,
    UserRegister,
    UserResponse,
    UserLoginResponse,
    SuccessResponse,
)
from turing_test.backend.services.invite_code_service import get_invite_code_service, InviteCodeService
from turing_test.backend.services.login_attempt_service import get_login_attempt_service, LoginAttemptService
from config import settings

router = APIRouter()

# JWT 配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# JWT 密钥验证
# =============================================================================

def validate_secret_key(key: str) -> bool:
    """
    验证 JWT 密钥强度

    要求:
    - 长度 >= 32
    - 包含大写字母
    - 包含小写字母
    - 包含数字
    - 包含特殊字符

    Args:
        key: JWT 密钥

    Returns:
        验证是否通过

    Raises:
        ValueError: 密钥强度不足
    """
    if len(key) < 32:
        raise ValueError("SECRET_KEY 长度必须 >= 32 字符")
    if not any(c.isupper() for c in key):
        raise ValueError("SECRET_KEY 必须包含大写字母")
    if not any(c.islower() for c in key):
        raise ValueError("SECRET_KEY 必须包含小写字母")
    if not any(c.isdigit() for c in key):
        raise ValueError("SECRET_KEY 必须包含数字")
    if not any(not c.isalnum() for c in key):
        raise ValueError("SECRET_KEY 必须包含特殊字符")
    return True


# 应用启动时验证密钥强度
try:
    validate_secret_key(settings.turing.auth.secret_key)
except ValueError as e:
    import warnings
    warnings.warn(f"⚠️  {e}，请检查 SECRET_KEY 配置")


# =============================================================================
# 工具函数
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.turing.auth.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.turing.auth.secret_key,
        algorithm=settings.turing.auth.algorithm
    )
    return encoded_jwt


async def get_current_user_id(
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> Optional[int]:
    """
    从 httpOnly Cookie 获取当前用户 ID
    
    若未登录或 Token 无效，返回 None
    """
    if not access_token:
        return None
    
    try:
        payload = jwt.decode(
            access_token,
            settings.turing.auth.secret_key,
            algorithms=[settings.turing.auth.algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None


# =============================================================================
# 路由
# =============================================================================

@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="用户登录",
    description="使用昵称与密码登录账号",
)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
    login_service: LoginAttemptService = Depends(get_login_attempt_service),
    response: Response = None
):
    """
    用户登录

    使用昵称和密码验证用户身份，返回用户信息和 JWT token（通过 httpOnly Cookie 存储）
    """
    from turing_test.backend.models import User

    # 检查账户是否被锁定
    is_locked, remaining_seconds = await login_service.check_lockout(user_data.nickname)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"账户已锁定，请 {remaining_seconds // 60} 分钟后再试"
        )

    # 根据昵称查找用户
    result = await db.execute(
        select(User).where(User.nickname == user_data.nickname)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # 记录失败尝试
        await login_service.record_failed_login(user_data.nickname)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="昵称或密码错误"
        )

    # 验证密码
    if not pwd_context.verify(user_data.password, user.password_hash):
        # 记录失败尝试
        await login_service.record_failed_login(user_data.nickname)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="昵称或密码错误"
        )

    # 登录成功，重置尝试计数
    await login_service.record_successful_login(user_data.nickname)

    # 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # 创建访问 token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.turing.auth.access_token_expire_minutes)
    )

    # 通过 httpOnly Cookie 返回 token（安全存储，防止 XSS 攻击）
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,        # 禁止 JavaScript 访问，防止 XSS 窃取
        secure=settings.debug is False,  # 生产环境仅 HTTPS 传输
        samesite="lax",       # 防止 CSRF 攻击
        max_age=settings.turing.auth.access_token_expire_minutes * 60,  # 过期时间（秒）
        path="/api"           # 限制 Cookie 作用路径
    )

    return UserLoginResponse(
        id=user.id,
        nickname=user.nickname,
        score=user.score,
        invite_code=user.invite_code,
        access_token=access_token,  # 保留在响应体中用于兼容，前端应忽略
        token_type="bearer"
    )


@router.post(
    "/register",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="使用邀请码、昵称和密码注册新用户",
)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service),
    response: Response = None
):
    """用户注册"""
    from turing_test.backend.models import User, UserStats

    # 验证邀请码
    verification = await invite_code_service.verify(user_data.invite_code)
    if not verification["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification["message"]
        )

    # 检查邀请码是否已被使用（针对单次使用的邀请码）
    invite_code = verification["invite_code"]
    if invite_code.max_uses == 1 and invite_code.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已被使用"
        )

    # 检查昵称是否已被占用
    result = await db.execute(
        select(User).where(User.nickname == user_data.nickname)
    )
    existing_nickname = result.scalar_one_or_none()

    if existing_nickname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="昵称已被占用"
        )

    # 密码哈希加密
    password_hash = pwd_context.hash(user_data.password)

    # 创建新用户
    user = User(
        nickname=user_data.nickname,
        password_hash=password_hash,
        invite_code=user_data.invite_code,
        score=settings.turing.auth.initial_score,
        highest_score=settings.turing.auth.initial_score,
        lowest_score=settings.turing.auth.initial_score,
    )
    db.add(user)
    await db.flush()

    # 创建用户统计记录
    user_stats = UserStats(user_id=user.id)
    db.add(user_stats)

    # 使用邀请码
    use_result = await invite_code_service.use(user_data.invite_code, user.id)
    if not use_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=use_result["message"]
        )

    await db.commit()
    await db.refresh(user)

    # 创建访问 token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.turing.auth.access_token_expire_minutes)
    )

    # 通过 httpOnly Cookie 返回 token（安全存储，防止 XSS 攻击）
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,        # 禁止 JavaScript 访问，防止 XSS 窃取
        secure=settings.debug is False,  # 生产环境仅 HTTPS 传输
        samesite="lax",       # 防止 CSRF 攻击
        max_age=settings.turing.auth.access_token_expire_minutes * 60,  # 过期时间（秒）
        path="/api"           # 限制 Cookie 作用路径
    )

    return UserLoginResponse(
        id=user.id,
        nickname=user.nickname,
        score=user.score,
        invite_code=user.invite_code,
        access_token=access_token,  # 保留在响应体中用于兼容，前端应忽略
        token_type="bearer"
    )


@router.get(
    "/verify/{invite_code}",
    response_model=SuccessResponse,
    summary="验证邀请码",
    description="验证邀请码是否有效",
)
async def verify_code(
    invite_code: str,
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """验证邀请码"""
    verification = await invite_code_service.verify(invite_code)
    if verification["valid"]:
        return SuccessResponse(message=verification["message"])
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification["message"]
        )
