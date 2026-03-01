"""
匹配 API 路由（重构版）

概率分流匹配模式:
- 30% 真人匹配
- 70% Bot 匹配 (含 15% 钓鱼 Bot)
- 真人超时 10 秒降级为 Bot

安全设计:
- 前端仅返回 opponent_type="opponent"
- true_identity、bot_level、is_honeypot 仅后台记录
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from turing_test.backend.database import get_db
from turing_test.backend.schemas import (
    MatchingStatusResponse,
    SuccessResponse,
    MatchResponse,
    AdminMatchResponse,
)

router = APIRouter()


# =============================================================================
# 依赖注入
# =============================================================================

from turing_test.backend.services.match_service.di import MatchServiceDep


# =============================================================================
# 公共接口
# =============================================================================

@router.post(
    "/join",
    response_model=MatchResponse,
    summary="加入匹配队列（概率分流）",
    description="""
加入匹配队列，采用概率分流机制：
- 30% 概率匹配真人
- 70% 概率匹配 Bot (含 15% 钓鱼 Bot)
- 真人匹配超时 10 秒后降级为 Bot

⚠️ 返回结果已过滤敏感字段，前端无法得知对手真实身份

🔒 防重复请求：如果用户已有匹配结果，直接返回旧结果
""",
)
async def join_match_queue(
    user_id: int = Query(..., description="用户 ID", gt=0),
    db: AsyncSession = Depends(get_db),
    match_service: MatchServiceDep = None,
):
    """
    加入匹配队列（概率分流模式）

    流程：
    1. 检查用户是否存在
    2. 获取 WebSocket 引用（从 session state）
    3. 后台概率掷骰子决定匹配类型
    4. Bot 局：立即分配 Bot (从 Bot 池抽取 Lv.1/2/3)
    5. 钓鱼局：立即分配钓鱼 Bot (攻击型/可疑型)
    6. 真人局：尝试匹配真人，超时 10 秒降级为 Bot
    7. 创建会话并记录真实身份 (后台)
    8. 返回安全结果给前端
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

    try:
        # 获取 WebSocket 引用（从 session state 或其他来源）
        # TODO: 实现 WebSocket 引用获取逻辑
        websocket_ref = 0  # 占位符

        # 加入队列并匹配
        match_result = await match_service.join_queue(
            user_id=user_id,
            websocket_ref=websocket_ref,
            user_score=user.score if hasattr(user, 'score') else 100,
        )

        # 获取内部结果以记录日志（不包含敏感信息返回给前端）
        internal_result = await match_service.get_result_internal(user_id)
        if internal_result:
            logger.info(
                f"用户 {user_id} 匹配完成："
                f"session_id={internal_result.session_id}, "
                f"true_identity={internal_result.true_identity}"
            )

        # ✅ 仅返回安全字段
        return MatchResponse(
            session_id=match_result.session_id,
            opponent_type=match_result.opponent_type,
            match_duration_ms=match_result.match_duration_ms,
            message="匹配成功",
        )

    except ValueError as e:
        # 用户已在队列中或已有匹配结果
        logger.info(f"用户 {user_id} 重复请求：{e}")
        
        # 尝试返回已有结果（处理超时清理的竞态）
        existing_result = await match_service.get_result(user_id)
        if existing_result:
            logger.info(f"用户 {user_id} 重复请求，返回已有匹配结果")
            return MatchResponse(
                session_id=existing_result.session_id,
                opponent_type=existing_result.opponent_type,
                match_duration_ms=existing_result.match_duration_ms,
                message="使用已有匹配结果",
            )
        
        # 如果用户确实在队列中等待，返回冲突
        if "已在匹配队列中" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        
        # 其他 ValueError
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error(f"匹配失败：user_id={user_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="匹配失败，请稍后重试",
        )
    except Exception as e:
        logger.error(f"未知错误：user_id={user_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误",
        )


@router.get(
    "/status",
    response_model=MatchingStatusResponse,
    summary="获取匹配状态",
    description="获取匹配队列状态",
)
async def get_match_status(
    match_service: MatchServiceDep = None,
):
    """获取匹配状态"""
    stats = match_service.get_statistics()

    return MatchingStatusResponse(
        waiting_count=stats.waiting_count,
        estimated_wait_time=5 if stats.waiting_count > 0 else 30,
    )


@router.post(
    "/leave",
    response_model=SuccessResponse,
    summary="离开匹配队列",
    description="将用户从匹配队列中移除",
)
async def leave_match_queue(
    user_id: int = Query(..., description="用户 ID", gt=0),
    match_service: MatchServiceDep = None,
):
    """离开匹配队列"""
    success = await match_service.remove_from_queue(user_id)
    
    if success:
        logger.info(f"用户 {user_id} 离开等待队列")
        return SuccessResponse(message="已离开匹配队列")
    else:
        # 用户不在队列中，也视为成功（幂等性）
        return SuccessResponse(message="未在队列中找到用户")


@router.get(
    "/result",
    response_model=MatchResponse,
    summary="获取匹配结果",
    description="获取暂存的匹配结果",
)
async def get_match_result(
    user_id: int = Query(..., description="用户 ID", gt=0),
    match_service: MatchServiceDep = None,
):
    """获取匹配结果"""
    result = await match_service.get_result(user_id)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到匹配结果，请稍后重试",
        )
    
    return MatchResponse(
        session_id=result.session_id,
        opponent_type=result.opponent_type,
        match_duration_ms=result.match_duration_ms,
        message="匹配成功",
    )


# =============================================================================
# 管理员接口
# =============================================================================

@router.get(
    "/admin/session/{session_id}",
    response_model=AdminMatchResponse,
    summary="管理员查看会话详情",
    description="查看会话完整信息，包含真实身份等敏感字段",
)
async def get_session_admin(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    # TODO: 添加管理员认证
    # current_user: User = Depends(require_admin),
):
    """
    管理员查看会话详情

    ✅ 返回完整信息，包含：
    - true_identity: 真实身份
    - bot_level: Bot 等级
    - is_honeypot: 是否钓鱼
    """
    from turing_test.backend.models import Session

    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    return AdminMatchResponse(
        session_id=session.id,
        opponent_type=session.opponent_type,
        true_identity=session.true_identity,
        bot_level=session.bot_level,
        is_honeypot=session.is_honeypot,
        opponent_user_id=session.opponent_user_id,
        match_duration_ms=0,
        message="",
    )


@router.get(
    "/admin/stats",
    response_model=Dict[str, Any],
    summary="管理员查看匹配统计",
    description="查看匹配服务统计信息",
)
async def get_match_stats(
    match_service: MatchServiceDep = None,
):
    """获取匹配服务统计"""
    stats = match_service.get_statistics()
    internal_stats = match_service.get_internal_stats()
    
    bot_pool, honeypot_pool = match_service.get_bot_pools()

    return {
        "queue": {
            "waiting_count": stats.waiting_count,
            "human_waiting": stats.human_waiting,
            "timeout_seconds": stats.timeout_seconds,
        },
        "internal": internal_stats,
        "bot_pool": bot_pool.get_stats(),
        "honeypot_pool": honeypot_pool.get_stats(),
    }


# =============================================================================
# 健康检查接口
# =============================================================================

@router.get(
    "/health",
    summary="健康检查",
    description="检查匹配服务健康状态",
)
async def health_check(
    match_service: MatchServiceDep = None,
):
    """健康检查"""
    return {
        "status": "healthy",
        "queue_size": match_service.get_queue_size(),
        "running": match_service._running,
    }
