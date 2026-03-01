"""
Repository 层 - 数据访问接口

设计原则:
1. 接口与实现分离
2. 异步操作
3. 领域模型与 ORM 模型转换
4. 工作单元模式 (Unit of Work)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from turing_test.backend.domain.models import (
    MatchId, RoomId, SessionId, UserId, MessageId,
    MatchStatus, OpponentType,
    RoomType, RoomStatus, ParticipantRole, ParticipantInfo,
    SessionStatus,
    Judgment, TurnState,
    ScoreBreakdown, ScoreSettlement,
)
from turing_test.backend.domain.services import (
    MatchAggregate,
    RoomAggregate,
    UserSessionAggregate,
    ScoreAggregate,
)

T = TypeVar('T')


# =============================================================================
# 工作单元 - Unit of Work
# =============================================================================

class AbstractUnitOfWork(ABC):
    """工作单元抽象基类"""
    
    matches: MatchRepository
    rooms: RoomRepository
    user_sessions: UserSessionRepository
    scores: ScoreRepository
    
    @abstractmethod
    async def commit(self):
        """提交事务"""
        pass
    
    @abstractmethod
    async def rollback(self):
        """回滚事务"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭工作单元"""
        pass


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy 工作单元实现
    
    用法:
        async with SqlAlchemyUnitOfWork(session) as uow:
            match = await uow.matches.get(match_id)
            uow.matches.add(match)
            await uow.commit()
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
        self.matches = MatchRepository(session)
        self.rooms = RoomRepository(session)
        self.user_sessions = UserSessionRepository(session)
        self.scores = ScoreRepository(session)
    
    async def commit(self):
        await self._session.commit()
    
    async def rollback(self):
        await self._session.rollback()
    
    async def close(self):
        await self._session.close()
    
    async def __aenter__(self) -> AbstractUnitOfWork:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        await self.close()


# =============================================================================
# Match Repository
# =============================================================================

