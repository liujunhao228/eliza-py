"""
领域模型测试

测试领域层的核心功能:
1. 值对象 - 不可变性
2. 聚合根 - 业务逻辑和状态流转
3. 领域事件 - 事件生成
4. 异常处理
"""

import pytest
from datetime import datetime, timedelta
from typing import List

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
    # 领域事件
    MatchRequested, MatchCompleted, MatchFailed,
    RoomCreated, MessageAdded, RoomEnded,
    JudgmentSubmitted, UserSessionEnded,
    ScoreSettled, BonusClaimed,
    # 异常
    DomainError, MatchError, RoomError, SessionError, ScoreError,
)
from turing_test.backend.domain.services import (
    MatchAggregate,
    RoomAggregate,
    UserSessionAggregate,
    ScoreAggregate,
)


# =============================================================================
# 值对象测试
# =============================================================================

class TestValueObjects:
    """值对象测试"""
    
    def test_match_id_auto_generate(self):
        """测试 MatchId 自动生成"""
        match_id = MatchId("")
        assert match_id.value != ""
        assert str(match_id).startswith("MatchId(") or len(str(match_id)) > 0
    
    def test_match_id_with_value(self):
        """测试 MatchId 使用已有值"""
        match_id = MatchId("test-123")
        assert match_id.value == "test-123"
    
    def test_user_id_value(self):
        """测试 UserId"""
        user_id = UserId(100)
        assert user_id.value == 100
        assert str(user_id) == "100"
    
    def test_score_breakdown_immutable(self):
        """测试 ScoreBreakdown 不可变性"""
        breakdown = ScoreBreakdown(base_score=10)
        
        # 尝试修改应该失败 (frozen dataclass)
        with pytest.raises(Exception):  # frozen dataclass 会抛出异常
            breakdown.base_score = 20
    
    def test_score_breakdown_final_score(self):
        """测试积分计算"""
        breakdown = ScoreBreakdown(
            base_score=10,
            confidence_multiplier=2.5,
            meta_multiplier=1.0,
            mid_game_multiplier=1.0,
            entry_fee=2,
            turn_penalty=0,
            opponent_bonus=0,
        )
        
        # final_score = 10 * 2.5 * 1.0 * 1.0 - 2 - 0 + 0 = 23
        assert breakdown.final_score == 23
    
    def test_score_breakdown_create(self):
        """测试 ScoreBreakdown.create 工厂方法"""
        breakdown = ScoreBreakdown.create(
            base_score=10,
            confidence="high",
            meta_count=2,
            is_mid_game=False,
            turn_count=5,
        )
        
        assert breakdown.base_score == 10
        assert breakdown.confidence_multiplier == 5.0  # high = 5.0
        assert breakdown.meta_multiplier == 3.0  # 1 + 2*1.0
        assert breakdown.mid_game_multiplier == 1.0
        assert breakdown.turn_penalty == 1  # (5-3) * 0.5 = 1
    
    def test_judgment_to_dict(self):
        """测试 Judgment 序列化"""
        judgment = Judgment(
            user_guess="ai",
            confidence="high",
            is_mid_game=False,
            submitted_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        
        data = judgment.to_dict()
        assert data["user_guess"] == "ai"
        assert data["confidence"] == "high"
        assert data["is_mid_game"] is False


# =============================================================================
# Match Aggregate 测试
# =============================================================================

class TestMatchAggregate:
    """Match 聚合根测试"""
    
    def test_create_pending_match(self):
        """测试创建待匹配"""
        match = MatchAggregate(
            id=MatchId("test-1"),
            user_id=UserId(100),
            status=MatchStatus.PENDING,
        )
        
        assert match.status == MatchStatus.PENDING
        assert match.is_terminal() is False
    
    def test_complete_match(self):
        """测试完成匹配"""
        match = MatchAggregate(
            id=MatchId("test-1"),
            user_id=UserId(100),
            status=MatchStatus.PENDING,
        )
        
        result = MatchResult(
            opponent_type=OpponentType.BOT,
            opponent_user_id=None,
            bot_config_id="bot-1",
            bot_level="lv1_newbie",
            is_honeypot=False,
        )
        
        event = match.complete(RoomId("room-1"), result)
        
        assert match.status == MatchStatus.MATCHED
        assert match.room_id == RoomId("room-1")
        assert isinstance(event, MatchCompleted)
        assert event.user_id == 100
    
    def test_complete_match_invalid_status(self):
        """测试在无效状态下完成匹配"""
        match = MatchAggregate(
            id=MatchId("test-1"),
            user_id=UserId(100),
            status=MatchStatus.MATCHED,  # 已经是 MATCHED
        )
        
        with pytest.raises(MatchError):
            match.complete(RoomId("room-1"), MatchResult(
                opponent_type=OpponentType.BOT,
                opponent_user_id=None,
                bot_config_id=None,
                bot_level=None,
                is_honeypot=False,
            ))
    
    def test_fail_match(self):
        """测试失败匹配"""
        match = MatchAggregate(
            id=MatchId("test-1"),
            user_id=UserId(100),
            status=MatchStatus.PENDING,
        )
        
        event = match.fail("Bot pool empty")
        
        assert match.status == MatchStatus.FAILED
        assert isinstance(event, MatchFailed)
        assert event.reason == "Bot pool empty"
    
    def test_timeout_match(self):
        """测试超时匹配"""
        match = MatchAggregate(
            id=MatchId("test-1"),
            user_id=UserId(100),
            status=MatchStatus.PENDING,
        )
        
        event = match.timeout()
        
        assert match.status == MatchStatus.TIMEOUT
        assert isinstance(event, MatchTimeout)
    
    def test_pop_events(self):
        """测试弹出事件"""
        match = MatchAggregate(
            id=MatchId("test-1"),
            user_id=UserId(100),
            status=MatchStatus.PENDING,
        )
        
        match.fail("Test error")
        
        events = match.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], MatchFailed)
        
        # 再次弹出应该为空
        events = match.pop_events()
        assert len(events) == 0


