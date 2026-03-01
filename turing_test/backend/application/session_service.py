"""
用户会话应用服务 - UserSession Application Service

负责：
1. 创建用户会话（个人视角）
2. 更新回合状态
3. 提交判断
4. 积分结算
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from loguru import logger

from turing_test.backend.domain.models import (
    SessionId, RoomId, MatchId, UserId,
    SessionStatus,
    UserSessionAggregate,
    TurnState,
    Judgment,
    ScoreAggregate,
    ScoreBreakdown,
    ScoreSettlement,
)
from turing_test.backend.domain.repositories import (
    AbstractUnitOfWork,
    UserSessionRepository,
    ScoreRepository,
    RoomRepository,
)
from turing_test.backend.infrastructure.events.event_bus import Event, EventType


class SessionApplicationService:
    """
    用户会话应用服务
    
    用例：
    1. 创建会话 - 用户加入对话时创建
    2. 更新回合 - 每次消息往来后更新
    3. 提交判断 - 用户提交 AI/人类判断
    4. 积分结算 - 会话结束时结算
    5. 奖励申领 - 申领对方猜错奖励
    """
    
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        event_bus: Optional[Any] = None,
    ):
        self._uow = uow
        self._event_bus = event_bus
    
    async def create_session(
        self,
        user_id: int,
        room_id: str,
        match_id: Optional[str] = None,
    ) -> UserSessionAggregate:
        """
        创建用户会话
        
        Args:
            user_id: 用户 ID
            room_id: 对话 ID
            match_id: 匹配 ID（可选）
            
        Returns:
            创建的会话聚合根
        """
        # 检查是否已存在
        existing = await self._uow.user_sessions.get_by_room_and_user(
            RoomId(room_id), UserId(user_id)
        )
        if existing:
            logger.warning(f"会话已存在：user_id={user_id}, room_id={room_id}")
            return existing
        
        # 创建会话聚合根
        session = UserSessionAggregate.create(
            user_id=UserId(user_id),
            room_id=RoomId(room_id),
            match_id=MatchId(match_id) if match_id else None,
        )
        
        # 保存到数据库
        await self._uow.user_sessions.add(session)
        await self._uow.commit()
        
        logger.info(f"创建用户会话：session_id={session.id}, user_id={user_id}, room_id={room_id}")
        return session
    
    async def update_turn(
        self,
        session_id: str,
        is_user_turn: bool,
        increment_turn: bool = True,
    ) -> bool:
        """
        更新回合状态
        
        Args:
            session_id: 会话 ID
            is_user_turn: 是否用户回合
            increment_turn: 是否增加轮次
            
        Returns:
            是否成功
        """
        session = await self._uow.user_sessions.get(SessionId(session_id))
        if not session:
            logger.warning(f"会话不存在：session_id={session_id}")
            return False
        
        # 更新回合
        session.update_turn(
            is_user_turn=is_user_turn,
            increment_turn=increment_turn,
        )
        
        await self._uow.user_sessions.update(session)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.SESSION_TURN_CHANGED,
                    aggregate_id=session_id,
                    aggregate_type="UserSession",
                    data={
                        "is_user_turn": is_user_turn,
                        "total_turns": session.turn_state.total_turns,
                    },
                )
            )
        
        return True
    
    async def submit_judgment(
        self,
        session_id: str,
        user_guess: str,
        confidence: str,
        is_mid_game: bool = False,
    ) -> bool:
        """
        提交判断
        
        Args:
            session_id: 会话 ID
            user_guess: 用户判断 (human/ai)
            confidence: 信心等级 (low/mid/high)
            is_mid_game: 是否中途判断
            
        Returns:
            是否成功
        """
        session = await self._uow.user_sessions.get(SessionId(session_id))
        if not session:
            logger.warning(f"会话不存在：session_id={session_id}")
            return False
        
        # 提交判断
        session.submit_judgment(
            user_guess=user_guess,
            confidence=confidence,
            is_mid_game=is_mid_game,
        )
        
        await self._uow.user_sessions.update(session)
        await self._uow.commit()
        
        logger.info(
            f"提交判断：session_id={session_id}, "
            f"guess={user_guess}, confidence={confidence}, mid_game={is_mid_game}"
        )
        return True
    
    async def settle_score(
        self,
        session_id: str,
        base_score: int,
        confidence_multiplier: float = 1.0,
        meta_multiplier: float = 1.0,
        mid_game_multiplier: float = 1.0,
        entry_fee: int = 2,
        turn_penalty: int = 0,
        opponent_bonus: int = 0,
        opponent_guess: Optional[str] = None,
        opponent_confidence: Optional[str] = None,
        opponent_is_correct: Optional[bool] = None,
    ) -> bool:
        """
        结算积分
        
        Args:
            session_id: 会话 ID
            base_score: 基础分
            confidence_multiplier: 信心倍率
            meta_multiplier: 元对话倍率
            mid_game_multiplier: 中途判断倍率
            entry_fee: 入场费
            turn_penalty: 轮次惩罚
            opponent_bonus: 对方猜错奖励
            opponent_guess: 对方判断
            opponent_confidence: 对方信心
            opponent_is_correct: 对方是否正确
            
        Returns:
            是否成功
        """
        session = await self._uow.user_sessions.get(SessionId(session_id))
        if not session:
            logger.warning(f"会话不存在：session_id={session_id}")
            return False
        
        # 计算最终得分
        final_score = int(
            base_score * confidence_multiplier * meta_multiplier * mid_game_multiplier
            - entry_fee - turn_penalty + opponent_bonus
        )
        
        # 创建积分聚合根
        score = ScoreAggregate.create(
            user_session_id=session.id,
            user_id=session.user_id,
            room_id=session.room_id,
            base_score=base_score,
            confidence_multiplier=confidence_multiplier,
            meta_multiplier=meta_multiplier,
            mid_game_multiplier=mid_game_multiplier,
            entry_fee=entry_fee,
            turn_penalty=turn_penalty,
            opponent_bonus=opponent_bonus,
            final_score=final_score,
            opponent_guess=opponent_guess,
            opponent_confidence=opponent_confidence,
            opponent_is_correct=opponent_is_correct,
        )
        
        # 保存积分
        await self._uow.scores.add(score)
        
        # 更新会话积分状态
        session.settle_score(
            final_score=final_score,
            bonus_pending=opponent_bonus > 0,
        )
        
        await self._uow.user_sessions.update(session)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.SCORE_SETTLED,
                    aggregate_id=session_id,
                    aggregate_type="UserSession",
                    data={
                        "final_score": final_score,
                        "base_score": base_score,
                        "opponent_bonus": opponent_bonus,
                    },
                )
            )
        
        logger.info(f"积分结算：session_id={session_id}, final_score={final_score}")
        return True
    
    async def claim_bonus(self, session_id: str) -> bool:
        """
        申领对方猜错奖励
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否成功
        """
        session = await self._uow.user_sessions.get(SessionId(session_id))
        if not session:
            logger.warning(f"会话不存在：session_id={session_id}")
            return False
        
        # 申领奖励
        success = session.claim_bonus()
        if not success:
            logger.warning(f"无法申领奖励：session_id={session_id}")
            return False
        
        await self._uow.user_sessions.update(session)
        await self._uow.commit()
        
        logger.info(f"申领奖励成功：session_id={session_id}")
        return True
    
    async def end_session(
        self,
        session_id: str,
        end_reason: str,
    ) -> bool:
        """
        结束会话
        
        Args:
            session_id: 会话 ID
            end_reason: 结束原因
            
        Returns:
            是否成功
        """
        session = await self._uow.user_sessions.get(SessionId(session_id))
        if not session:
            logger.warning(f"会话不存在：session_id={session_id}")
            return False
        
        # 结束会话
        session.end(end_reason=end_reason)
        
        await self._uow.user_sessions.update(session)
        await self._uow.commit()
        
        logger.info(f"会话结束：session_id={session_id}, reason={end_reason}")
        return True
    
    async def get_session(self, session_id: str) -> Optional[UserSessionAggregate]:
        """获取会话详情"""
        return await self._uow.user_sessions.get(SessionId(session_id))
    
    async def get_user_sessions(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[UserSessionAggregate]:
        """获取用户会话历史"""
        return await self._uow.user_sessions.get_by_user(UserId(user_id), limit)
    
    async def get_score(self, session_id: str) -> Optional[ScoreAggregate]:
        """获取会话积分"""
        session = await self._uow.user_sessions.get(SessionId(session_id))
        if not session:
            return None
        return session.score


def create_session_application_service(
    uow: AbstractUnitOfWork,
    event_bus: Optional[Any] = None,
) -> SessionApplicationService:
    """创建用户会话应用服务实例"""
    return SessionApplicationService(uow, event_bus)