class MatchRepository:
    """
    匹配仓库
    
    负责 Match 实体的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, match_id: MatchId) -> Optional[MatchAggregate]:
        """获取匹配"""
        from turing_test.backend.models.domain_models import Match
        
        result = await self._session.execute(
            select(Match).where(Match.id == int(match_id.value) if match_id.value.isdigit() else match_id.value)
        )
        match_orm = result.scalar_one_or_none()
        
        if not match_orm:
            return None
        
        return self._to_domain(match_orm)
    
    async def get_by_user_id(self, user_id: UserId) -> Optional[MatchAggregate]:
        """获取用户的匹配"""
        from turing_test.backend.models.domain_models import Match
        
        result = await self._session.execute(
            select(Match)
            .where(Match.user_id == user_id.value)
            .order_by(Match.requested_at.desc())
        )
        match_orm = result.scalar_one_or_none()
        
        if not match_orm:
            return None
        
        return self._to_domain(match_orm)
    
    async def get_active_by_user_id(self, user_id: UserId) -> Optional[MatchAggregate]:
        """获取用户活跃的匹配"""
        from turing_test.backend.models.domain_models import Match

        result = await self._session.execute(
            select(Match)
            .where(Match.user_id == user_id.value)
            .where(Match.status.in_(["pending", "matched"]))
            .order_by(Match.requested_at.desc())
        )
        match_orm = result.scalar_one_or_none()

        if not match_orm:
            return None

        return self._to_domain(match_orm)

    async def get_pending_by_user(self, user_id: UserId) -> Optional[MatchAggregate]:
        """获取用户待处理的匹配"""
        from turing_test.backend.models.domain_models import Match

        result = await self._session.execute(
            select(Match)
            .where(Match.user_id == user_id.value)
            .where(Match.status == "pending")
            .order_by(Match.requested_at.desc())
        )
        match_orm = result.scalar_one_or_none()

        if not match_orm:
            return None

        return self._to_domain(match_orm)
    
    async def add(self, match: MatchAggregate):
        """添加匹配"""
        from turing_test.backend.models.domain_models import Match
        
        match_orm = Match(
            user_id=match.user_id.value,
            status=match.status.value,
            user_score_snapshot=match.request.user_score if match.request else 0,
            opponent_type=match.opponent_type.value if match.opponent_type else None,
            matched_opponent_id=match.matched_opponent_id.value if match.matched_opponent_id else None,
            bot_config_id=match.bot_config_id,
            bot_level=match.bot_level,
            is_honeypot=match.is_honeypot,
            requested_at=match.requested_at,
            matched_at=match.matched_at,
            expired_at=match.expired_at,
        )
        
        if match.room_id:
            match_orm.room_id = int(match.room_id.value) if match.room_id.value.isdigit() else match.room_id.value
        
        self._session.add(match_orm)
        await self._session.flush()
        
        # 更新聚合根的 ID
        match.id = MatchId(str(match_orm.id))
    
    async def update(self, match: MatchAggregate):
        """更新匹配"""
        from turing_test.backend.models.domain_models import Match
        
        result = await self._session.execute(
            select(Match).where(Match.id == int(match.id.value) if match.id.value.isdigit() else match.id.value)
        )
        match_orm = result.scalar_one_or_none()
        
        if not match_orm:
            raise ValueError(f"Match not found: {match.id}")
        
        match_orm.status = match.status.value
        match_orm.room_id = int(match.room_id.value) if match.room_id and match.room_id.value.isdigit() else None
        match_orm.opponent_type = match.opponent_type.value if match.opponent_type else None
        match_orm.matched_opponent_id = match.matched_opponent_id.value if match.matched_opponent_id else None
        match_orm.bot_config_id = match.bot_config_id
        match_orm.bot_level = match.bot_level
        match_orm.is_honeypot = match.is_honeypot
        match_orm.matched_at = match.matched_at
        match_orm.expired_at = match.expired_at
    
    def _to_domain(self, match_orm: Any) -> MatchAggregate:
        """ORM 转领域模型"""
        from turing_test.backend.domain.models import MatchRequest
        
        # 重建 request 对象
        request = MatchRequest(
            user_id=UserId(match_orm.user_id),
            user_score=match_orm.user_score_snapshot,
            preferences=match_orm.preferences or {},
            requested_at=match_orm.requested_at,
        )
        
        return MatchAggregate(
            id=MatchId(str(match_orm.id)),
            user_id=UserId(match_orm.user_id),
            status=MatchStatus(match_orm.status),
            room_id=RoomId(str(match_orm.room_id)) if match_orm.room_id else None,
            request=request,
            requested_at=match_orm.requested_at,
            matched_at=match_orm.matched_at,
            expired_at=match_orm.expired_at,
            opponent_type=OpponentType(match_orm.opponent_type) if match_orm.opponent_type else None,
            matched_opponent_id=UserId(match_orm.matched_opponent_id) if match_orm.matched_opponent_id else None,
            bot_config_id=match_orm.bot_config_id,
            bot_level=match_orm.bot_level,
            is_honeypot=match_orm.is_honeypot,
        )


# =============================================================================
# Room Repository
# =============================================================================

class RoomRepository:
    """
    对话仓库
    
    负责 Room 实体的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, room_id: RoomId) -> Optional[RoomAggregate]:
        """获取对话"""
        from turing_test.backend.models.domain_models import Room, RoomParticipant
        
        result = await self._session.execute(
            select(Room)
            .options(selectinload(Room.participants))
            .where(Room.id == int(room_id.value) if room_id.value.isdigit() else room_id.value)
        )
        room_orm = result.scalar_one_or_none()
        
        if not room_orm:
            return None
        
        return self._to_domain(room_orm)
    
    async def add(self, room: RoomAggregate):
        """添加对话"""
        from turing_test.backend.models.domain_models import Room, RoomParticipant
        
        room_orm = Room(
            type=room.type.value,
            status=room.status.value,
            total_turns=room.total_turns,
            meta_count=room.meta_count,
            first_leaver_id=room.first_leaver_id.value if room.first_leaver_id else None,
            created_at=room.created_at,
            started_at=room.started_at,
            ended_at=room.ended_at,
            end_reason=room.end_reason,
        )
        
        self._session.add(room_orm)
        await self._session.flush()
        
        # 更新聚合根的 ID
        room.id = RoomId(str(room_orm.id))
        
        # 添加参与者
        for participant in room.participants:
            participant_orm = RoomParticipant(
                room_id=room_orm.id,
                user_id=participant.user_id.value if participant.user_id else None,
                role=participant.role.value,
                bot_config_id=participant.bot_config_id,
                bot_level=participant.bot_level,
                is_honeypot=participant.is_honeypot,
                joined_at=participant.joined_at,
                left_at=participant.left_at,
                left_reason=participant.left_reason,
            )
            self._session.add(participant_orm)
    
    async def update(self, room: RoomAggregate):
        """更新对话"""
        from turing_test.backend.models.domain_models import Room, RoomParticipant

        result = await self._session.execute(
            select(Room).where(Room.id == int(room.id.value) if room.id.value.isdigit() else room.id.value)
        )
        room_orm = result.scalar_one_or_none()

        if not room_orm:
            raise ValueError(f"Room not found: {room.id}")

        room_orm.status = room.status.value
        room_orm.total_turns = room.total_turns
        room_orm.meta_count = room.meta_count
        room_orm.first_leaver_id = room.first_leaver_id.value if room.first_leaver_id else None
        room_orm.ended_at = room.ended_at
        room_orm.end_reason = room.end_reason

        # 同步参与者
        # 1. 删除不存在的参与者
        existing_user_ids = {p.user_id for p in room_orm.participants if p.user_id is not None}
        current_user_ids = {p.user_id.value for p in room.participants if p.user_id is not None}

        for user_id in existing_user_ids - current_user_ids:
            # 标记为离开而不是删除
            for p in room_orm.participants:
                if p.user_id == user_id:
                    p.left_at = datetime.utcnow()
                    p.left_reason = "removed"

        # 2. 添加新的参与者
        for participant in room.participants:
            # 检查是否已存在
            if participant.user_id and participant.user_id.value in existing_user_ids:
                continue

            participant_orm = RoomParticipant(
                room_id=room_orm.id,
                user_id=participant.user_id.value if participant.user_id else None,
                role=participant.role.value,
                bot_config_id=participant.bot_config_id,
                bot_level=participant.bot_level,
                is_honeypot=participant.is_honeypot,
                joined_at=participant.joined_at,
                left_at=participant.left_at,
                left_reason=participant.left_reason,
            )
            self._session.add(participant_orm)
    
    def _to_domain(self, room_orm: Any) -> RoomAggregate:
        """ORM 转领域模型"""
        room = RoomAggregate(
            id=RoomId(str(room_orm.id)),
            type=RoomType(room_orm.type),
            status=RoomStatus(room_orm.status),
            total_turns=room_orm.total_turns,
            meta_count=room_orm.meta_count,
            created_at=room_orm.created_at,
            started_at=room_orm.started_at,
            ended_at=room_orm.ended_at,
            end_reason=room_orm.end_reason,
            first_leaver_id=UserId(room_orm.first_leaver_id) if room_orm.first_leaver_id else None,
        )
        
        for p in room_orm.participants:
            room.participants.append(ParticipantInfo(
                user_id=UserId(p.user_id) if p.user_id else None,
                role=ParticipantRole(p.role),
                bot_config_id=p.bot_config_id,
                bot_level=p.bot_level,
                is_honeypot=p.is_honeypot,
                joined_at=p.joined_at,
                left_at=p.left_at,
                left_reason=p.left_reason,
            ))
        
        return room


