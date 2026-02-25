"""
数据库连接和 Session 管理

使用 SQLAlchemy 2.0+ 的异步模式。
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


# =============================================================================
# 数据库引擎
# =============================================================================

# 将 SQLite URL 转换为异步格式
database_url = settings.turing.database.url
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    # SQLite 不支持连接池参数，使用默认配置
    engine = create_async_engine(
        database_url,
        echo=settings.debug,  # 调试模式下打印 SQL
        future=True,
        # SQLite 连接池配置（使用 NullPool 避免兼容性问题）
        connect_args={"check_same_thread": False},
    )
else:
    # 其他数据库（PostgreSQL, MySQL）使用连接池优化
    engine = create_async_engine(
        database_url,
        echo=settings.debug,
        future=True,
        # 连接池配置
        pool_size=20,          # 连接池大小（默认 5，根据并发需求调整）
        max_overflow=40,       # 最大溢出连接数（超出 pool_size 后可创建的连接数）
        pool_pre_ping=True,    # 连接前测试，避免使用失效的连接
        pool_recycle=3600,     # 连接回收时间（秒），避免连接超时
        pool_timeout=30,       # 获取连接超时时间（秒）
    )

# 创建 Session 工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期对象
    autocommit=False,        # 不自动提交
    autoflush=False,         # 不自动刷新
)


# =============================================================================
# 基类
# =============================================================================

class Base(DeclarativeBase):
    """所有模型的基础类"""

    pass


# =============================================================================
# Session 依赖
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库 Session

    用于 FastAPI 依赖注入：

    ```python
    @app.get("/users/{id}")
    async def get_user(id: int, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()
    ```
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# 数据库初始化
# =============================================================================

async def init_db():
    """
    初始化数据库表结构

    注意：生产环境应使用 Alembic 迁移，不建议直接调用此函数。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
