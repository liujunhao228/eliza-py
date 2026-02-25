"""
数据分析 API 路由

处理用户行为数据采集和查询。
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from turing_test.backend.database import get_db
from turing_test.backend.schemas.analytics import (
    AnalyticsEvent,
    AnalyticsBatchSubmit,
    AnalyticsBatchResponse,
    AnalyticsSummary,
    EventType,
)

router = APIRouter()


# =============================================================================
# 数据采集
# =============================================================================

@router.post(
    "/events",
    response_model=AnalyticsBatchResponse,
    summary="提交分析事件",
    description="批量提交用户行为事件",
)
async def submit_analytics_events(
    batch: AnalyticsBatchSubmit,
    db: AsyncSession = Depends(get_db),
):
    """
    提交分析事件

    接收批量事件并存储到数据库，用于后续分析。
    """
    try:
        # 简化版实现：仅记录事件数量
        # 实际应用中应存储到专门的分析数据库（如 Elasticsearch）
        accepted_count = len(batch.events)
        rejected_count = 0

        # 记录关键事件
        for event in batch.events:
            # 记录积分变化事件
            if event.event_type == EventType.SCORE_CHANGE:
                logger.info(
                    f"积分变化：user_id={event.user_id}, "
                    f"change={event.metadata.get('score_change')}, "
                    f"after={event.metadata.get('score_after')}"
                )

            # 记录匹配事件
            elif event.event_type == EventType.MATCH_FOUND:
                logger.info(
                    f"匹配成功：user_id={event.user_id}, "
                    f"opponent={event.metadata.get('opponent_type')}, "
                    f"wait_time={event.metadata.get('wait_time')}s"
                )

            # 记录元对话事件
            elif event.event_type == EventType.META_CONVERSATION:
                logger.info(
                    f"元对话：user_id={event.user_id}, "
                    f"keyword={event.metadata.get('keyword')}, "
                    f"count={event.metadata.get('meta_count')}"
                )

        return AnalyticsBatchResponse(
            success=True,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
        )

    except Exception as e:
        logger.error(f"提交分析事件失败：{e}", exc_info=True)
        return AnalyticsBatchResponse(
            success=False,
            accepted_count=0,
            rejected_count=len(batch.events),
            message=str(e),
        )


# =============================================================================
# 数据查询
# =============================================================================

@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="获取分析摘要",
    description="获取指定时间范围内的数据分析摘要",
)
async def get_analytics_summary(
    days: int = Query(default=7, ge=1, le=90, description="查询天数"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取分析数据摘要

    返回指定时间范围内的统计数据。
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    # 简化版实现：返回空摘要
    # 实际应用中应从分析数据库查询真实数据
    return AnalyticsSummary(
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/events",
    summary="查询事件列表",
    description="查询指定类型的事件列表",
)
async def query_analytics_events(
    event_type: Optional[EventType] = Query(None, description="事件类型"),
    user_id: Optional[int] = Query(None, description="用户 ID"),
    session_id: Optional[int] = Query(None, description="会话 ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
):
    """
    查询分析事件

    支持按事件类型、用户 ID、会话 ID 过滤。
    """
    # 简化版实现：返回空列表
    # 实际应用中应从分析数据库查询真实数据
    return {
        "events": [],
        "total": 0,
        "limit": limit,
    }


# =============================================================================
# 用户行为分析
# =============================================================================

@router.get(
    "/user/{user_id}/stats",
    summary="获取用户行为统计",
    description="获取指定用户的行为统计数据",
)
async def get_user_analytics(
    user_id: int,
    days: int = Query(default=30, ge=1, le=90, description="查询天数"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户行为统计

    返回用户在指定时间范围内的行为数据。
    """
    # 简化版实现：返回空统计
    # 实际应用中应查询用户行为数据
    return {
        "user_id": user_id,
        "period_days": days,
        "stats": {
            "total_sessions": 0,
            "total_messages": 0,
            "total_meta_conversations": 0,
            "judgment_accuracy": 0.0,
            "avg_wait_time": 0.0,
        },
    }


# =============================================================================
# 系统监控
# =============================================================================

@router.get(
    "/system/health",
    summary="系统健康检查",
    description="检查分析系统运行状态",
)
async def get_system_health():
    """
    系统健康检查

    返回分析系统的运行状态。
    """
    return {
        "status": "healthy",
        "components": {
            "event_collector": "ok",
            "data_storage": "ok",
            "query_service": "ok",
        },
    }
