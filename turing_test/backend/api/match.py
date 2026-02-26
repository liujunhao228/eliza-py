"""
匹配 API 路由（简化版）

处理用户匹配相关功能。
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from loguru import logger

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    MatchingStatusResponse,
    SuccessResponse,
    MatchResponse,
)
from turing_test.backend.services.match_service import get_match_service

router = APIRouter()


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

    流程：
    1. 将用户加入队列
    2. 20% 概率直接分配 AI（对照组）
    3. 80% 概率尝试匹配真人
    4. 匹配结果暂存，前端固定等待 3 秒后调用 /result 获取
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

    # 获取匹配服务
    from turing_test.backend.services.match_service import get_match_service
    match_service = get_match_service()

    # 检查用户是否已在队列中
    if match_service.is_user_waiting(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已在匹配队列中"
        )

    # 获取 WebSocket 引用（用于后续推送，简化版暂不使用）
    from turing_test.backend.websocket.manager import manager
    websocket = manager.get_user_websocket(user_id)
    websocket_ref = id(websocket) if websocket else 0

    # 加入队列（内部会立即尝试匹配）
    await match_service.add_to_queue(user_id, websocket_ref, user.score)

    logger.info(f"用户 {user_id} 已加入匹配队列")

    # 返回响应（session_id 初始为 0，前端需调用 /result 获取真实结果）
    return MatchResponse(
        session_id=0,
        opponent_type="waiting",
        is_honeypot=False,
    )


@router.get(
    "/result",
    response_model=MatchResponse,
    summary="获取匹配结果",
    description="获取匹配结果（前端固定等待 3 秒后调用）",
)
async def get_match_result(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    获取匹配结果

    前端在加入队列后固定等待 3 秒，然后调用此接口获取匹配结果。
    如果用户仍在等待队列中（无真人匹配），则自动分配 AI 对手。
    """
    match_service = get_match_service()

    # 先检查是否已有匹配结果
    result = await match_service.get_result(user_id)

    if result:
        # 清除暂存结果
        await match_service.clear_result(user_id)
        return MatchResponse(
            session_id=result["session_id"],
            opponent_type=result["opponent_type"],
            is_honeypot=result["is_honeypot"],
        )

    # 如果用户仍在等待队列中，超时后自动分配 AI
    if match_service.is_user_waiting(user_id):
        logger.info(f"用户 {user_id} 匹配超时，自动分配 AI 对手")

        # 从队列中移除（先获取 websocket 引用和积分）
        from turing_test.backend.websocket.manager import manager
        websocket = manager.get_user_websocket(user_id)
        websocket_ref = id(websocket) if websocket else 0

        # 从数据库获取用户积分
        from turing_test.backend.models import User
        db_result = await db.execute(select(User).where(User.id == user_id))
        user = db_result.scalar_one_or_none()
        user_score = user.score if user else 100

        # 从队列中移除
        await match_service.remove_from_queue(user_id)

        # 分配 AI 对手（在锁外调用，避免死锁）
        await match_service._assign_ai(user_id, websocket_ref, user_score)

        # 获取结果
        result = await match_service.get_result(user_id)
        if result:
            await match_service.clear_result(user_id)
            return MatchResponse(
                session_id=result["session_id"],
                opponent_type=result["opponent_type"],
                is_honeypot=result["is_honeypot"],
            )

    # 如果用户既不在结果中也不在队列中，说明未加入匹配
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="请先加入匹配队列"
    )


@router.get(
    "/status",
    response_model=MatchingStatusResponse,
    summary="获取匹配状态",
    description="获取当前用户的匹配状态",
)
async def get_matching_status(user_id: int = Query(...)):
    """获取匹配状态"""
    match_service = get_match_service()
    
    in_queue = match_service.is_user_waiting(user_id)
    
    return MatchingStatusResponse(
        in_queue=in_queue,
        queue_position=1 if in_queue else None,
        estimated_wait_time=3 if in_queue else None,  # 固定 3 秒
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
    """离开匹配队列"""
    match_service = get_match_service()
    
    await match_service.remove_from_queue(user_id)
    
    return SuccessResponse(message="已离开匹配队列")


@router.get(
    "/statistics",
    summary="获取匹配统计",
    description="获取匹配服务的统计信息（仅管理员）",
)
async def get_match_statistics():
    """获取匹配统计信息"""
    match_service = get_match_service()
    stats = match_service.get_statistics()
    
    return stats
