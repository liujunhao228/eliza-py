"""
历史会话 API

提供用户查看历史会话记录的功能。
注意：历史会话为完全只读，不允许删除或修改。
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from jose import jwt, JWTError

from turing_test.backend.database import get_db
from turing_test.backend.models import User, Session, SessionShare, Message
from turing_test.backend.schemas import (
    SessionListResponse,
    SessionListItem,
    SessionDetailResponse,
    SuccessResponse,
    SharedMessagesResponse,
    MessageResponse,
)
from config import settings
from loguru import logger

router = APIRouter()


# =============================================================================
# 工具函数
# =============================================================================

def _normalize_opponent_type(opponent_type: str) -> str:
    """
    规范化对手类型，将 honeypot 隐藏为 ai
    
    这是为了向用户隐藏钓鱼机器人的存在
    """
    if opponent_type == "honeypot":
        return "ai"
    return opponent_type


def now_utc() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


async def get_current_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> int:
    """
    从 Authorization header 获取当前用户 ID

    若未登录或 Token 无效，抛出 401
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
        )
    
    # 提取 token
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误，应为 Bearer {token}",
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.turing.auth.secret_key,
            algorithms=[settings.turing.auth.algorithm]
        )
        user_id = int(payload.get("sub", 0))
        if user_id == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 token",
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期或无效",
        )


async def is_admin_user(user_id: int, db: AsyncSession) -> bool:
    """检查用户是否为管理员"""
    # 简化实现：检查用户名是否为 admin
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return False
    # 这里可以根据实际需求修改管理员判断逻辑
    return user.nickname == "admin"


# =============================================================================
# 历史会话 API
# =============================================================================

@router.get(
    "/user/{user_id}/sessions",
    response_model=SessionListResponse,
    tags=["历史会话"],
    summary="获取用户会话列表",
    description="获取指定用户的会话列表（分页、过滤）。历史会话为只读，不支持删除。",
)
async def get_user_sessions(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    opponent_type: Optional[str] = None,
    is_correct: Optional[bool] = None,
    search: Optional[str] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户会话列表（分页、过滤）
    
    权限：仅本人或管理员可访问
    注意：历史会话为只读，不提供删除接口
    """
    # 权限校验
    if current_user_id != user_id:
        is_admin = await is_admin_user(current_user_id, db)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问其他用户的历史会话",
            )
    
    # 构建查询
    query = select(Session).where(Session.user_id == user_id)

    # 应用过滤
    if opponent_type:
        query = query.where(Session.opponent_type == opponent_type)
    if is_correct is not None:
        query = query.where(Session.is_correct == is_correct)
    
    # 应用搜索（按会话 ID）
    if search:
        # 尝试解析为整数
        try:
            search_id = int(search)
            query = query.where(Session.id == search_id)
        except ValueError:
            # 如果不是整数，返回空结果
            query = query.where(Session.id == -1)
    
    # 计算总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0
    
    # 分页和排序
    query = query.order_by(Session.started_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # 检查每个会话是否有有效分享
    session_ids = [s.id for s in sessions]
    if session_ids:
        shares_result = await db.execute(
            select(SessionShare.session_id).where(
                SessionShare.session_id.in_(session_ids),
                (SessionShare.expires_at.is_(None) | (SessionShare.expires_at > now_utc()))
            )
        )
        shared_session_ids = set(r[0] for r in shares_result.all())
    else:
        shared_session_ids = set()
    
    return SessionListResponse(
        items=[
            SessionListItem(
                id=s.id,
                opponent_type=_normalize_opponent_type(s.opponent_type),
                turn_count=s.turn_count,
                final_score=s.final_score,
                is_correct=s.is_correct,
                confidence_level=s.confidence_level,
                started_at=s.started_at,
                ended_at=s.ended_at,
                has_share=s.id in shared_session_ids,
            )
            for s in sessions
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get(
    "/session/{session_id}/detail",
    response_model=SessionDetailResponse,
    tags=["历史会话"],
    summary="获取会话详情",
    description="获取会话的详细信息，包括统计数据和积分明细。",
)
async def get_session_detail(
    session_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话详细信息
    
    权限：仅会话所有者或管理员可访问
    """
    # 获取会话
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    # 权限校验
    if session.user_id != current_user_id:
        is_admin = await is_admin_user(current_user_id, db)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此会话",
            )

    # 计算时长
    duration = None
    if session.started_at and session.ended_at:
        duration = int((session.ended_at - session.started_at).total_seconds())

    return SessionDetailResponse(
        id=session.id,
        opponent_type=_normalize_opponent_type(session.opponent_type),
        is_honeypot=session.is_honeypot,
        turn_count=session.turn_count,
        meta_conversation_count=session.meta_conversation_count,
        final_score=session.final_score,
        is_correct=session.is_correct,
        confidence_level=session.confidence_level,
        score_breakdown=session.score_breakdown,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_seconds=duration,
    )


@router.get(
    "/session/{session_id}/messages",
    response_model=SharedMessagesResponse,
    tags=["历史会话"],
    summary="获取会话消息",
    description="获取指定会话的完整聊天记录。",
)
async def get_session_messages(
    session_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话消息列表

    权限：仅会话所有者或管理员可访问
    """
    # 获取会话并校验权限
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    # 权限校验
    if session.user_id != current_user_id:
        is_admin = await is_admin_user(current_user_id, db)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此会话",
            )

    # 获取消息
    msg_result = await db.execute(
        select(Message).where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return SharedMessagesResponse(
        session_id=session.id,
        opponent_type=_normalize_opponent_type(session.opponent_type),
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                content=msg.content,
                is_meta_conversation=msg.is_meta_conversation,
                meta_keyword=msg.meta_keyword,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )
