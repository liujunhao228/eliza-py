"""
匹配 API 路由

处理用户匹配相关功能。

注意：实际匹配逻辑需要通过 WebSocket 实现，
这里仅提供基础 API 结构。
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from pydantic import BaseModel

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    MatchingStatusResponse,
    SuccessResponse,
)
from config import settings

router = APIRouter()


# =============================================================================
# 响应模型
# =============================================================================

class MatchStatisticsResponse(BaseModel):
    """匹配统计响应"""
    waiting_count: int
    active_match_tasks: int
    connected_users: int
    match_statistics: dict


# =============================================================================
# 全局匹配队列（简化版，实际应使用 Redis 或其他消息队列）
# =============================================================================

# 注意：这是简化版实现，实际应用中应使用 Redis
# 或专门的消息队列系统来管理匹配队列
matching_queue = []


# =============================================================================
# 路由
# =============================================================================

@router.get(
    "/status",
    response_model=MatchingStatusResponse,
    summary="获取匹配状态",
    description="获取当前用户的匹配状态",
)
async def get_matching_status(user_id: int = Query(...)):
    """
    获取匹配状态

    TODO: 实现真实的匹配状态查询
    """
    # 简化版：假设用户不在队列中
    return MatchingStatusResponse(
        in_queue=False,
        queue_position=None,
        estimated_wait_time=None,
    )


@router.post(
    "/join",
    response_model=SuccessResponse,
    summary="加入匹配队列",
    description="将用户加入匹配队列，等待匹配对手",
)
async def join_match_queue(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    加入匹配队列

    TODO: 实现真实的匹配队列逻辑
    """
    # 检查用户是否存在
    from turing_test.backend.models import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # TODO: 将用户加入匹配队列
    # matching_queue.append({
    #     "user_id": user_id,
    #     "joined_at": datetime.utcnow(),
    # })

    return SuccessResponse(message="已加入匹配队列")


@router.post(
    "/leave",
    response_model=SuccessResponse,
    summary="离开匹配队列",
    description="将用户从匹配队列中移除",
)
async def leave_match_queue(
    user_id: int = Query(...),
):
    """
    离开匹配队列

    TODO: 实现真实的离开队列逻辑
    """
    # TODO: 从匹配队列中移除用户
    # matching_queue = [u for u in matching_queue if u["user_id"] != user_id]

    return SuccessResponse(message="已离开匹配队列")


@router.get(
    "/statistics",
    response_model=MatchStatisticsResponse,
    summary="获取匹配统计",
    description="获取匹配服务的统计信息（仅管理员）",
)
async def get_match_statistics():
    """
    获取匹配统计信息

    返回：
    - 当前等待人数
    - 活跃匹配任务数
    - 连接用户数
    - 匹配统计（总匹配数、真人匹配数、AI 匹配数、平均等待时间等）
    """
    from turing_test.backend.services.match_service import get_match_service
    
    match_service = get_match_service()
    stats = match_service.get_statistics()
    
    return MatchStatisticsResponse(**stats)
