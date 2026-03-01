"""
领域层 - Domain Layer

包含:
- 领域模型 (值对象、聚合根)
- 领域服务 (业务逻辑)
- 领域事件
- Repository 接口
"""

from turing_test.backend.domain.models import (
    # 值对象
    MatchId,
    RoomId,
    SessionId,
    UserId,
    MessageId,
    MatchRequest,
    MatchResult,
    ParticipantInfo,
    MessageContent,
    Judgment,
    TurnState,
    ScoreBreakdown,
    ScoreSettlement,
    # 枚举
    MatchStatus,
    OpponentType,
    RoomType,
    RoomStatus,
    ParticipantRole,
    SessionStatus,
    # 领域事件
    DomainEvent,
    MatchRequested,
    MatchFound,
    MatchCompleted,
    MatchFailed,
    MatchTimeout,
    RoomCreated,
    MessageAdded,
    ParticipantLeft,
    RoomEnded,
    UserSessionCreated,
    MessageSent,
    JudgmentSubmitted,
    UserSessionEnded,
    ScoreCalculating,
    ScoreSettled,
    BonusClaimed,
    # 异常
    DomainError,
    MatchError,
    RoomError,
    SessionError,
    ScoreError,
)

from turing_test.backend.domain.services import (
    MatchAggregate,
    RoomAggregate,
    UserSessionAggregate,
    ScoreAggregate,
)

from turing_test.backend.domain.repositories import (
    AbstractUnitOfWork,
    SqlAlchemyUnitOfWork,
    MatchRepository,
    RoomRepository,
    UserSessionRepository,
    ScoreRepository,
)

__all__ = [
    # 值对象
    'MatchId',
    'RoomId',
    'SessionId',
    'UserId',
    'MessageId',
    'MatchRequest',
    'MatchResult',
    'ParticipantInfo',
    'MessageContent',
    'Judgment',
    'TurnState',
    'ScoreBreakdown',
    'ScoreSettlement',
    # 枚举
    'MatchStatus',
    'OpponentType',
    'RoomType',
    'RoomStatus',
    'ParticipantRole',
    'SessionStatus',
    # 领域事件
    'DomainEvent',
    'MatchRequested',
    'MatchFound',
    'MatchCompleted',
    'MatchFailed',
    'MatchTimeout',
    'RoomCreated',
    'MessageAdded',
    'ParticipantLeft',
    'RoomEnded',
    'UserSessionCreated',
    'MessageSent',
    'JudgmentSubmitted',
    'UserSessionEnded',
    'ScoreCalculating',
    'ScoreSettled',
    'BonusClaimed',
    # 异常
    'DomainError',
    'MatchError',
    'RoomError',
    'SessionError',
    'ScoreError',
    # 聚合根
    'MatchAggregate',
    'RoomAggregate',
    'UserSessionAggregate',
    'ScoreAggregate',
    # Repository
    'AbstractUnitOfWork',
    'SqlAlchemyUnitOfWork',
    'MatchRepository',
    'RoomRepository',
    'UserSessionRepository',
    'ScoreRepository',
]