# =============================================================================
# Room Aggregate 测试
# =============================================================================

class TestRoomAggregate:
    """Room 聚合根测试"""
    
    def test_create_room(self):
        """测试创建对话"""
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
            status=RoomStatus.ACTIVE,
        )
        
        assert room.status == RoomStatus.ACTIVE
        assert room.total_turns == 0
    
    def test_add_participant(self):
        """测试添加参与者"""
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
        )
        
        participant = ParticipantInfo(
            user_id=UserId(100),
            role=ParticipantRole.USER,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        )
        
        room.add_participant(participant)
        
        assert len(room.participants) == 1
        assert room.get_participant(UserId(100)) is not None
    
    def test_add_message(self):
        """测试添加消息"""
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
        )
        
        event = room.add_message(
            sender_id=UserId(100),
            sender_type="user",
            content="Hello",
            is_meta=False,
        )
        
        assert room.total_turns == 1
        assert isinstance(event, MessageAdded)
        assert event.turn_number == 1
    
    def test_add_meta_message(self):
        """测试添加元对话消息"""
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
        )
        
        room.add_message(
            sender_id=UserId(100),
            sender_type="user",
            content="你是真人吗？",
            is_meta=True,
            meta_keyword="identity_question",
        )
        
        assert room.total_turns == 1
        assert room.meta_count == 1
    
    def test_participant_left(self):
        """测试参与者离开"""
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_HUMAN,
        )
        
        # 添加两个参与者
        room.add_participant(ParticipantInfo(
            user_id=UserId(100),
            role=ParticipantRole.USER,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        ))
        
        room.add_participant(ParticipantInfo(
            user_id=UserId(200),
            role=ParticipantRole.OPPONENT,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        ))
        
        # 用户 100 离开
        event = room.participant_left(UserId(100), "gave_up")
        
        assert room.first_leaver_id == UserId(100)
        assert room.status == RoomStatus.ACTIVE  # 还有人，保持 active
        assert isinstance(event, ParticipantLeft)
        assert event.is_first_leaver is True
    
    def test_room_end_when_all_left(self):
        """测试所有人离开时对话结束"""
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_HUMAN,
        )
        
        room.add_participant(ParticipantInfo(
            user_id=UserId(100),
            role=ParticipantRole.USER,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
            left_at=datetime.utcnow(),  # 已离开
        ))
        
        room.add_participant(ParticipantInfo(
            user_id=UserId(200),
            role=ParticipantRole.OPPONENT,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        ))
        
        # 最后一个参与者离开
        room.participant_left(UserId(200), "ended")
        
        assert room.status == RoomStatus.ENDED
        assert room.ended_at is not None
    
    def test_is_single_player(self):
        """测试是否单人对话"""
        room_bot = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
        )
        assert room_bot.is_single_player() is True
        
        room_human = RoomAggregate(
            id=RoomId("room-2"),
            type=RoomType.HUMAN_VS_HUMAN,
        )
        room_human.add_participant(ParticipantInfo(
            user_id=UserId(100),
            role=ParticipantRole.USER,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        ))
        room_human.add_participant(ParticipantInfo(
            user_id=UserId(200),
            role=ParticipantRole.OPPONENT,
            bot_config_id=None,
            bot_level=None,
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        ))
        assert room_human.is_single_player() is False


