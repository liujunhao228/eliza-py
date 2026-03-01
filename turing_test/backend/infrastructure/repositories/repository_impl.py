"""
Repository 层实现 - 数据访问

实现 domain/repositories.py 中定义的接口
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from turing_test.backend.models.domain_models import (
    BotConfig as BotConfigORM,
    Match as MatchORM,
    Room as RoomORM,
    RoomParticipant as RoomParticipantORM,
    Message as MessageORM,
    UserSession as UserSessionORM,
    SessionScore as SessionScoreORM,
    ScoreBreakdownItem as ScoreBreakdownItemORM,
)
from turing_test.backend.domain.models import (
    MatchId, RoomId, SessionId, UserId, MessageId,
    MatchStatus as DomainMatchStatus, OpponentType as DomainOpponentType,
    RoomType as DomainRoomType, RoomStatus as DomainRoomStatus,
    ParticipantRole as DomainParticipantRole,
    SessionStatus as DomainSessionStatus,
    MatchAggregate, RoomAggregate, UserSessionAggregate, ScoreAggregate,
    MatchRequestInfo, ParticipantInfo,
    TurnState, Judgment, ScoreBreakdown, ScoreSettlement,
)
from turing_test.backend.domain.repositories import (
    MatchRepository,
    RoomRepository,
    UserSessionRepository,
    ScoreRepository,
)


# =============================================================================
# 辅助函数 - 领域模型与 ORM 模型转换
# =============================================================================

def _match_status_to_orm(status: DomainMatchStatus) -> str:
    """领域匹配状态转 ORM 状态"""
    return status.value


def _match_status_from_orm(status: str) -> DomainMatchStatus:
    """ORM 匹配状态转领域状态"""
    return DomainMatchStatus(status)


def _opponent_type_to_orm(opponent_type: Optional[DomainOpponentType]) -> Optional[str]:
    """领域对手类型转 ORM"""
    return opponent_type.value if opponent_type else None


def _opponent_type_from_orm(status: Optional[str]) -> Optional[DomainOpponentType]:
    """ORM 对手类型转领域"""
    return DomainOpponentType(status) if status else None


def _room_type_to_orm(room_type: DomainRoomType) -> str:
    """领域对话类型转 ORM"""
    return room_type.value


def _room_type_from_orm(room_type: str) -> DomainRoomType:
    """ORM 对话类型转领域"""
    return DomainRoomType(room_type)


def _room_status_to_orm(status: DomainRoomStatus) -> str:
    """领域对话状态转 ORM"""
    return status.value


def _room_status_from_orm(status: str) -> DomainRoomStatus:
    """ORM 对话状态转领域"""
    return DomainRoomStatus(status)


def _participant_role_to_orm(role: DomainParticipantRole) -> str:
    """领域参与者角色转 ORM"""
    return role.value


def _participant_role_from_orm(role: str) -> DomainParticipantRole:
    """ORM 参与者角色转领域"""
    return DomainParticipantRole(role)


def _session_status_to_orm(status: DomainSessionStatus) -> str:
    """领域会话状态转 ORM"""
    return status.value


def _session_status_from_orm(status: str) -> DomainSessionStatus:
    """ORM 会话状态转领域"""
    return DomainSessionStatus(status)


# =============================================================================
# Match Repository 实现
# =============================================================================

class MatchRepositoryImpl(MatchRepository):
    """
    Match Repository 实现
    
    负责 Match 聚合根的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, match_id: MatchId) -> Optional[MatchAggregate]:
        """根据 ID 获取匹配"""
        stmt = select(MatchORM).where(MatchORM.id == match_id.value)
        result = await self._session.execute(stmt)
        orm_match = result.scalar_one_or_none()
        
        if not orm_match:
            return None
        
        return self._to_domain(orm_match)
    
    async def get_by_user_id(self, user_id: UserId, limit: int = 10) -> List[MatchAggregate]:
        """获取用户的匹配历史"""
        stmt = (
            select(MatchORM)
            .where(MatchORM.user_id == user_id.value)
            .order_by(MatchORM.requested_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_matches = result.scalars().all()
        
        return [self._to_domain(m) for m in orm_matches]
    
    async def get_pending_by_user(self, user_id: UserId) -> Optional[MatchAggregate]:
        """获取用户待处理的匹配"""
        stmt = (
            select(MatchORM)
            .where(MatchORM.user_id == user_id.value)
            .where(MatchORM.status == "pending")
            .order_by(MatchORM.requested_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_match = result.scalar_one_or_none()
        
        return self._to_domain(orm_match) if orm_match else None
    
    async def add(self, match: MatchAggregate) -> None:
        """添加匹配"""
        orm_match = self._to_orm(match)
        self._session.add(orm_match)
    
    async def update(self, match: MatchAggregate) -> None:
        """更新匹配"""
        orm_match = self._to_orm(match)
        await self._session.merge(orm_match)
    
    def _to_domain(self, orm: MatchORM) -> MatchAggregate:
        """ORM 转领域模型"""
        match = MatchAggregate(
            id=MatchId(str(orm.id)),
            user_id=UserId(orm.user_id),
            room_id=RoomId(str(orm.room_id)) if orm.room_id else None,
            request_info=MatchRequestInfo(
                user_score_snapshot=orm.user_score_snapshot,
                preferences=orm.preferences or {},
            ),
            status=_match_status_from_orm(orm.status),
            opponent_type=_opponent_type_from_orm(orm.opponent_type),
            matched_opponent_id=UserId(orm.matched_opponent_id) if orm.matched_opponent_id else None,
            bot_config_id=orm.bot_config_id,
            bot_level=orm.bot_level,
            is_honeypot=orm.is_honeypot,
            requested_at=orm.requested_at,
            matched_at=orm.matched_at,
            expired_at=orm.expired_at,
        )
        return match
    
    def _to_orm(self, match: MatchAggregate) -> MatchORM:
        """领域模型转 ORM"""
        orm = MatchORM(
            id=int(match.id.value),
            user_id=match.user_id.value,
            room_id=int(match.room_id.value) if match.room_id else None,
            user_score_snapshot=match.request_info.user_score_snapshot,
            preferences=match.request_info.preferences,
            status=_match_status_to_orm(match.status),
            opponent_type=_opponent_type_to_orm(match.opponent_type),
            matched_opponent_id=match.matched_opponent_id.value if match.matched_opponent_id else None,
            bot_config_id=match.bot_config_id,
            bot_level=match.bot_level,
            is_honeypot=match.is_honeypot,
            requested_at=match.requested_at,
            matched_at=match.matched_at,
            expired_at=match.expired_at,
        )
        return orm


# =============================================================================
# Room Repository 实现
# =============================================================================

class RoomRepositoryImpl(RoomRepository):
    """
    Room Repository 实现
    
    负责 Room 聚合根的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, room_id: RoomId) -> Optional[RoomAggregate]:
        """根据 ID 获取对话"""
        stmt = (
            select(RoomORM)
            .options(
                selectinload(RoomORM.participants),
                selectinload(RoomORM.messages),
            )
            .where(RoomORM.id == room_id.value)
        )
        result = await self._session.execute(stmt)
        orm_room = result.scalar_one_or_none()
        
        if not orm_room:
            return None
        
        return self._to_domain(orm_room)
    
    async def get_active(self, limit: int = 20) -> List[RoomAggregate]:
        """获取活跃的对话"""
        stmt = (
            select(RoomORM)
            .where(RoomORM.status == "active")
            .order_by(RoomORM.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_rooms = result.scalars().all()
        
        return [self._to_domain(r) for r in orm_rooms]
    
    async def add(self, room: RoomAggregate) -> None:
        """添加对话"""
        orm_room = self._to_orm(room)
        self._session.add(orm_room)
    
    async def update(self, room: RoomAggregate) -> None:
        """更新对话"""
        orm_room = self._to_orm(room)
        await self._session.merge(orm_room)
    
    def _to_domain(self, orm: RoomORM) -> RoomAggregate:
        """ORM 转领域模型"""
        room = RoomAggregate(
            id=RoomId(str(orm.id)),
            match_id=MatchId(str(orm.match_id)) if orm.match_id else None,
            room_type=_room_type_from_orm(orm.type),
            status=_room_status_from_orm(orm.status),
            end_reason=orm.end_reason,
            total_turns=orm.total_turns,
            meta_count=orm.meta_count,
            first_leaver_id=UserId(orm.first_leaver_id) if orm.first_leaver_id else None,
            created_at=orm.created_at,
            started_at=orm.started_at,
            ended_at=orm.ended_at,
        )
        
        # 添加参与者
        for participant_orm in orm.participants:
            participant = ParticipantInfo(
                user_id=UserId(participant_orm.user_id) if participant_orm.user_id else None,
                bot_config_id=participant_orm.bot_config_id,
                role=_participant_role_from_orm(participant_orm.role),
                bot_level=participant_orm.bot_level,
                is_honeypot=participant_orm.is_honeypot,
                joined_at=participant_orm.joined_at,
                left_at=participant_orm.left_at,
                left_reason=participant_orm.left_reason,
            )
            room.add_participant_raw(participant)
        
        return room
    
    def _to_orm(self, room: RoomAggregate) -> RoomORM:
        """领域模型转 ORM"""
        orm = RoomORM(
            id=int(room.id.value),
            match_id=int(room.match_id.value) if room.match_id else None,
            type=_room_type_to_orm(room.room_type),
            status=_room_status_to_orm(room.status),
            end_reason=room.end_reason,
            total_turns=room.total_turns,
            meta_count=room.meta_count,
            first_leaver_id=room.first_leaver_id.value if room.first_leaver_id else None,
            created_at=room.created_at,
            started_at=room.started_at,
            ended_at=room.ended_at,
        )
        return orm


# =============================================================================
# UserSession Repository 实现
# =============================================================================

class UserSessionRepositoryImpl(UserSessionRepository):
    """
    UserSession Repository 实现
    
    负责 UserSession 聚合根的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, session_id: SessionId) -> Optional[UserSessionAggregate]:
        """根据 ID 获取会话"""
        stmt = (
            select(UserSessionORM)
            .options(
                joinedload(UserSessionORM.score).joinedload(SessionScoreORM.breakdown_items),
            )
            .where(UserSessionORM.id == session_id.value)
        )
        result = await self._session.execute(stmt)
        orm_session = result.scalar_one_or_none()
        
        if not orm_session:
            return None
        
        return self._to_domain(orm_session)
    
    async def get_by_room_and_user(
        self, room_id: RoomId, user_id: UserId
    ) -> Optional[UserSessionAggregate]:
        """根据 Room 和用户 ID 获取会话"""
        stmt = (
            select(UserSessionORM)
            .where(UserSessionORM.room_id == int(room_id.value))
            .where(UserSessionORM.user_id == user_id.value)
        )
        result = await self._session.execute(stmt)
        orm_session = result.scalar_one_or_none()
        
        return self._to_domain(orm_session) if orm_session else None
    
    async def get_by_user(self, user_id: UserId, limit: int = 20) -> List[UserSessionAggregate]:
        """获取用户的会话历史"""
        stmt = (
            select(UserSessionORM)
            .where(UserSessionORM.user_id == user_id.value)
            .order_by(UserSessionORM.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_sessions = result.scalars().all()
        
        return [self._to_domain(s) for s in orm_sessions]
    
    async def add(self, session: UserSessionAggregate) -> None:
        """添加会话"""
        orm_session = self._to_orm(session)
        self._session.add(orm_session)
    
    async def update(self, session: UserSessionAggregate) -> None:
        """更新会话"""
        orm_session = self._to_orm(session)
        await self._session.merge(orm_session)
    
    def _to_domain(self, orm: UserSessionORM) -> UserSessionAggregate:
        """ORM 转领域模型"""
        session = UserSessionAggregate(
            id=SessionId(str(orm.id)),
            user_id=UserId(orm.user_id),
            room_id=RoomId(str(orm.room_id)),
            match_id=MatchId(str(orm.match_id)) if orm.match_id else None,
            turn_state=TurnState(
                user_turn_count=orm.user_turn_count,
                total_turns=orm.total_turns,
                is_user_turn=orm.is_user_turn,
            ),
            judgment=Judgment(
                user_guess=orm.user_guess,
                confidence=orm.confidence,
                is_mid_game=orm.is_mid_game,
                submitted_at=orm.judgment_submitted_at,
            ) if orm.user_guess else None,
            status=_session_status_from_orm(orm.status),
            ended_at=orm.ended_at,
            end_reason=orm.end_reason,
            created_at=orm.created_at,
            last_active_at=orm.last_active_at,
        )
        
        # 积分信息
        if orm.score:
            score_orm = orm.score
            session.score = ScoreAggregate(
                id=score_orm.id,
                user_session_id=session.id,
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
                    final_score=score_orm.final_score,
                ),
                settlement=ScoreSettlement(
                    base_settled=score_orm.base_settled,
                    base_settled_at=score_orm.base_settled_at,
                    bonus_pending=score_orm.bonus_pending,
                    bonus_claimed=score_orm.bonus_claimed,
                    bonus_claimed_at=score_orm.bonus_claimed_at,
                ),
                opponent_info={
                    "guess": score_orm.opponent_guess,
                    "confidence": score_orm.opponent_confidence,
                    "is_correct": score_orm.opponent_is_correct,
                },
                created_at=score_orm.created_at,
                updated_at=score_orm.updated_at,
            )
        
        return session
    
    def _to_orm(self, session: UserSessionAggregate) -> UserSessionORM:
        """领域模型转 ORM"""
        orm = UserSessionORM(
            id=int(session.id.value),
            user_id=session.user_id.value,
            room_id=int(session.room_id.value),
            match_id=int(session.match_id.value) if session.match_id else None,
            user_turn_count=session.turn_state.user_turn_count,
            total_turns=session.turn_state.total_turns,
            is_user_turn=session.turn_state.is_user_turn,
            user_guess=session.judgment.user_guess if session.judgment else None,
            confidence=session.judgment.confidence if session.judgment else None,
            is_mid_game=session.judgment.is_mid_game if session.judgment else False,
            judgment_submitted_at=session.judgment.submitted_at if session.judgment else None,
            status=_session_status_to_orm(session.status),
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            created_at=session.created_at,
            last_active_at=session.last_active_at,
        )
        return orm


# =============================================================================
# Score Repository 实现
# =============================================================================

class ScoreRepositoryImpl(ScoreRepository):
    """
    Score Repository 实现
    
    负责 Score 聚合根的持久化
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_user_session(self, user_session_id: SessionId) -> Optional[ScoreAggregate]:
        """根据 UserSession ID 获取积分"""
        stmt = (
            select(SessionScoreORM)
            .options(
                joinedload(SessionScoreORM.breakdown_items),
            )
            .where(SessionScoreORM.user_session_id == int(user_session_id.value))
        )
        result = await self._session.execute(stmt)
        orm_score = result.scalar_one_or_none()
        
        if not orm_score:
            return None
        
        return self._to_domain(orm_score, user_session_id)
    
    async def get_by_user(self, user_id: UserId, limit: int = 50) -> List[ScoreAggregate]:
        """获取用户的积分历史"""
        stmt = (
            select(SessionScoreORM)
            .where(SessionScoreORM.user_id == user_id.value)
            .order_by(SessionScoreORM.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_scores = result.scalars().all()
        
        return [self._to_domain(s, None) for s in orm_scores]
    
    async def add(self, score: ScoreAggregate) -> None:
        """添加积分"""
        orm_score = self._to_orm(score)
        self._session.add(orm_score)
    
    async def update(self, score: ScoreAggregate) -> None:
        """更新积分"""
        orm_score = self._to_orm(score)
        await self._session.merge(orm_score)
    
    def _to_domain(self, orm: SessionScoreORM, user_session_id: Optional[SessionId] = None) -> ScoreAggregate:
        """ORM 转领域模型"""
        score = ScoreAggregate(
            id=orm.id,
            user_session_id=user_session_id or SessionId(str(orm.user_session_id)),
            user_id=UserId(orm.user_id),
            room_id=RoomId(str(orm.room_id)),
            breakdown=ScoreBreakdown(
                base_score=orm.base_score,
                confidence_multiplier=orm.confidence_multiplier,
                meta_multiplier=orm.meta_multiplier,
                mid_game_multiplier=orm.mid_game_multiplier,
                entry_fee=orm.entry_fee,
                turn_penalty=orm.turn_penalty,
                opponent_bonus=orm.opponent_bonus,
                final_score=orm.final_score,
            ),
            settlement=ScoreSettlement(
                base_settled=orm.base_settled,
                base_settled_at=orm.base_settled_at,
                bonus_pending=orm.bonus_pending,
                bonus_claimed=orm.bonus_claimed,
                bonus_claimed_at=orm.bonus_claimed_at,
            ),
            opponent_info={
                "guess": orm.opponent_guess,
                "confidence": orm.opponent_confidence,
                "is_correct": orm.opponent_is_correct,
            },
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
        return score
    
    def _to_orm(self, score: ScoreAggregate) -> SessionScoreORM:
        """领域模型转 ORM"""
        orm = SessionScoreORM(
            id=score.id,
            user_session_id=int(score.user_session_id.value),
            user_id=score.user_id.value,
            room_id=int(score.room_id.value),
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
            opponent_guess=score.opponent_info.get("guess"),
            opponent_confidence=score.opponent_info.get("confidence"),
            opponent_is_correct=score.opponent_info.get("is_correct"),
        )
        return orm
