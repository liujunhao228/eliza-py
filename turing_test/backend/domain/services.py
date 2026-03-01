"""
领域服务 - 聚合根业务逻辑

包含:
1. MatchAggregate - 匹配聚合根
2. RoomAggregate - 对话聚合根
3. UserSessionAggregate - 用户会话聚合根
4. ScoreAggregate - 积分聚合根
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from turing_test.backend.domain.models import (
    # 值对象
    MatchId, RoomId, SessionId, UserId, MessageId,
    MatchRequest, MatchResult,
    ParticipantInfo, MessageContent,
    Judgment, TurnState,
    ScoreBreakdown, ScoreSettlement,
    # 枚举
    MatchStatus, OpponentType,
    RoomType, RoomStatus, ParticipantRole,
    SessionStatus,
    # 事件
    DomainEvent,
    MatchRequested, MatchFound, MatchCompleted, MatchFailed, MatchTimeout,
    RoomCreated, MessageAdded, ParticipantLeft, RoomEnded,
    UserSessionCreated, MessageSent, JudgmentSubmitted, UserSessionEnded,
    ScoreCalculating, ScoreSettled, BonusClaimed,
    # 异常
    DomainError, MatchError, RoomError, SessionError, ScoreError,
)


# =============================================================================
# 匹配聚合根
# =============================================================================

@dataclass
class MatchAggregate:
    """
    匹配聚合根
    
    职责:
    1. 管理匹配状态流转
    2. 记录匹配结果
    3. 发布匹配事件
    """
    
    id: MatchId
    user_id: UserId
    status: MatchStatus = MatchStatus.PENDING
    request: Optional[MatchRequest] = None
    result: Optional[MatchResult] = None
    room_id: Optional[RoomId] = None
    
    requested_at: datetime = field(default_factory=datetime.utcnow)
    matched_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    # 领域事件 (待发布)
    _events: List[DomainEvent] = field(default_factory=list, repr=False)
    
    # 匹配结果字段
    opponent_type: Optional[OpponentType] = None
    matched_opponent_id: Optional[UserId] = None
    bot_config_id: Optional[str] = None
    bot_level: Optional[str] = None
    is_honeypot: bool = False
    
    def record_request(self, request: MatchRequest):
        """记录匹配请求"""
        if self.status != MatchStatus.PENDING:
            raise MatchError(f"Cannot record request in status {self.status}")
        
        self.request = request
        self.requested_at = request.requested_at
        
        self._events.append(MatchRequested(
            aggregate_id=str(self.id),
            user_id=self.user_id.value,
            user_score=request.user_score,
        ))
    
    def complete(self, room_id: RoomId, result: MatchResult) -> MatchCompleted:
        """
        完成匹配
        
        Args:
            room_id: 创建的对话 ID
            result: 匹配结果
        
        Returns:
            MatchCompleted 事件
        """
        if self.status != MatchStatus.PENDING:
            raise MatchError(f"Cannot complete match in status {self.status}")
        
        self.status = MatchStatus.MATCHED
        self.room_id = room_id
        self.result = result
        self.matched_at = datetime.utcnow()
        
        self.opponent_type = result.opponent_type
        self.matched_opponent_id = result.opponent_user_id
        self.bot_config_id = result.bot_config_id
        self.bot_level = result.bot_level
        self.is_honeypot = result.is_honeypot
        
        event = MatchCompleted(
            aggregate_id=str(self.id),
            match_id=str(self.id),
            user_id=self.user_id.value,
            room_id=str(room_id),
            opponent_type=result.opponent_type.value,
        )
        self._events.append(event)
        
        return event
    
    def fail(self, reason: str) -> MatchFailed:
        """
        失败
        
        Args:
            reason: 失败原因
        
        Returns:
            MatchFailed 事件
        """
        if self.status != MatchStatus.PENDING:
            raise MatchError(f"Cannot fail match in status {self.status}")
        
        self.status = MatchStatus.FAILED
        self.expired_at = datetime.utcnow()
        
        event = MatchFailed(
            aggregate_id=str(self.id),
            match_id=str(self.id),
            reason=reason,
        )
        self._events.append(event)
        
        return event
    
    def cancel(self) -> MatchCompleted:
        """取消匹配"""
        if self.status != MatchStatus.PENDING:
            raise MatchError(f"Cannot cancel match in status {self.status}")
        
        self.status = MatchStatus.CANCELLED
        self.expired_at = datetime.utcnow()
        
        event = MatchCompleted(
            aggregate_id=str(self.id),
            match_id=str(self.id),
            user_id=self.user_id.value,
            room_id="",
            opponent_type="",
        )
        self._events.append(event)
        
        return event
    
    def timeout(self) -> MatchTimeout:
        """超时"""
        if self.status != MatchStatus.PENDING:
            raise MatchError(f"Cannot timeout match in status {self.status}")
        
        self.status = MatchStatus.TIMEOUT
        self.expired_at = datetime.utcnow()
        
        event = MatchTimeout(
            aggregate_id=str(self.id),
            match_id=str(self.id),
        )
        self._events.append(event)
        
        return event
    
    def is_terminal(self) -> bool:
        """是否终端状态"""
        return self.status in {
            MatchStatus.MATCHED,
            MatchStatus.FAILED,
            MatchStatus.CANCELLED,
            MatchStatus.TIMEOUT,
        }
    
    def pop_events(self) -> List[DomainEvent]:
        """弹出并清空事件"""
        events = self._events.copy()
        self._events.clear()
        return events


# =============================================================================
# 对话聚合根
# =============================================================================

@dataclass
class RoomAggregate:
    """
    对话聚合根
    
    职责:
    1. 管理对话空间
    2. 添加消息
    3. 管理参与者
    4. 发布对话事件
    """
    
    id: RoomId
    type: RoomType
    status: RoomStatus = RoomStatus.ACTIVE
    
    participants: List[ParticipantInfo] = field(default_factory=list)
    total_turns: int = 0
    meta_count: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    end_reason: Optional[str] = None
    first_leaver_id: Optional[UserId] = None
    
    # 领域事件
    _events: List[DomainEvent] = field(default_factory=list, repr=False)
    
    def add_participant(self, participant: ParticipantInfo):
        """添加参与者"""
        self.participants.append(participant)
    
    def add_message(
        self,
        sender_id: Optional[UserId],
        sender_type: str,
        content: str,
        is_meta: bool = False,
        meta_keyword: Optional[str] = None,
    ) -> MessageAdded:
        """
        添加消息
        
        Returns:
            MessageAdded 事件
        """
        if self.status != RoomStatus.ACTIVE:
            raise RoomError(f"Room is not active: {self.status}")
        
        self.total_turns += 1
        
        if is_meta:
            self.meta_count += 1
        
        if self.started_at is None:
            self.started_at = datetime.utcnow()
        
        event = MessageAdded(
            aggregate_id=str(self.id),
            room_id=str(self.id),
            message_id=0,  # 由数据库生成
            sender_id=sender_id.value if sender_id else 0,
            turn_number=self.total_turns,
        )
        self._events.append(event)
        
        return event
    
    def participant_left(
        self,
        user_id: UserId,
        reason: str,
    ) -> ParticipantLeft:
        """
        参与者离开
        
        Returns:
            ParticipantLeft 事件
        """
        participant = self.get_participant(user_id)
        if not participant:
            raise RoomError(f"Participant not found: {user_id}")
        
        # 更新参与者状态
        for i, p in enumerate(self.participants):
            if p.user_id == user_id:
                self.participants[i] = ParticipantInfo(
                    user_id=p.user_id,
                    role=p.role,
                    bot_config_id=p.bot_config_id,
                    bot_level=p.bot_level,
                    is_honeypot=p.is_honeypot,
                    joined_at=p.joined_at,
                    left_at=datetime.utcnow(),
                    left_reason=reason,
                )
                break
        
        # 记录第一个离开者
        is_first = self.first_leaver_id is None
        if is_first:
            self.first_leaver_id = user_id
        
        # 检查是否所有人都离开了
        active_count = sum(1 for p in self.participants if p.left_at is None)
        if active_count == 0:
            self.status = RoomStatus.ENDED
            self.ended_at = datetime.utcnow()
            self.end_reason = reason
        
        event = ParticipantLeft(
            aggregate_id=str(self.id),
            room_id=str(self.id),
            user_id=user_id.value,
            reason=reason,
            is_first_leaver=is_first,
        )
        self._events.append(event)
        
        return event
    
    def end(self, reason: str) -> RoomEnded:
        """结束对话"""
        if self.status != RoomStatus.ACTIVE:
            raise RoomError(f"Room is not active: {self.status}")
        
        self.status = RoomStatus.ENDED
        self.ended_at = datetime.utcnow()
        self.end_reason = reason
        
        event = RoomEnded(
            aggregate_id=str(self.id),
            room_id=str(self.id),
            reason=reason,
        )
        self._events.append(event)
        
        return event
    
    def get_participant(self, user_id: UserId) -> Optional[ParticipantInfo]:
        """获取参与者"""
        for p in self.participants:
            if p.user_id == user_id:
                return p
        return None
    
    def get_opponent(self, user_id: UserId) -> Optional[ParticipantInfo]:
        """获取对手"""
        for p in self.participants:
            if p.user_id != user_id:
                return p
        return None
    
    def get_active_participants(self) -> List[ParticipantInfo]:
        """获取未离开的参与者"""
        return [p for p in self.participants if p.left_at is None]
    
    def is_single_player(self) -> bool:
        """是否单人对话"""
        return len(self.participants) == 1 or self.type == RoomType.HUMAN_VS_BOT
    
    def pop_events(self) -> List[DomainEvent]:
        """弹出并清空事件"""
        events = self._events.copy()
        self._events.clear()
        return events


# =============================================================================
# 用户会话聚合根
# =============================================================================

@dataclass
class UserSessionAggregate:
    """
    用户会话聚合根
    
    职责:
    1. 管理用户会话状态
    2. 提交判断
    3. 同步 Room 状态
    4. 发布会话事件
    """
    
    id: SessionId
    user_id: UserId
    room_id: RoomId
    match_id: Optional[MatchId] = None
    
    turn_state: TurnState = field(default_factory=lambda: TurnState(
        user_turn_count=0,
        total_turns=0,
        is_user_turn=True,
        last_message_id=None,
    ))
    
    judgment: Optional[Judgment] = None
    status: SessionStatus = SessionStatus.ACTIVE
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    end_reason: Optional[str] = None
    
    # 积分字段
    final_score: Optional[int] = None
    score_settled: bool = False
    bonus_pending: bool = False
    bonus_claimed: bool = False
    
    # 领域事件
    _events: List[DomainEvent] = field(default_factory=list, repr=False)
    
    def sync_from_room(self, room: RoomAggregate):
        """从 Room 同步状态"""
        self.turn_state = TurnState(
            user_turn_count=self.turn_state.user_turn_count,
            total_turns=room.total_turns,
            is_user_turn=self._calculate_is_user_turn(room),
            last_message_id=self.turn_state.last_message_id,
        )
    
    def _calculate_is_user_turn(self, room: RoomAggregate) -> bool:
        """计算是否轮到用户"""
        # 人机：总是用户的回合
        if room.is_single_player():
            return True
        
        # 真人：交替发言
        return room.total_turns % 2 == 0
    
    def send_message(self, message_id: int) -> MessageSent:
        """发送消息"""
        if self.status != SessionStatus.ACTIVE:
            raise SessionError(f"Session is not active: {self.status}")
        
        self.turn_state = TurnState(
            user_turn_count=self.turn_state.user_turn_count + 1,
            total_turns=self.turn_state.total_turns + 1,
            is_user_turn=False,
            last_message_id=MessageId(str(message_id)),
        )
        
        self.last_active_at = datetime.utcnow()
        
        event = MessageSent(
            aggregate_id=str(self.id),
            session_id=int(self.id.value) if self.id.value.isdigit() else 0,
            user_id=self.user_id.value,
            message_id=message_id,
        )
        self._events.append(event)
        
        return event
    
    def submit_judgment(
        self,
        guess: str,
        confidence: str,
        is_mid_game: bool = False,
    ) -> JudgmentSubmitted:
        """提交判断"""
        if not self.can_submit_judgment():
            raise SessionError("Cannot submit judgment")
        
        self.judgment = Judgment(
            user_guess=guess,
            confidence=confidence,
            is_mid_game=is_mid_game,
            submitted_at=datetime.utcnow(),
        )
        
        event = JudgmentSubmitted(
            aggregate_id=str(self.id),
            session_id=int(self.id.value) if self.id.value.isdigit() else 0,
            user_id=self.user_id.value,
            guess=guess,
            confidence=confidence,
            is_mid_game=is_mid_game,
        )
        self._events.append(event)
        
        return event
    
    def end(self, reason: str) -> UserSessionEnded:
        """结束会话"""
        if self.status != SessionStatus.ACTIVE:
            raise SessionError(f"Session is not active: {self.status}")
        
        self.status = SessionStatus.ENDED
        self.ended_at = datetime.utcnow()
        self.end_reason = reason
        
        event = UserSessionEnded(
            aggregate_id=str(self.id),
            session_id=int(self.id.value) if self.id.value.isdigit() else 0,
            user_id=self.user_id.value,
            reason=reason,
        )
        self._events.append(event)
        
        return event
    
    def can_submit_judgment(self) -> bool:
        """是否可以提交判断"""
        return (
            self.status in (SessionStatus.ACTIVE, SessionStatus.ENDED) and
            self.judgment is None
        )
    
    def can_receive_message(self) -> bool:
        """是否可以接收消息"""
        return self.status == SessionStatus.ACTIVE
    
    def is_ended(self) -> bool:
        """是否已结束"""
        return self.status in (
            SessionStatus.ENDED,
            SessionStatus.TIMEOUT,
            SessionStatus.ERROR,
        )
    
    def pop_events(self) -> List[DomainEvent]:
        """弹出并清空事件"""
        events = self._events.copy()
        self._events.clear()
        return events


# =============================================================================
# 积分聚合根
# =============================================================================

@dataclass
class ScoreAggregate:
    """
    积分聚合根
    
    职责:
    1. 计算积分
    2. 结算基础分
    3. 发放奖励
    4. 发布积分事件
    """
    
    session_id: SessionId
    user_id: UserId
    room_id: RoomId
    
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    settlement: ScoreSettlement = field(default_factory=lambda: ScoreSettlement(
        base_settled=False,
        base_settled_at=None,
        bonus_pending=False,
        bonus_claimed=False,
        bonus_claimed_at=None,
    ))
    
    opponent_guess: Optional[str] = None
    opponent_confidence: Optional[str] = None
    opponent_is_correct: Optional[bool] = None
    
    # 领域事件
    _events: List[DomainEvent] = field(default_factory=list, repr=False)
    
    def calculate(
        self,
        user_guess: str,
        opponent_type: str,
        confidence: str,
        turn_count: int,
        meta_count: int,
        is_mid_game: bool = False,
        opponent_guess: Optional[str] = None,
        opponent_confidence: Optional[str] = None,
    ):
        """
        计算积分
        
        Args:
            user_guess: 用户判断 (human/ai)
            opponent_type: 对手类型 (human/bot/honeypot)
            confidence: 信心等级
            turn_count: 总轮次
            meta_count: 元对话次数
            is_mid_game: 是否场中判断
            opponent_guess: 对手判断
            opponent_confidence: 对手信心
        """
        # 判断是否正确
        is_correct = (
            (user_guess == "ai" and opponent_type in ("bot", "honeypot")) or
            (user_guess == "human" and opponent_type == "human")
        )
        
        # 基础分
        base_score = 10 if is_correct else -15
        
        # 创建积分明细
        self.breakdown = ScoreBreakdown.create(
            base_score=base_score,
            confidence=confidence,
            meta_count=meta_count,
            is_mid_game=is_mid_game,
            turn_count=turn_count,
        )
        
        # 计算对方猜错奖励
        opponent_bonus = 0
        if opponent_guess and opponent_confidence:
            opp_is_correct = (
                (opponent_guess == "ai" and opponent_type in ("bot", "honeypot")) or
                (opponent_guess == "human" and opponent_type == "human")
            )
            
            self.opponent_guess = opponent_guess
            self.opponent_confidence = opponent_confidence
            self.opponent_is_correct = opp_is_correct
            
            if not opp_is_correct:
                # 对方猜错，计算奖励
                opp_base = -15  # 对方错误的基础分
                opp_mult = {"low": 1.0, "mid": 2.5, "high": 5.0}.get(opponent_confidence.lower(), 1.0)
                opponent_bonus = abs(opp_base * opp_mult)
                self.breakdown = ScoreBreakdown.create(
                    base_score=base_score,
                    confidence=confidence,
                    meta_count=meta_count,
                    is_mid_game=is_mid_game,
                    turn_count=turn_count,
                    opponent_bonus=int(opponent_bonus),
                )
        
        event = ScoreCalculating(
            aggregate_id=str(self.session_id),
            session_id=int(self.session_id.value) if self.session_id.value.isdigit() else 0,
            user_id=self.user_id.value,
        )
        self._events.append(event)
    
    def settle_base(self) -> ScoreSettled:
        """结算基础积分"""
        self.settlement = ScoreSettlement(
            base_settled=True,
            base_settled_at=datetime.utcnow(),
            bonus_pending=self.breakdown.opponent_bonus > 0,
            bonus_claimed=self.settlement.bonus_claimed,
            bonus_claimed_at=self.settlement.bonus_claimed_at,
        )
        
        event = ScoreSettled(
            aggregate_id=str(self.session_id),
            session_id=int(self.session_id.value) if self.session_id.value.isdigit() else 0,
            user_id=self.user_id.value,
            final_score=self.breakdown.final_score,
            breakdown=self.breakdown.to_dict(),
        )
        self._events.append(event)
        
        return event
    
    def claim_bonus(self) -> BonusClaimed:
        """领取奖励"""
        if not self.settlement.bonus_pending:
            raise ScoreError("No pending bonus")
        
        self.settlement = ScoreSettlement(
            base_settled=self.settlement.base_settled,
            base_settled_at=self.settlement.base_settled_at,
            bonus_pending=False,
            bonus_claimed=True,
            bonus_claimed_at=datetime.utcnow(),
        )
        
        event = BonusClaimed(
            aggregate_id=str(self.session_id),
            session_id=int(self.session_id.value) if self.session_id.value.isdigit() else 0,
            user_id=self.user_id.value,
            bonus_amount=self.breakdown.opponent_bonus,
        )
        self._events.append(event)
        
        return event
    
    def pop_events(self) -> List[DomainEvent]:
        """弹出并清空事件"""
        events = self._events.copy()
        self._events.clear()
        return events