# =============================================================================
# UserSession Repository
# =============================================================================

class UserSessionRepository:
    """
    用户会话仓库
    
    负责 UserSession 实体的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, session_id: SessionId) -> Optional[UserSessionAggregate]:
        """获取会话"""
        from turing_test.backend.models.domain_models import UserSession

        result = await self._session.execute(
            select(UserSession)
            .options(selectinload(UserSession.score))
            .where(
                UserSession.id == int(session_id.value) if session_id.value.isdigit() else session_id.value
            )
        )
        session_orm = result.scalar_one_or_none()

        if not session_orm:
            return None

        return self._to_domain(session_orm)
    
    async def get_by_user_id(self, user_id: UserId) -> List[UserSessionAggregate]:
        """获取用户的会话列表"""
        from turing_test.backend.models.domain_models import UserSession
        
        result = await self._session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id.value)
            .order_by(UserSession.created_at.desc())
        )
        sessions_orm = result.scalars().all()
        
        return [self._to_domain(s) for s in sessions_orm]
    
    async def get_by_room_id(self, room_id: RoomId) -> List[UserSessionAggregate]:
        """获取对话的所有用户会话"""
        from turing_test.backend.models.domain_models import UserSession
        
        result = await self._session.execute(
            select(UserSession).where(UserSession.room_id == int(room_id.value) if room_id.value.isdigit() else room_id.value)
        )
        sessions_orm = result.scalars().all()
        
        return [self._to_domain(s) for s in sessions_orm]
    
    async def get_active_by_user_id(self, user_id: UserId) -> Optional[UserSessionAggregate]:
        """获取用户活跃的会话"""
        from turing_test.backend.models.domain_models import UserSession

        result = await self._session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id.value)
            .where(UserSession.status == "active")
            .order_by(UserSession.created_at.desc())
        )
        session_orm = result.scalar_one_or_none()

        if not session_orm:
            return None

        return self._to_domain(session_orm)

    async def get_by_room_and_user(
        self,
        room_id: RoomId,
        user_id: UserId,
    ) -> Optional[UserSessionAggregate]:
        """根据对话 ID 和用户 ID 获取会话"""
        from turing_test.backend.models.domain_models import UserSession

        result = await self._session.execute(
            select(UserSession)
            .where(UserSession.room_id == int(room_id.value) if room_id.value.isdigit() else room_id.value)
            .where(UserSession.user_id == user_id.value)
            .order_by(UserSession.created_at.desc())
        )
        session_orm = result.scalar_one_or_none()

        if not session_orm:
            return None

        return self._to_domain(session_orm)

    async def add(self, session: UserSessionAggregate):
        """添加会话"""
        from turing_test.backend.models.domain_models import UserSession
        
        session_orm = UserSession(
            user_id=session.user_id.value,
            room_id=int(session.room_id.value) if session.room_id.value.isdigit() else session.room_id.value,
            match_id=int(session.match_id.value) if session.match_id and session.match_id.value.isdigit() else None,
            user_turn_count=session.turn_state.user_turn_count,
            total_turns=session.turn_state.total_turns,
            is_user_turn=session.turn_state.is_user_turn,
            last_message_id=session.turn_state.last_message_id.value if session.turn_state.last_message_id else None,
            user_guess=session.judgment.user_guess if session.judgment else None,
            confidence=session.judgment.confidence if session.judgment else None,
            is_mid_game=session.judgment.is_mid_game if session.judgment else False,
            judgment_submitted_at=session.judgment.submitted_at if session.judgment else None,
            final_score=session.final_score,
            score_settled=session.score_settled,
            bonus_pending=session.bonus_pending,
            bonus_claimed=session.bonus_claimed,
            status=session.status.value,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            created_at=session.created_at,
            last_active_at=session.last_active_at,
        )
        
        self._session.add(session_orm)
        await self._session.flush()
        
        # 更新聚合根的 ID
        session.id = SessionId(str(session_orm.id))
    
    async def update(self, session: UserSessionAggregate):
        """更新会话"""
        from turing_test.backend.models.domain_models import UserSession
        
        result = await self._session.execute(
            select(UserSession).where(
                UserSession.id == int(session.id.value) if session.id.value.isdigit() else session.id.value
            )
        )
        session_orm = result.scalar_one_or_none()
        
        if not session_orm:
            raise ValueError(f"UserSession not found: {session.id}")
        
        session_orm.user_turn_count = session.turn_state.user_turn_count
        session_orm.total_turns = session.turn_state.total_turns
        session_orm.is_user_turn = session.turn_state.is_user_turn
        session_orm.last_message_id = session.turn_state.last_message_id.value if session.turn_state.last_message_id else None
        session_orm.user_guess = session.judgment.user_guess if session.judgment else None
        session_orm.confidence = session.judgment.confidence if session.judgment else None
        session_orm.is_mid_game = session.judgment.is_mid_game if session.judgment else False
        session_orm.judgment_submitted_at = session.judgment.submitted_at if session.judgment else None
        session_orm.final_score = session.final_score
        session_orm.score_settled = session.score_settled
        session_orm.bonus_pending = session.bonus_pending
        session_orm.bonus_claimed = session.bonus_claimed
        session_orm.status = session.status.value
        session_orm.ended_at = session.ended_at
        session_orm.end_reason = session.end_reason
        session_orm.last_active_at = session.last_active_at
    
    def _to_domain(self, session_orm: Any) -> UserSessionAggregate:
        """ORM 转领域模型"""
        session = UserSessionAggregate(
            id=SessionId(str(session_orm.id)),
            user_id=UserId(session_orm.user_id),
            room_id=RoomId(str(session_orm.room_id)),
            match_id=MatchId(str(session_orm.match_id)) if session_orm.match_id else None,
            turn_state=TurnState(
                user_turn_count=session_orm.user_turn_count,
                total_turns=session_orm.total_turns,
                is_user_turn=session_orm.is_user_turn,
                last_message_id=MessageId(str(session_orm.last_message_id)) if session_orm.last_message_id else None,
            ),
            status=SessionStatus(session_orm.status),
            created_at=session_orm.created_at,
            last_active_at=session_orm.last_active_at,
            ended_at=session_orm.ended_at,
            end_reason=session_orm.end_reason,
            final_score=session_orm.final_score,
            score_settled=session_orm.score_settled,
            bonus_pending=session_orm.bonus_pending,
            bonus_claimed=session_orm.bonus_claimed,
        )

        if session_orm.user_guess:
            session.judgment = Judgment(
                user_guess=session_orm.user_guess,
                confidence=session_orm.confidence,
                is_mid_game=session_orm.is_mid_game,
                submitted_at=session_orm.judgment_submitted_at,
            )

        # 加载关联的积分
        if session_orm.score:
            score_orm = session_orm.score
            session.score = ScoreAggregate(
                session_id=SessionId(str(score_orm.user_session_id)),
                user_id=UserId(score_orm.user_id),
                room_id=RoomId(str(score_orm.room_id)),
                breakdown=ScoreBreakdown(
                    base_score=score_orm.base_score,
                    confidence_multiplier=score_orm.confidence_multiplier,
                    meta_multiplier=score_orm.meta_multiplier,
                    mid_game_multiplier=score_orm.mid_game_multiplier,
                    entry_fee=score_orm.entry_fee,
                    turn_penalty=score_orm.turn_penalty,
                    opponent_bonus=score_orm.opponent_bonus,
                ),
                settlement=ScoreSettlement(
                    base_settled=score_orm.base_settled,
                    base_settled_at=score_orm.base_settled_at,
                    bonus_pending=score_orm.bonus_pending,
                    bonus_claimed=score_orm.bonus_claimed,
                    bonus_claimed_at=score_orm.bonus_claimed_at,
                ),
                opponent_guess=score_orm.opponent_guess,
                opponent_confidence=score_orm.opponent_confidence,
                opponent_is_correct=score_orm.opponent_is_correct,
            )

        return session


# =============================================================================
# Score Repository
# =============================================================================

class ScoreRepository:
    """
    积分仓库
    
    负责 SessionScore 实体的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_session_id(self, session_id: SessionId) -> Optional[ScoreAggregate]:
        """获取会话积分"""
        from turing_test.backend.models.domain_models import SessionScore, ScoreBreakdownItem
        
        result = await self._session.execute(
            select(SessionScore)
            .options(selectinload(SessionScore.breakdown_items))
            .where(SessionScore.user_session_id == int(session_id.value) if session_id.value.isdigit() else session_id.value)
        )
        score_orm = result.scalar_one_or_none()
        
        if not score_orm:
            return None
        
        return self._to_domain(score_orm)
    
    async def add(self, score: ScoreAggregate):
        """添加积分"""
        from turing_test.backend.models.domain_models import SessionScore, ScoreBreakdownItem
        
        score_orm = SessionScore(
            user_session_id=int(score.session_id.value) if score.session_id.value.isdigit() else score.session_id.value,
            user_id=score.user_id.value,
            room_id=int(score.room_id.value) if score.room_id.value.isdigit() else score.room_id.value,
            base_score=score.breakdown.base_score,
            confidence_multiplier=score.breakdown.confidence_multiplier,
            meta_multiplier=score.breakdown.meta_multiplier,
            mid_game_multiplier=score.breakdown.mid_game_multiplier,
            entry_fee=score.breakdown.entry_fee,
            turn_penalty=score.breakdown.turn_penalty,
            opponent_bonus=score.breakdown.opponent_bonus,
            final_score=score.breakdown.final_score,
            base_settled=score.settlement.base_settled,
            base_settled_at=score.settlement.base_settled_at,
            bonus_pending=score.settlement.bonus_pending,
            bonus_claimed=score.settlement.bonus_claimed,
            bonus_claimed_at=score.settlement.bonus_claimed_at,
            opponent_guess=score.opponent_guess,
            opponent_confidence=score.opponent_confidence,
            opponent_is_correct=score.opponent_is_correct,
        )
        
        self._session.add(score_orm)
        await self._session.flush()
    
    async def update(self, score: ScoreAggregate):
        """更新积分"""
        from turing_test.backend.models.domain_models import SessionScore
        
        result = await self._session.execute(
            select(SessionScore).where(
                SessionScore.user_session_id == int(score.session_id.value) if score.session_id.value.isdigit() else score.session_id.value
            )
        )
        score_orm = result.scalar_one_or_none()
        
        if not score_orm:
            raise ValueError(f"SessionScore not found: {score.session_id}")
        
        score_orm.base_score = score.breakdown.base_score
        score_orm.confidence_multiplier = score.breakdown.confidence_multiplier
        score_orm.meta_multiplier = score.breakdown.meta_multiplier
        score_orm.mid_game_multiplier = score.breakdown.mid_game_multiplier
        score_orm.turn_penalty = score.breakdown.turn_penalty
        score_orm.opponent_bonus = score.breakdown.opponent_bonus
        score_orm.final_score = score.breakdown.final_score
        score_orm.base_settled = score.settlement.base_settled
        score_orm.base_settled_at = score.settlement.base_settled_at
        score_orm.bonus_pending = score.settlement.bonus_pending
        score_orm.bonus_claimed = score.settlement.bonus_claimed
        score_orm.bonus_claimed_at = score.settlement.bonus_claimed_at
        score_orm.opponent_guess = score.opponent_guess
        score_orm.opponent_confidence = score.opponent_confidence
        score_orm.opponent_is_correct = score.opponent_is_correct
    
    def _to_domain(self, score_orm: Any) -> ScoreAggregate:
        """ORM 转领域模型"""
        score = ScoreAggregate(
            session_id=SessionId(str(score_orm.user_session_id)),
            user_id=UserId(score_orm.user_id),
            room_id=RoomId(str(score_orm.room_id)),
            breakdown=ScoreBreakdown(
                base_score=score_orm.base_score,
                confidence_multiplier=score_orm.confidence_multiplier,
                meta_multiplier=score_orm.meta_multiplier,
                mid_game_multiplier=score_orm.mid_game_multiplier,
                entry_fee=score_orm.entry_fee,
                turn_penalty=score_orm.turn_penalty,
                opponent_bonus=score_orm.opponent_bonus,
            ),
            settlement=ScoreSettlement(
                base_settled=score_orm.base_settled,
                base_settled_at=score_orm.base_settled_at,
                bonus_pending=score_orm.bonus_pending,
                bonus_claimed=score_orm.bonus_claimed,
                bonus_claimed_at=score_orm.bonus_claimed_at,
            ),
            opponent_guess=score_orm.opponent_guess,
            opponent_confidence=score_orm.opponent_confidence,
            opponent_is_correct=score_orm.opponent_is_correct,
        )
        
        return score