# =============================================================================
# UserSession Aggregate 测试
# =============================================================================

class TestUserSessionAggregate:
    """UserSession 聚合根测试"""
    
    def test_create_session(self):
        """测试创建会话"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        assert session.status == SessionStatus.ACTIVE
        assert session.can_submit_judgment() is True
        assert session.can_receive_message() is True
    
    def test_send_message(self):
        """测试发送消息"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        event = session.send_message(1)
        
        assert session.turn_state.user_turn_count == 1
        assert session.turn_state.is_user_turn is False
        assert isinstance(event, MessageSent)
    
    def test_submit_judgment(self):
        """测试提交判断"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        event = session.submit_judgment(
            guess="ai",
            confidence="high",
            is_mid_game=False,
        )
        
        assert session.judgment is not None
        assert session.judgment.user_guess == "ai"
        assert session.judgment.confidence == "high"
        assert isinstance(event, JudgmentSubmitted)
    
    def test_submit_judgment_twice(self):
        """测试重复提交判断"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        session.submit_judgment(guess="ai", confidence="high")
        
        with pytest.raises(SessionError):
            session.submit_judgment(guess="human", confidence="low")
    
    def test_end_session(self):
        """测试结束会话"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        event = session.end("user_requested")
        
        assert session.status == SessionStatus.ENDED
        assert session.ended_at is not None
        assert isinstance(event, UserSessionEnded)
    
    def test_sync_from_room_bot(self):
        """测试从 Room 同步状态 (人机)"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
        )
        room.total_turns = 4
        
        session.sync_from_room(room)
        
        # 人机对战：总是用户的回合
        assert session.turn_state.is_user_turn is True
    
    def test_sync_from_room_human(self):
        """测试从 Room 同步状态 (真人)"""
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_HUMAN,
        )
        
        # 偶数轮：用户回合
        room.total_turns = 4
        session.sync_from_room(room)
        assert session.turn_state.is_user_turn is True
        
        # 奇数轮：对方回合
        room.total_turns = 5
        session.sync_from_room(room)
        assert session.turn_state.is_user_turn is False


# =============================================================================
# Score Aggregate 测试
# =============================================================================

