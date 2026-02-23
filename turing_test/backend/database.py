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

# 创建异步引擎
engine = create_async_engine(
    database_url,
    echo=settings.debug,  # 调试模式下打印 SQL
    future=True,
)

# 创建 Session 工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期对象
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
