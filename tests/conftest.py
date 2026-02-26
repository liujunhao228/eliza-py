"""
Pytest 全局 Fixture

提供测试所需的通用 fixture。
"""

import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from turing_test.backend.database import Base, get_db
from turing_test.backend.main import app
from config import settings


# =============================================================================
# 数据库 Fixture
# =============================================================================

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """获取测试数据库 URL（使用内存 SQLite）"""
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine(test_database_url: str):
    """创建测试数据库引擎"""
    return create_async_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话（每个测试函数）"""
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        # 删除所有表
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session_per_test(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """为每个测试创建独立的数据库会话"""
    yield db_session


# =============================================================================
# HTTP 客户端 Fixture
# =============================================================================

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试 HTTP 客户端"""

    # 覆盖数据库依赖
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# 认证 Fixture
# =============================================================================

@pytest.fixture
def auth_headers(test_user) -> dict:
    """生成认证头"""
    from jose import jwt
    from config import settings

    token = jwt.encode(
        {"sub": str(test_user.id)},
        settings.turing.auth.secret_key,
        algorithm=settings.turing.auth.algorithm
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 测试用户 Fixture
# =============================================================================

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """创建测试用户"""
    from turing_test.backend.models import User
    
    user = User(
        username="test_user",
        invite_code="test_invite_001",
        score=100,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_session(db_session: AsyncSession, test_user):
    """创建测试会话"""
    from turing_test.backend.models import Session
    
    session = Session(
        user_id=test_user.id,
        opponent_type="human",
        is_honeypot=False,
        turn_count=5,
        meta_conversation_count=2,
        final_score=10,
        is_correct=True,
        confidence_level="high",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def test_messages(db_session: AsyncSession, test_session) -> list:
    """创建测试消息"""
    from turing_test.backend.models import Message
    
    messages = [
        Message(
            session_id=test_session.id,
            sender="user",
            content="你好",
            is_meta_conversation=False,
        ),
        Message(
            session_id=test_session.id,
            sender="opponent",
            content="你好啊！",
            is_meta_conversation=False,
        ),
        Message(
            session_id=test_session.id,
            sender="user",
            content="你是真人吗？",
            is_meta_conversation=True,
            meta_keyword="identity",
        ),
    ]
    db_session.add_all(messages)
    await db_session.commit()
    return messages