class TestScoreAggregate:
    """Score 聚合根测试"""
    
    def test_calculate_correct_ai(self):
        """测试正确识别 AI 的积分计算"""
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        score.calculate(
            user_guess="ai",
            opponent_type="bot",
            confidence="high",
            turn_count=5,
            meta_count=0,
            is_mid_game=False,
        )
        
        # base_score = 10 (正确)
        # confidence_multiplier = 5.0 (high)
        # meta_multiplier = 1.0
        # mid_game_multiplier = 1.0
        # entry_fee = 2
        # turn_penalty = 1 (5-3)*0.5
        # final = 10*5.0*1.0*1.0 - 2 - 1 = 47
        assert score.breakdown.base_score == 10
        assert score.breakdown.confidence_multiplier == 5.0
        assert score.breakdown.final_score == 47
    
    def test_calculate_wrong_ai(self):
        """测试误判 AI 的积分计算"""
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        score.calculate(
            user_guess="human",
            opponent_type="bot",
            confidence="high",
            turn_count=5,
            meta_count=0,
            is_mid_game=False,
        )
        
        # base_score = -15 (错误)
        # confidence_multiplier = 5.0 (high)
        # final = -15*5.0*1.0*1.0 - 2 - 1 = -78
        assert score.breakdown.base_score == -15
        assert score.breakdown.final_score == -78
    
    def test_calculate_with_opponent_bonus(self):
        """测试对方猜错奖励"""
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        score.calculate(
            user_guess="ai",
            opponent_type="bot",
            confidence="mid",
            turn_count=5,
            meta_count=0,
            is_mid_game=False,
            opponent_guess="human",  # 对方猜 human
            opponent_confidence="mid",
        )
        
        # 对方猜错，应该有奖励
        assert score.breakdown.opponent_bonus > 0
        assert score.settlement.bonus_pending is True
    
    def test_settle_base(self):
        """测试结算基础积分"""
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        score.calculate(
            user_guess="ai",
            opponent_type="bot",
            confidence="mid",
            turn_count=5,
            meta_count=0,
        )
        
        event = score.settle_base()
        
        assert score.settlement.base_settled is True
        assert score.settlement.base_settled_at is not None
        assert isinstance(event, ScoreSettled)
        assert event.final_score == score.breakdown.final_score
    
    def test_claim_bonus(self):
        """测试领取奖励"""
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        score.calculate(
            user_guess="ai",
            opponent_type="bot",
            confidence="mid",
            turn_count=5,
            opponent_guess="human",
            opponent_confidence="mid",
        )
        score.settle_base()
        
        event = score.claim_bonus()
        
        assert score.settlement.bonus_claimed is True
        assert score.settlement.bonus_pending is False
        assert isinstance(event, BonusClaimed)
        assert event.bonus_amount == score.breakdown.opponent_bonus
    
    def test_claim_bonus_without_pending(self):
        """测试没有待领取奖励时领取"""
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        score.calculate(
            user_guess="ai",
            opponent_type="bot",
            confidence="mid",
            turn_count=5,
        )
        score.settle_base()
        
        with pytest.raises(ScoreError):
            score.claim_bonus()


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试 - 测试完整流程"""
    
    def test_full_bot_match_flow(self):
        """测试完整人机匹配流程"""
        # 1. 创建匹配
        match = MatchAggregate(
            id=MatchId("match-1"),
            user_id=UserId(100),
            status=MatchStatus.PENDING,
        )
        
        # 2. 完成匹配 (Bot)
        result = MatchResult(
            opponent_type=OpponentType.BOT,
            opponent_user_id=None,
            bot_config_id="bot-1",
            bot_level="lv1_newbie",
            is_honeypot=False,
        )
        match.complete(RoomId("room-1"), result)
        
        # 3. 创建对话
        room = RoomAggregate(
            id=RoomId("room-1"),
            type=RoomType.HUMAN_VS_BOT,
        )
        room.add_participant(ParticipantInfo(
            user_id=UserId(100),
            role=ParticipantRole.USER,
            bot_config_id="bot-1",
            bot_level="lv1_newbie",
            is_honeypot=False,
            joined_at=datetime.utcnow(),
        ))
        
        # 4. 创建用户会话
        session = UserSessionAggregate(
            id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        
        # 5. 发送消息 (3 轮)
        for i in range(3):
            room.add_message(UserId(100), "user", f"Message {i+1}")
            session.send_message(i + 1)
        
        # 6. 提交判断
        session.submit_judgment(guess="ai", confidence="high")
        
        # 7. 结束会话
        session.end("user_requested")
        
        # 8. 计算积分
        score = ScoreAggregate(
            session_id=SessionId("session-1"),
            user_id=UserId(100),
            room_id=RoomId("room-1"),
        )
        score.calculate(
            user_guess="ai",
            opponent_type="bot",
            confidence="high",
            turn_count=3,
            meta_count=0,
        )
        score.settle_base()
        
        # 验证
        assert match.status == MatchStatus.MATCHED
        assert room.status == RoomStatus.ACTIVE
        assert session.status == SessionStatus.ENDED
        assert session.judgment is not None
        assert score.settlement.base_settled is True
        assert score.breakdown.final_score > 0  # 正确识别 AI，应该得分


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
