"""
数据库连接和 Session 管理

使用 SQLAlchemy 2.0+ 的异步模式。

安全说明:
    SQLite 的 `check_same_thread=False` 配置：
    - 在异步环境下是安全的，因为 aiosqlite 使用单一事件循环
    - 所有数据库操作通过队列序列化执行，不存在并发访问
    - 但生产环境仍建议使用 PostgreSQL 以获得更好的并发性能
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 数据库引擎
# =============================================================================

# 将 SQLite URL 转换为异步格式
database_url = settings.turing.database.url
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    # SQLite 不支持传统连接池，使用 NullPool 避免兼容性问题
    #
    # 关于 check_same_thread=False 的安全性说明:
    # - aiosqlite 使用单一事件循环，所有操作通过队列序列化
    # - 在异步环境下，同一时间只有一个操作在执行，不存在线程竞争
    # - 因此在此特定场景下，该配置是安全的
    #
    # ⚠️ 警告：生产环境建议使用 PostgreSQL 以获得：
    # - 更好的并发性能
    # - 更完善的事务支持
    # - 更好的数据持久性保证
    engine = create_async_engine(
        database_url,
        echo=settings.debug,  # 调试模式下打印 SQL
        future=True,
        poolclass=NullPool,   # 使用 NullPool 避免 SQLite 连接池问题
        connect_args={"check_same_thread": False},
    )
    logger.warning(
        "⚠️  使用 SQLite 数据库，生产环境建议迁移到 PostgreSQL。"
        "配置说明：https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#threading-pooling"
    )
else:
    # 其他数据库（PostgreSQL, MySQL）使用连接池优化
    # 从配置文件读取连接池参数
    pool_config = settings.turing.database.pool
    engine = create_async_engine(
        database_url,
        echo=settings.debug,
        future=True,
        # 连接池配置（从 config.turing.yaml 读取）
        pool_size=pool_config.size if pool_config else 20,
        max_overflow=pool_config.max_overflow if pool_config else 40,
        pool_pre_ping=True,    # 连接前测试，避免使用失效的连接
        pool_recycle=pool_config.recycle if pool_config else 3600,
        pool_timeout=pool_config.timeout if pool_config else 30,
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
