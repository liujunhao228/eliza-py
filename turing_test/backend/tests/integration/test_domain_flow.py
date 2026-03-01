"""
端到端测试 - 三层分离架构验证

测试完整流程：
1. 用户请求匹配 → Match 层
2. 创建对话空间 → Room 层
3. 发送消息 → Message 层
4. 提交判断 → UserSession 层
5. 积分结算 → Score 层

运行测试：
    pytest turing_test/backend/tests/integration/test_domain_flow.py -v
"""

import pytest
import asyncio
from datetime import datetime, timezone

# 先导入 Base，再导入所有模型以确保它们被注册到 Base.metadata
from turing_test.backend.database import Base, async_session_maker, get_db

# 导入所有领域模型（必须导入以确保模型被注册到 Base.metadata）
from turing_test.backend.models.domain_models import (
    BotConfig, Match, Room, RoomParticipant, Message,
    UserSession, SessionScore, ScoreBreakdownItem,
)

# 导入领域服务
from turing_test.backend.domain.services import (
    MatchAggregate, RoomAggregate, UserSessionAggregate, ScoreAggregate,
)
from turing_test.backend.domain.models import (
    MatchId, RoomId, SessionId, UserId,
    MatchStatus, OpponentType,
    RoomType, RoomStatus, ParticipantRole,
    SessionStatus, ScoreBreakdown,
)
from turing_test.backend.domain.repositories import SqlAlchemyUnitOfWork
from turing_test.backend.application.match_service import MatchApplicationService
from turing_test.backend.application.room_service import RoomApplicationService
from turing_test.backend.application.session_service import SessionApplicationService


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """创建测试数据库引擎"""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """创建数据库会话"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # 使用测试数据库引擎创建 session maker
    test_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with test_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def uow(db_session):
    """创建工作单元"""
    return SqlAlchemyUnitOfWork(db_session)


@pytest.fixture(scope="function")
async def match_service(uow):
    """创建匹配应用服务"""
    return MatchApplicationService(uow, event_bus=None)


@pytest.fixture(scope="function")
async def room_service(uow):
    """创建对话应用服务"""
    return RoomApplicationService(uow, event_bus=None)


@pytest.fixture(scope="function")
async def session_service(uow):
    """创建用户会话应用服务"""
    return SessionApplicationService(uow, event_bus=None)


class TestDomainFlow:
    """测试完整领域流程"""

    @pytest.mark.asyncio
    async def test_match_request(self, match_service, uow):
        """测试 1: 请求匹配"""
        user_id = 1
        user_score = 100
        
        # 请求匹配
        match = await match_service.request_match(
            user_id=user_id,
            user_score=user_score,
            preferences={"bot_type": "normal"},
        )
        
        # 验证
        assert match is not None
        assert match.user_id.value == user_id
        assert match.status == MatchStatus.PENDING
        assert match.request.user_score == user_score
        
        # 验证数据库中有记录
        stored_match = await uow.matches.get(match.id)
        assert stored_match is not None
        assert stored_match.id.value == match.id.value

    @pytest.mark.asyncio
    async def test_create_room(self, room_service, uow):
        """测试 2: 创建对话空间"""
        # 创建对话
        room = await room_service.create_room(
            match_id=None,
            room_type=RoomType.HUMAN_VS_BOT,
        )
        
        # 验证
        assert room is not None
        assert room.room_type == RoomType.HUMAN_VS_BOT
        assert room.status == RoomStatus.ACTIVE
        
        # 验证数据库中有记录
        stored_room = await uow.rooms.get(room.id)
        assert stored_room is not None
        assert stored_room.id.value == room.id.value

    @pytest.mark.asyncio
    async def test_add_participant(self, room_service, uow):
        """测试 3: 添加参与者"""
        # 创建对话
        room = await room_service.create_room(room_type=RoomType.HUMAN_VS_BOT)
        
        # 添加用户参与者
        user_id = 1
        success = await room_service.add_participant(
            room_id=str(room.id),
            user_id=user_id,
            role=ParticipantRole.USER,
        )
        
        assert success is True
        
        # 验证
        stored_room = await uow.rooms.get(room.id)
        assert len(stored_room.participants) == 1
        assert stored_room.participants[0].user_id.value == user_id

    @pytest.mark.asyncio
    async def test_send_message(self, room_service, uow):
        """测试 4: 发送消息"""
        # 创建对话
        room = await room_service.create_room(room_type=RoomType.HUMAN_VS_BOT)
        
        # 添加参与者
        user_id = 1
        await room_service.add_participant(
            room_id=str(room.id),
            user_id=user_id,
            role=ParticipantRole.USER,
        )
        
        # 发送消息
        message = await room_service.send_message(
            room_id=str(room.id),
            sender_id=user_id,
            sender_type="user",
            content="你好，请问你是真人还是 AI？",
            is_meta=True,
            meta_keyword="你是真人",
        )
        
        # 验证
        assert message is not None
        assert message.room_id == int(room.id.value)
        assert message.sender_id == user_id
        assert message.content == "你好，请问你是真人还是 AI？"
        assert message.is_meta is True
        assert message.meta_keyword == "你是真人"
        
        # 验证对话统计
        stored_room = await uow.rooms.get(room.id)
        assert stored_room.total_turns == 1
        assert stored_room.meta_count == 1

    @pytest.mark.asyncio
    async def test_create_session(self, session_service, uow):
        """测试 5: 创建用户会话"""
        # 创建对话
        room_service = RoomApplicationService(uow, event_bus=None)
        room = await room_service.create_room(room_type=RoomType.HUMAN_VS_BOT)
        
        # 创建用户会话
        user_id = 1
        session = await session_service.create_session(
            user_id=user_id,
            room_id=str(room.id),
            match_id=None,
        )
        
        # 验证
        assert session is not None
        assert session.user_id.value == user_id
        assert session.room_id.value == room.id.value
        assert session.status == SessionStatus.ACTIVE
        assert session.turn_state.is_user_turn is True
        
        # 验证数据库中有记录
        stored_session = await uow.user_sessions.get(session.id)
        assert stored_session is not None

    @pytest.mark.asyncio
    async def test_update_turn(self, session_service, uow):
        """测试 6: 更新回合"""
        # 创建对话和会话
        room_service = RoomApplicationService(uow, event_bus=None)
        room = await room_service.create_room(room_type=RoomType.HUMAN_VS_BOT)
        
        user_id = 1
        session = await session_service.create_session(
            user_id=user_id,
            room_id=str(room.id),
        )
        
        # 更新回合
        success = await session_service.update_turn(
            session_id=str(session.id),
            is_user_turn=False,
            increment_turn=True,
        )
        
        assert success is True
        
        # 验证
        stored_session = await uow.user_sessions.get(session.id)
        assert stored_session.turn_state.total_turns == 1
        assert stored_session.turn_state.is_user_turn is False

    @pytest.mark.asyncio
    async def test_submit_judgment(self, session_service, uow):
        """测试 7: 提交判断"""
        # 创建对话和会话
        room_service = RoomApplicationService(uow, event_bus=None)
        room = await room_service.create_room(room_type=RoomType.HUMAN_VS_BOT)
        
        user_id = 1
        session = await session_service.create_session(
            user_id=user_id,
            room_id=str(room.id),
        )
        
        # 提交判断
        success = await session_service.submit_judgment(
            session_id=str(session.id),
            user_guess="ai",
            confidence="mid",
            is_mid_game=False,
        )
        
        assert success is True
        
        # 验证
        stored_session = await uow.user_sessions.get(session.id)
        assert stored_session.judgment is not None
        assert stored_session.judgment.user_guess == "ai"
        assert stored_session.judgment.confidence == "mid"

    @pytest.mark.asyncio
    async def test_settle_score(self, session_service, uow):
        """测试 8: 积分结算"""
        # 创建对话和会话
        room_service = RoomApplicationService(uow, event_bus=None)
        room = await room_service.create_room(room_type=RoomType.HUMAN_VS_BOT)
        
        user_id = 1
        session = await session_service.create_session(
            user_id=user_id,
            room_id=str(room.id),
        )
        
        # 提交判断
        await session_service.submit_judgment(
            session_id=str(session.id),
            user_guess="ai",
            confidence="mid",
        )
        
        # 结算积分
        success = await session_service.settle_score(
            session_id=str(session.id),
            base_score=10,
            confidence_multiplier=2.5,
            meta_multiplier=1.0,
            mid_game_multiplier=1.0,
            entry_fee=2,
            turn_penalty=0,
            opponent_bonus=0,
        )
        
        assert success is True
        
        # 验证
        stored_session = await uow.user_sessions.get(session.id)
        assert stored_session.score is not None
        assert stored_session.score.breakdown.final_score == 23  # 10 * 2.5 - 2 = 23
        assert stored_session.score_settled is True

    @pytest.mark.asyncio
    async def test_full_flow(self, uow):
        """测试 9: 完整流程测试"""
        # 初始化所有服务
        match_service = MatchApplicationService(uow, event_bus=None)
        room_service = RoomApplicationService(uow, event_bus=None)
        session_service = SessionApplicationService(uow, event_bus=None)
        
        user_id = 1
        user_score = 100
        
        # 1. 请求匹配
        match = await match_service.request_match(
            user_id=user_id,
            user_score=user_score,
        )
        print(f"✓ 匹配请求成功：match_id={match.id}")
        
        # 2. 创建对话
        room = await room_service.create_room(
            match_id=str(match.id),
            room_type=RoomType.HUMAN_VS_BOT,
        )
        print(f"✓ 对话创建成功：room_id={room.id}")
        
        # 3. 完成匹配
        success = await match_service.complete_match(
            match_id=str(match.id),
            room_id=str(room.id),
            opponent_type=OpponentType.BOT,
            bot_config_id=1,
            bot_level="lv2_typical",
        )
        assert success is True
        print(f"✓ 匹配完成")
        
        # 4. 添加参与者
        await room_service.add_participant(
            room_id=str(room.id),
            user_id=user_id,
            role=ParticipantRole.USER,
        )
        await room_service.add_participant(
            room_id=str(room.id),
            user_id=None,
            role=ParticipantRole.BOT,
            bot_config_id=1,
            bot_level="lv2_typical",
        )
        print(f"✓ 参与者已添加")
        
        # 5. 创建用户会话
        session = await session_service.create_session(
            user_id=user_id,
            room_id=str(room.id),
            match_id=str(match.id),
        )
        print(f"✓ 用户会话创建成功：session_id={session.id}")
        
        # 6. 发送消息
        await room_service.send_message(
            room_id=str(room.id),
            sender_id=user_id,
            sender_type="user",
            content="你好",
        )
        await room_service.send_message(
            room_id=str(room.id),
            sender_id=None,
            sender_type="bot",
            content="你好，我是 AI 助手",
        )
        print(f"✓ 消息已发送")
        
        # 7. 提交判断
        await session_service.submit_judgment(
            session_id=str(session.id),
            user_guess="ai",
            confidence="high",
        )
        print(f"✓ 判断已提交")
        
        # 8. 结算积分
        await session_service.settle_score(
            session_id=str(session.id),
            base_score=10,
            confidence_multiplier=5.0,  # high = 5.0
            entry_fee=2,
        )
        print(f"✓ 积分已结算")
        
        # 9. 结束会话
        await session_service.end_session(
            session_id=str(session.id),
            end_reason="user_normal_end",
        )
        print(f"✓ 会话已结束")
        
        # 10. 结束对话
        await room_service.end_room(
            room_id=str(room.id),
            end_reason="user_normal_end",
        )
        print(f"✓ 对话已结束")
        
        # 验证最终状态
        final_session = await uow.user_sessions.get(session.id)
        assert final_session.status == SessionStatus.ENDED
        assert final_session.score.breakdown.final_score == 48  # 10 * 5.0 - 2 = 48
        
        print("\n✅ 完整流程测试通过!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
