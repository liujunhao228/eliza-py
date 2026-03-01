"""
领域模型 - 聚合根和值对象

设计原则:
1. 聚合根 - 业务操作的核心入口
2. 值对象 - 不可变的业务概念
3. 领域事件 - 记录发生的重要业务事件
4. 纯 Python 类 - 不依赖 SQLAlchemy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid


# =============================================================================
# 值对象 - 通用类型
# =============================================================================

@dataclass(frozen=True)
class MatchId:
    """匹配 ID 值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value:
            object.__setattr__(self, 'value', str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RoomId:
    """对话 ID 值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value:
            object.__setattr__(self, 'value', str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SessionId:
    """会话 ID 值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value:
            object.__setattr__(self, 'value', str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class UserId:
    """用户 ID 值对象"""
    value: int
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class MessageId:
    """消息 ID 值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value:
            object.__setattr__(self, 'value', str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# 匹配领域 - 值对象
# =============================================================================

class MatchStatus(Enum):
    """匹配状态"""
    PENDING = "pending"
    MATCHED = "matched"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class OpponentType(Enum):
    """对手类型"""
    HUMAN = "human"
    BOT = "bot"
    HONEYPOT = "honeypot"


@dataclass(frozen=True)
class MatchRequest:
    """匹配请求值对象"""
    user_id: UserId
    user_score: int
    preferences: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class MatchResult:
    """匹配结果值对象"""
    opponent_type: OpponentType
    opponent_user_id: Optional[UserId]
    bot_config_id: Optional[str]
    bot_level: Optional[str]
    is_honeypot: bool
    matched_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opponent_type": self.opponent_type.value,
            "opponent_user_id": self.opponent_user_id.value if self.opponent_user_id else None,
            "bot_config_id": self.bot_config_id,
            "bot_level": self.bot_level,
            "is_honeypot": self.is_honeypot,
            "matched_at": self.matched_at.isoformat(),
        }


# =============================================================================
# 对话领域 - 值对象
# =============================================================================

class RoomType(Enum):
    """对话类型"""
    HUMAN_VS_BOT = "human_vs_bot"
    HUMAN_VS_HUMAN = "human_vs_human"
    HONEYPOT = "honeypot"


class RoomStatus(Enum):
    """对话状态"""
    ACTIVE = "active"
    ENDED = "ended"
    TIMEOUT = "timeout"


class ParticipantRole(Enum):
    """参与者角色"""
    USER = "user"
    OPPONENT = "opponent"
    BOT = "bot"


@dataclass(frozen=True)
class ParticipantInfo:
    """参与者信息值对象"""
    user_id: Optional[UserId]
    role: ParticipantRole
    bot_config_id: Optional[str]
    bot_level: Optional[str]
    is_honeypot: bool
    joined_at: datetime
    left_at: Optional[datetime] = None
    left_reason: Optional[str] = None


@dataclass(frozen=True)
class MessageContent:
    """消息内容值对象"""
    sender_id: Optional[UserId]
    sender_type: str  # "user" or "bot"
    content: str
    is_meta: bool = False
    meta_keyword: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id.value if self.sender_id else None,
            "sender_type": self.sender_type,
            "content": self.content,
            "is_meta": self.is_meta,
            "meta_keyword": self.meta_keyword,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# 用户会话领域 - 值对象
# =============================================================================

class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    ENDED = "ended"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True)
class Judgment:
    """判断值对象"""
    user_guess: str  # "human" or "ai"
    confidence: str  # "low", "mid", "high"
    is_mid_game: bool
    submitted_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_guess": self.user_guess,
            "confidence": self.confidence,
            "is_mid_game": self.is_mid_game,
            "submitted_at": self.submitted_at.isoformat(),
        }


@dataclass(frozen=True)
class TurnState:
    """回合状态值对象"""
    user_turn_count: int
    total_turns: int
    is_user_turn: bool
    last_message_id: Optional[MessageId]


# =============================================================================
# 积分领域 - 值对象
# =============================================================================

@dataclass(frozen=True)
class ScoreBreakdown:
    """
    积分明细值对象
    
    不可变，计算后不再改变
    """
    base_score: int = 0
    confidence_multiplier: float = 1.0
    meta_multiplier: float = 1.0
    mid_game_multiplier: float = 1.0
    entry_fee: int = 2
    turn_penalty: int = 0
    opponent_bonus: int = 0
    
    @property
    def final_score(self) -> int:
        """计算最终得分"""
        base = (
            self.base_score *
            self.confidence_multiplier *
            self.meta_multiplier *
            self.mid_game_multiplier
        )
        return int(base) - self.entry_fee - self.turn_penalty + self.opponent_bonus
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_score": self.base_score,
            "confidence_multiplier": self.confidence_multiplier,
            "meta_multiplier": self.meta_multiplier,
            "mid_game_multiplier": self.mid_game_multiplier,
            "entry_fee": self.entry_fee,
            "turn_penalty": self.turn_penalty,
            "opponent_bonus": self.opponent_bonus,
            "final_score": self.final_score,
        }
    
    @classmethod
    def create(
        cls,
        base_score: int,
        confidence: str,
        meta_count: int,
        is_mid_game: bool,
        turn_count: int,
        opponent_bonus: int = 0,
    ) -> ScoreBreakdown:
        """
        创建积分明细
        
        Args:
            base_score: 基础分
            confidence: 信心等级 (low/mid/high)
            meta_count: 元对话次数
            is_mid_game: 是否场中判断
            turn_count: 总轮次
            opponent_bonus: 对方猜错奖励
        """
        # 信心倍率
        confidence_multipliers = {
            "low": 1.0,
            "mid": 2.5,
            "high": 5.0,
        }
        confidence_multiplier = confidence_multipliers.get(confidence.lower(), 1.0)
        
        # 元对话倍率
        meta_multiplier = 1.0 + (meta_count * 1.0)
        
        # 场中倍率
        mid_game_multiplier = 2.0 if is_mid_game else 1.0
        
        # 轮数惩罚 (超过 3 轮后每轮 -0.5)
        penalty_turns = max(0, turn_count - 3)
        turn_penalty = int(penalty_turns * 0.5)
        
        return cls(
            base_score=base_score,
            confidence_multiplier=confidence_multiplier,
            meta_multiplier=meta_multiplier,
            mid_game_multiplier=mid_game_multiplier,
            entry_fee=2,
            turn_penalty=turn_penalty,
            opponent_bonus=opponent_bonus,
        )


@dataclass(frozen=True)
class ScoreSettlement:
    """积分结算状态值对象"""
    base_settled: bool
    base_settled_at: Optional[datetime]
    bonus_pending: bool
    bonus_claimed: bool
    bonus_claimed_at: Optional[datetime]


# =============================================================================
# 领域事件
# =============================================================================

@dataclass
class DomainEvent:
    """领域事件基类"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""
    aggregate_type: str = ""


# 匹配领域事件
@dataclass
class MatchRequested(DomainEvent):
    aggregate_type: str = "Match"
    user_id: int = 0
    user_score: int = 0


@dataclass
class MatchFound(DomainEvent):
    aggregate_type: str = "Match"
    user_id: int = 0
    opponent_type: str = ""
    room_id: str = ""


@dataclass
class MatchCompleted(DomainEvent):
    aggregate_type: str = "Match"
    match_id: str = ""
    user_id: int = 0
    room_id: str = ""
    opponent_type: str = ""


@dataclass
class MatchFailed(DomainEvent):
    aggregate_type: str = "Match"
    match_id: str = ""
    reason: str = ""


@dataclass
class MatchTimeout(DomainEvent):
    aggregate_type: str = "Match"
    match_id: str = ""


# 对话领域事件
@dataclass
class RoomCreated(DomainEvent):
    aggregate_type: str = "Room"
    room_id: str = ""
    room_type: str = ""
    participant_ids: List[int] = field(default_factory=list)


@dataclass
class MessageAdded(DomainEvent):
    aggregate_type: str = "Room"
    room_id: str = ""
    message_id: int = 0
    sender_id: int = 0
    turn_number: int = 0


@dataclass
class ParticipantLeft(DomainEvent):
    aggregate_type: str = "Room"
    room_id: str = ""
    user_id: int = 0
    reason: str = ""
    is_first_leaver: bool = False


@dataclass
class RoomEnded(DomainEvent):
    aggregate_type: str = "Room"
    room_id: str = ""
    reason: str = ""


# 用户会话领域事件
@dataclass
class UserSessionCreated(DomainEvent):
    aggregate_type: str = "UserSession"
    session_id: int = 0
    user_id: int = 0
    room_id: str = ""


@dataclass
class MessageSent(DomainEvent):
    aggregate_type: str = "UserSession"
    session_id: int = 0
    user_id: int = 0
    message_id: int = 0


@dataclass
class JudgmentSubmitted(DomainEvent):
    aggregate_type: str = "UserSession"
    session_id: int = 0
    user_id: int = 0
    guess: str = ""
    confidence: str = ""
    is_mid_game: bool = False


@dataclass
class UserSessionEnded(DomainEvent):
    aggregate_type: str = "UserSession"
    session_id: int = 0
    user_id: int = 0
    reason: str = ""


# 积分领域事件
@dataclass
class ScoreCalculating(DomainEvent):
    aggregate_type: str = "SessionScore"
    session_id: int = 0
    user_id: int = 0


@dataclass
class ScoreSettled(DomainEvent):
    aggregate_type: str = "SessionScore"
    session_id: int = 0
    user_id: int = 0
    final_score: int = 0
    breakdown: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BonusClaimed(DomainEvent):
    aggregate_type: str = "SessionScore"
    session_id: int = 0
    user_id: int = 0
    bonus_amount: int = 0


# =============================================================================
# 异常定义
# =============================================================================

class DomainError(Exception):
    """领域异常基类"""
    pass


class MatchError(DomainError):
    """匹配异常"""
    pass


class RoomError(DomainError):
    """对话异常"""
    pass


class SessionError(DomainError):
    """会话异常"""
    pass


class ScoreError(DomainError):
    """积分异常"""
    pass
