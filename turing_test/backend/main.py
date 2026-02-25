"""
FastAPI 应用主入口

图灵测试后端 API 服务。
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# =============================================================================
# 导入模块
# =============================================================================

# 动态获取项目根目录，以便导入统一的 config 模块
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 使用统一的配置模块
from config import settings

# 使用绝对导入
from turing_test.backend.database import init_db, close_db, get_db, async_session_maker
from turing_test.backend.schemas import (
    HealthResponse,
    ErrorResponse,
)

# 导入中间件模块
from turing_test.backend.middleware import (
    setup_rate_limiter,
    setup_request_logger,
    setup_error_tracker,
)

# =============================================================================
# 生命周期管理
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info(f"🚀 启动 {settings.turing.ai_bot.name} v0.1.0")
    logger.info(f"📊 数据库 URL: {settings.turing.database.url}")
    logger.info(f"🔧 Debug 模式：{settings.debug}")

    # 初始化数据库
    try:
        await init_db()
        logger.info("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败：{e}")
        raise

    # 初始化 AI Bot 池
    try:
        from turing_test.backend.services.ai_bot_service import get_ai_bot_service
        ai_bot_service = await get_ai_bot_service()
        stats = ai_bot_service.get_pool_stats()
        logger.info(f"✅ 机器人池初始化成功，实例数：{stats.get('total_instances', 0)}")
    except Exception as e:
        logger.error(f"❌ 机器人池初始化失败：{e}")
        # 不阻止启动，但记录错误

    # 启动 WebSocket 心跳监控
    from turing_test.backend.websocket.manager import manager
    await manager.start_heartbeat_monitor()
    logger.info("✅ WebSocket 心跳监控已启动")

    yield

    # 关闭时清理
    logger.info("🔄 正在关闭应用...")

    # 停止 WebSocket 心跳监控
    await manager.stop_heartbeat_monitor()

    # 关闭 AI Bot 池
    try:
        from turing_test.backend.services.ai_bot_service import shutdown_ai_bot_service
        await shutdown_ai_bot_service()
        logger.info("✅ 机器人池已关闭")
    except Exception as e:
        logger.error(f"❌ 机器人池关闭失败：{e}")

    await close_db()
    logger.info("✅ 应用已关闭")


# =============================================================================
# 创建 FastAPI 应用
# =============================================================================

app = FastAPI(
    title="Turing Test Backend",
    version="0.1.0",
    description="图灵测试社交实验平台后端 API",
    lifespan=lifespan,
    debug=settings.debug,
)

# =============================================================================
# 配置 CORS
# =============================================================================

# 允许的前端域名（可在 config.yaml 中配置）
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 配置中间件
# =============================================================================

# 设置请求日志中间件
setup_request_logger(app)

# 设置限流中间件
setup_rate_limiter(app)

# 设置错误追踪中间件（Sentry）
setup_error_tracker(app)

# =============================================================================
# 健康检查
# =============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["系统"],
    summary="健康检查",
    description="检查服务运行状态",
)
async def health_check():
    """健康检查端点"""
    # 检查数据库连接
    db_connected = False
    try:
        async with async_session_maker() as session:
            # 执行一个简单的查询测试连接
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            db_connected = True
    except Exception as e:
        logger.warning(f"数据库连接检查失败：{e}")

    # 获取 WebSocket 连接数
    from turing_test.backend.websocket.manager import manager
    ws_connections = manager.get_online_count()

    # 获取 NLP 服务状态
    try:
        from turing_test.backend.services.nlp_service import get_nlp_service
        nlp_service = get_nlp_service()
        nlp_status = nlp_service.get_status()
    except Exception as e:
        logger.warning(f"获取 NLP 服务状态失败：{e}")
        nlp_status = None

    # 获取 Bot 池状态
    bot_pool_size = 0
    try:
        from turing_test.backend.services.ai_bot_service import get_ai_bot_service
        ai_bot_service = await get_ai_bot_service()
        stats = ai_bot_service.get_pool_stats()
        bot_pool_size = stats.get('total_instances', 0)
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        version="0.1.0",
        database_connected=db_connected,
        bot_pool_size=bot_pool_size,
    )


@app.get(
    "/",
    tags=["系统"],
    summary="根路径",
    description="API 根路径，返回基本信息",
)
async def root():
    """根路径"""
    return {
        "app": "Turing Test Backend",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


# =============================================================================
# 异常处理
# =============================================================================

from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常：{exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误" if not settings.debug else str(exc),
        }
    )


# =============================================================================
# API 路由
# =============================================================================

# 认证路由
from turing_test.backend.api.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])

# 邀请码管理路由
from turing_test.backend.api.invite_code import router as invite_code_router
app.include_router(invite_code_router, prefix="/api/invite-codes", tags=["邀请码管理"])

# 匹配路由
from turing_test.backend.api.match import router as match_router
app.include_router(match_router, prefix="/api/match", tags=["匹配"])

# 用户路由
from turing_test.backend.api.user import router as user_router
app.include_router(user_router, prefix="/api/user", tags=["用户"])

# 游戏路由（积分博弈）
from turing_test.backend.api.game import router as game_router
app.include_router(game_router, prefix="/api", tags=["游戏"])

# 分析路由（数据埋点）
from turing_test.backend.api.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/analytics", tags=["数据分析"])

# 历史会话路由
from turing_test.backend.api.history import router as history_router
app.include_router(history_router, prefix="/api", tags=["历史会话"])

# 分享会话路由
from turing_test.backend.api.share import router as share_router
app.include_router(share_router, prefix="/api", tags=["分享会话"])

# WebSocket 路由
from turing_test.backend.websocket.match import router as match_ws_router
from turing_test.backend.websocket.chat import router as chat_ws_router
app.include_router(match_ws_router, prefix="/ws", tags=["WebSocket"])
app.include_router(chat_ws_router, prefix="/ws", tags=["WebSocket"])

# 聊天路由（待实现）
# from api.chat import router as chat_router
# app.include_router(chat_router, prefix="/api/chat", tags=["聊天"])


# =============================================================================
# 开发模式下的额外配置
# =============================================================================

if settings.debug:
    logger.warning("⚠️  Debug 模式已启用，生产环境请关闭！")
    logger.warning("⚠️  API 文档可在 /docs 访问")
