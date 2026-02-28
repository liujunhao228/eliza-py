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
import os
from pathlib import Path
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
    # 提取相对路径并转换为绝对路径
    # sqlite:///data/turing.db -> data/turing.db
    # sqlite:////app/data/turing.db -> /app/data/turing.db (已经是绝对路径)
    db_path = database_url.replace("sqlite:///", "")
    
    logger.info(f"[DEBUG] 原始数据库路径：{db_path}")
    logger.info(f"[DEBUG] 当前工作目录：{Path.cwd()}")
    logger.info(f"[DEBUG] PROJECT_ROOT 环境变量：{os.getenv('PROJECT_ROOT', '未设置')}")

    # 如果是相对路径，转换为绝对路径（相对于项目根目录）
    if not db_path.startswith("/"):
        # 优先使用环境变量 PROJECT_ROOT，其次使用当前文件所在目录的父目录
        # 避免 uv run 时工作目录变化导致路径解析错误
        project_root = os.getenv("PROJECT_ROOT")
        if project_root:
            project_root = Path(project_root)
            logger.info(f"[DEBUG] 使用环境变量 PROJECT_ROOT: {project_root}")
        else:
            # 使用 __file__ 定位项目根目录 (turing_test/backend/database.py -> turing_test -> project_root)
            project_root = Path(__file__).resolve().parent.parent.parent
            logger.info(f"[DEBUG] 使用 __file__ 定位项目根目录：{project_root}")
        db_path = str(project_root / db_path)
        logger.info(f"[DEBUG] 计算后的绝对路径：{db_path}")

    database_url = f"sqlite+aiosqlite:///{db_path}"
    logger.info(f"[DEBUG] 最终数据库 URL: {database_url}")

    # 确保数据库目录存在
    db_dir = Path(db_path).parent
    logger.info(f"[DEBUG] 数据库目录：{db_dir}")
    logger.info(f"[DEBUG] 数据库目录是否存在：{db_dir.exists()}")
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ SQLite 数据库目录已确保存在：{db_dir}")
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
    logger.info("正在关闭数据库连接...")

    # 处置引擎，这将关闭所有连接池连接
    # 注意：async_sessionmaker 只是工厂，不需要显式关闭
    try:
        await engine.dispose()
        logger.debug("数据库引擎已处置")
    except Exception as e:
        logger.warning(f"处置数据库引擎时出错：{e}")

    logger.info("✅ 数据库连接已关闭")
