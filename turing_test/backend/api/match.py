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
from loguru import logger

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    MatchingStatusResponse,
    SuccessResponse,
    MatchResponse,
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
# 路由
# =============================================================================

@router.post(
    "/join",
    response_model=MatchResponse,
    summary="加入匹配队列",
    description="将用户加入匹配队列，等待匹配对手",
)
async def join_match_queue(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    加入匹配队列

    将用户加入匹配队列，等待匹配对手。
    匹配成功后会通过 WebSocket 推送通知。

    注意：此端点需要配合 WebSocket 使用：
    1. 前端先建立 WebSocket 连接到 /ws/match?user_id=xxx
    2. 然后调用此 API 加入队列
    3. 匹配结果通过 WebSocket 推送
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

    # 获取 WebSocket manager
    from turing_test.backend.websocket.manager import manager

    # 检查用户是否已连接 WebSocket
    if not manager.is_user_connected(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WebSocket 未连接，请先建立 WebSocket 连接到 /ws/match?user_id=" + str(user_id)
        )

    # 获取匹配服务
    from turing_test.backend.services.match_service import get_match_service
    match_service = get_match_service()

    # 检查用户是否已在队列中
    if match_service.is_user_waiting(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已在匹配队列中"
        )

    # 获取 WebSocket 引用
    websocket = manager.get_user_websocket(user_id)
    websocket_ref = id(websocket) if websocket else 0

    # 将用户加入匹配队列
    await match_service.add_to_queue(user_id, websocket_ref, user.score)

    # 启动匹配任务
    await match_service.start_match_task(user_id, websocket_ref)

    logger.info(f"用户 {user_id} 已加入匹配队列")

    # 返回匹配响应（注意：此时会话尚未创建，需要等待 WebSocket 推送）
    return MatchResponse(
        session_id=0,  # 会话 ID 将通过 WebSocket 推送
        opponent_type="waiting",
        is_honeypot=False,
    )


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
