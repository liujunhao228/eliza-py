"""
游戏 API - 基于新领域模型

使用三层分离架构：
- Match (匹配层) → Room (对话层) → UserSession (用户会话层)

端点：
1. POST /session/{session_id}/end - 结束会话
2. GET /session/{session_id}/messages - 获取会话消息
3. GET /session/{session_id}/result - 获取会话结果
4. POST /survey - 提交问卷
5. POST /session/{room_id}/message - 发送消息
6. POST /session/{session_id}/judgment - 提交判断
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from pydantic import BaseModel, ConfigDict

from turing_test.backend.database import get_db
from turing_test.backend.schemas import SuccessResponse
from turing_test.backend.application.room_service import RoomApplicationService
from turing_test.backend.application.session_service import SessionApplicationService
from turing_test.backend.domain.repositories import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from turing_test.backend.domain.models import SessionStatus, RoomStatus
from turing_test.backend.models.domain_models import Message as MessageORM

router = APIRouter()


# =============================================================================
# Request/Response Schema
# =============================================================================

class EndSessionRequest(BaseModel):
    """结束会话请求"""
    end_reason: str = "user_gave_up"


class MessageRequest(BaseModel):
    """发送消息请求"""
    content: str


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    room_id: int
    sender_id: Optional[int]
    sender_type: str
    content: str
    is_meta: bool
    meta_keyword: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionMessagesResponse(BaseModel):
    """会话消息列表响应"""
    room_id: int
    turn_count: int
    meta_count: int
    messages: List[MessageResponse]


class JudgmentRequest(BaseModel):
    """提交判断请求"""
    user_guess: str  # "human" or "ai"
    confidence: str  # "low", "mid", "high"
    is_mid_game: bool = False


class ScoreBreakdownResponse(BaseModel):
    """积分明细响应"""
    final_score: int
    base_score: int
    confidence_multiplier: float
    meta_multiplier: float
    mid_game_multiplier: float
    entry_fee: int
    turn_penalty: int
    opponent_bonus: int


class SessionResultResponse(BaseModel):
    """会话结果响应"""
    session_id: int
    room_id: int
    user_id: int
    final_score: int
    score_settled: bool
    bonus_pending: bool
    bonus_claimed: bool
    score_breakdown: Optional[ScoreBreakdownResponse] = None


# =============================================================================
# 依赖注入
# =============================================================================

async def get_room_service(db: AsyncSession) -> RoomApplicationService:
    """获取 Room 应用服务"""
    uow = SqlAlchemyUnitOfWork(db)
    from turing_test.backend.infrastructure.events.event_bus import event_bus
    return RoomApplicationService(uow, event_bus)


async def get_session_service(db: AsyncSession) -> SessionApplicationService:
    """获取 Session 应用服务"""
    uow = SqlAlchemyUnitOfWork(db)
    from turing_test.backend.infrastructure.events.event_bus import event_bus
    return SessionApplicationService(uow, event_bus)


# =============================================================================
# 发送消息
# =============================================================================

@router.post(
    "/room/{room_id}/message",
    response_model=MessageResponse,
    summary="发送消息",
    description="在对话中发送消息",
)
async def send_message(
    room_id: int,
    request: MessageRequest,
    user_id: int,
    room_service: RoomApplicationService = Depends(get_room_service),
):
    """
    发送消息 API

    流程：
    1. 验证用户会话是否存在
    2. 检查是否为用户回合
    3. 发送消息到 Room
    4. 更新用户会话回合状态
    5. 返回消息
    """
    # 获取用户会话
    from turing_test.backend.database import async_session_maker
    from turing_test.backend.models.domain_models import UserSession as UserSessionORM
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserSessionORM).where(
                UserSessionORM.room_id == room_id,
                UserSessionORM.user_id == user_id,
            )
        )
        user_session = result.scalar_one_or_none()
        
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户会话不存在",
            )
        
        # 检查是否为用户回合
        if not user_session.is_user_turn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请等待对方发送消息",
            )
        
        # 检测元对话
        is_meta, meta_keyword = _detect_meta_conversation(request.content)
        
        # 发送消息
        message = await room_service.send_message(
            room_id=str(room_id),
            sender_id=user_id,
            sender_type="user",
            content=request.content.strip(),
            is_meta=is_meta,
            meta_keyword=meta_keyword if is_meta else None,
        )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="发送消息失败",
            )
        
        # 更新回合状态
        await room_service._session_service.update_turn(
            session_id=str(user_session.id),
            is_user_turn=False,
            increment_turn=True,
        )
        
        logger.info(f"用户发送消息：user_id={user_id}, room_id={room_id}")
        
        return MessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            sender_type=message.sender_type,
            content=message.content,
            is_meta=message.is_meta,
            meta_keyword=message.meta_keyword,
            created_at=message.created_at,
        )


# =============================================================================
# 结束会话
# =============================================================================

@router.post(
    "/session/{session_id}/end",
    response_model=SuccessResponse,
    summary="结束会话",
    description="用户主动结束当前会话",
)
async def end_session(
    session_id: int,
    request: EndSessionRequest,
    session_service: SessionApplicationService = Depends(get_session_service),
):
    """
    结束会话 API

    流程：
    1. 获取用户会话
    2. 结束会话
    3. 如果是真人对战，通知对方
    """
    # 获取会话
    session = await session_service.get_session(str(session_id))
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    
    if session.is_ended():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="会话已结束",
        )
    
    # 结束会话
    success = await session_service.end_session(
        session_id=str(session_id),
        end_reason=request.end_reason,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="结束会话失败",
        )
    
    # TODO: 如果是真人对战，通知对方
    
    logger.info(f"用户结束会话：session_id={session_id}, reason={request.end_reason}")
    
    return SuccessResponse(
        success=True,
        message="会话已结束，请完成问卷提交以结算积分",
    )


# =============================================================================
# 获取会话消息
# =============================================================================

@router.get(
    "/room/{room_id}/messages",
    response_model=SessionMessagesResponse,
    summary="获取对话消息",
    description="获取指定对话的所有历史消息",
)
async def get_room_messages(
    room_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取对话消息列表"""
    # 获取消息
    result = await db.execute(
        select(MessageORM)
        .where(MessageORM.room_id == room_id)
        .order_by(MessageORM.created_at.asc())
    )
    messages = result.scalars().all()
    
    if not messages:
        return SessionMessagesResponse(
            room_id=room_id,
            turn_count=0,
            meta_count=0,
            messages=[],
        )
    
    # 获取对话统计
    from turing_test.backend.models.domain_models import Room as RoomORM
    room_result = await db.execute(select(RoomORM).where(RoomORM.id == room_id))
    room = room_result.scalar_one_or_none()
    
    return SessionMessagesResponse(
        room_id=room_id,
        turn_count=room.total_turns if room else 0,
        meta_count=room.meta_count if room else 0,
        messages=[
            MessageResponse(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                sender_type=msg.sender_type,
                content=msg.content,
                is_meta=msg.is_meta,
                meta_keyword=msg.meta_keyword,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


# =============================================================================
# 提交判断
# =============================================================================

@router.post(
    "/session/{session_id}/judgment",
    response_model=SessionResultResponse,
    summary="提交判断",
    description="提交 AI/人类判断和信心等级",
)
async def submit_judgment(
    session_id: int,
    request: JudgmentRequest,
    session_service: SessionApplicationService = Depends(get_session_service),
):
    """
    提交判断 API

    流程：
    1. 验证会话存在
    2. 提交判断
    3. 返回会话状态
    """
    # 提交判断
    success = await session_service.submit_judgment(
        session_id=str(session_id),
        user_guess=request.user_guess,
        confidence=request.confidence,
        is_mid_game=request.is_mid_game,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交判断失败",
        )
    
    # 获取会话
    session = await session_service.get_session(str(session_id))
    
    return SessionResultResponse(
        session_id=int(session.id.value),
        room_id=int(session.room_id.value),
        user_id=session.user_id.value,
        final_score=session.final_score or 0,
        score_settled=session.score_settled,
        bonus_pending=session.bonus_pending,
        bonus_claimed=session.bonus_claimed,
    )


# =============================================================================
# 获取会话结果
# =============================================================================

@router.get(
    "/session/{session_id}/result",
    response_model=SessionResultResponse,
    summary="获取会话结果",
    description="获取会话的最终结果和积分明细",
)
async def get_session_result(
    session_id: int,
    session_service: SessionApplicationService = Depends(get_session_service),
):
    """获取会话完整结果"""
    # 获取会话
    session = await session_service.get_session(str(session_id))
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    
    # 获取积分
    score = session.score
    
    score_breakdown = None
    if score:
        score_breakdown = ScoreBreakdownResponse(
            final_score=score.breakdown.final_score,
            base_score=score.breakdown.base_score,
            confidence_multiplier=score.breakdown.confidence_multiplier,
            meta_multiplier=score.breakdown.meta_multiplier,
            mid_game_multiplier=score.breakdown.mid_game_multiplier,
            entry_fee=score.breakdown.entry_fee,
            turn_penalty=score.breakdown.turn_penalty,
            opponent_bonus=score.breakdown.opponent_bonus,
        )
    
    return SessionResultResponse(
        session_id=int(session.id.value),
        room_id=int(session.room_id.value),
        user_id=session.user_id.value,
        final_score=score.breakdown.final_score if score else (session.final_score or 0),
        score_settled=session.score_settled,
        bonus_pending=session.bonus_pending,
        bonus_claimed=session.bonus_claimed,
        score_breakdown=score_breakdown,
    )


# =============================================================================
# 辅助函数
# =============================================================================

def _detect_meta_conversation(content: str) -> tuple[bool, Optional[str]]:
    """
    检测元对话关键词
    
    Args:
        content: 消息内容
        
    Returns:
        (是否元对话，关键词)
    """
    meta_keywords = [
        "你是谁",
        "你是 AI",
        "你是真人",
        "你是 bot",
        "聊天",
        "规则",
    ]
    
    content_lower = content.lower()
    for keyword in meta_keywords:
        if keyword in content_lower:
            return True, keyword
    
    return False, None
