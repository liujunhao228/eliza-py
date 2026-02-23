"""
认证 API 路由

处理用户登录、注册和邀请码验证。
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt, JWTError

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    UserLogin,
    UserRegister,
    UserResponse,
    SuccessResponse,
)
from turing_test.backend.services.invite_code_service import get_invite_code_service, InviteCodeService
from config import settings

router = APIRouter()

# JWT 配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# 工具函数
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.turing.auth.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.turing.auth.secret_key,
        algorithm=settings.turing.auth.algorithm
    )
    return encoded_jwt


# =============================================================================
# 路由
# =============================================================================

@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="用户登录",
    description="使用邀请码登录或注册用户",
)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """
    用户登录/注册

    如果邀请码不存在，则创建新用户并返回
    如果邀请码已存在，则返回已有用户信息
    """
    from turing_test.backend.models import User, UserStats

    # 验证邀请码
    verification = await invite_code_service.verify(user_data.invite_code)
    if not verification["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification["message"]
        )

    # 查找用户
    result = await db.execute(
        select(User).where(User.invite_code == user_data.invite_code)
    )
    user = result.scalar_one_or_none()

    # 用户不存在，创建新用户
    if user is None:
        # 生成用户名
        username = f"用户{user_data.invite_code[:4]}"

        user = User(
            invite_code=user_data.invite_code,
            username=username,
            score=settings.turing.auth.initial_score,
            highest_score=settings.turing.auth.initial_score,
            lowest_score=settings.turing.auth.initial_score,
        )
        db.add(user)
        await db.flush()  # 获取 user.id

        # 创建用户统计记录
        user_stats = UserStats(user_id=user.id)
        db.add(user_stats)

        # 使用邀请码
        invite_code = verification["invite_code"]
        invite_code.current_uses += 1
        invite_code.used_by_user_id = user.id
        invite_code.used_at = datetime.utcnow()
        if invite_code.max_uses != -1 and invite_code.current_uses >= invite_code.max_uses:
            invite_code.is_used = True

        await db.commit()
        await db.refresh(user)

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    await db.commit()

    return UserResponse.model_validate(user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="使用邀请码和用户名注册新用户",
)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
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

    # 检查用户名是否已被占用
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_username = result.scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被占用"
        )

    # 创建新用户
    user = User(
        invite_code=user_data.invite_code,
        username=user_data.username,
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

    return UserResponse.model_validate(user)


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
