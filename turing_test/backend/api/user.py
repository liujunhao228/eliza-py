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


def _normalize_opponent_type(opponent_type: str) -> str:
    """
    规范化对手类型，将 honeypot 隐藏为 ai
    
    这是为了向用户隐藏钓鱼机器人的存在，用户只需知道对手是"AI"或"真人"即可
    """
    if opponent_type == "honeypot":
        return "ai"
    return opponent_type


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
            "opponent_type": _normalize_opponent_type(session.opponent_type),
            "is_honeypot": session.is_honeypot,
            "final_score": session.final_score,
            "turn_count": session.turn_count,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
        }
        for session in sessions
    ]


@router.get(
    "/{user_id}/profile",
    response_model=dict,
    summary="获取用户完整档案",
    description="获取用户的完整信息，包括基本信息、统计数据和积分历史",
)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取用户完整档案"""
    from turing_test.backend.models import User, UserStats, ScoreHistory, Session

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

    # 获取最近的积分历史（最近 10 条）
    result = await db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.user_id == user_id)
        .order_by(ScoreHistory.created_at.desc())
        .limit(10)
    )
    score_history = result.scalars().all()

    # 获取最近的会话历史（最近 10 条）
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.started_at.desc())
        .limit(10)
    )
    sessions = result.scalars().all()

    def _normalize_opponent_type(opponent_type: str) -> str:
        """规范化对手类型，将 honeypot 隐藏为 ai"""
        if opponent_type == "honeypot":
            return "ai"
        return opponent_type

    return {
        "user": UserResponse.model_validate(user),
        "stats": UserStatsResponse.model_validate(user_stats) if user_stats else None,
        "score_history": [
            ScoreHistoryResponse.model_validate(record)
            for record in score_history
        ],
        "history": [
            {
                "id": session.id,
                "opponent_type": _normalize_opponent_type(session.opponent_type),
                "turn_count": session.turn_count,
                "final_score": session.final_score,
                "is_correct": session.is_correct,
                "confidence_level": session.confidence_level,
                "started_at": session.started_at,
                "ended_at": session.ended_at,
                "has_share": False,  # 简化处理，不检查分享状态
                "meta_conversation_count": session.meta_conversation_count,
                "triggered_mid_game": session.triggered_mid_game,
            }
            for session in sessions
        ],
    }
