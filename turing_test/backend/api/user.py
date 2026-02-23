"""
用户 API 路由

处理用户信息查询、统计和积分历史。
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    UserResponse,
    UserStatsResponse,
    ScoreHistoryResponse,
)
from config import settings

router = APIRouter()


# =============================================================================
# 路由
# =============================================================================

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户信息",
    description="根据用户 ID 获取用户基本信息",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取用户信息"""
    from turing_test.backend.models import User

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}/stats",
    response_model=UserStatsResponse,
    summary="获取用户统计",
    description="获取用户的详细统计数据",
)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取用户统计信息"""
    from turing_test.backend.models import User, UserStats

    # 检查用户是否存在
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 获取用户统计
    result = await db.execute(
        select(UserStats).where(UserStats.user_id == user_id)
    )
    user_stats = result.scalar_one_or_none()

    if user_stats is None:
        # 如果统计不存在，返回默认值
        return UserStatsResponse()

    return UserStatsResponse.model_validate(user_stats)


@router.get(
    "/{user_id}/score-history",
    response_model=List[ScoreHistoryResponse],
    summary="获取积分历史",
    description="获取用户的积分变化历史记录",
)
async def get_score_history(
    user_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """获取用户积分历史"""
    from turing_test.backend.models import User, ScoreHistory

    # 检查用户是否存在
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 获取积分历史
    result = await db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.user_id == user_id)
        .order_by(ScoreHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    score_history = result.scalars().all()

    return [
        ScoreHistoryResponse.model_validate(record)
        for record in score_history
    ]


@router.get(
    "/{user_id}/sessions",
    response_model=List[dict],
    summary="获取用户会话",
    description="获取用户的游戏会话记录",
)
async def get_user_sessions(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """获取用户会话记录"""
    from turing_test.backend.models import User, Session

    # 检查用户是否存在
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 获取会话记录
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()

    return [
        {
            "id": session.id,
            "opponent_type": session.opponent_type,
            "is_honeypot": session.is_honeypot,
            "final_score": session.final_score,
            "turn_count": session.turn_count,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
        }
        for session in sessions
    ]
