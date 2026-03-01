"""
FastAPI 应用主入口

图灵测试后端 API 服务。
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List
from datetime import datetime
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

    # 启动会话超时清理任务
    from turing_test.backend.services.session_state import session_state_manager
    await session_state_manager.start()
    logger.info("✅ 会话超时清理任务已启动")

    # 初始化匹配服务
    try:
        from turing_test.backend.services.match_service import (
            MatchService, MatchConfig, set_match_service, get_match_service
        )
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        from sqlalchemy import select
        from datetime import datetime, timezone

        match_service = MatchService(MatchConfig())

        # 注入会话创建器（异步非阻塞）
        class SessionCreator:
            """会话创建器（用于匹配服务注入）"""

            async def create_session(self, safe_result, user_id: int) -> None:
                """
                根据匹配结果创建会话（异步非阻塞）

                Args:
                    safe_result: 安全匹配结果（SafeMatchResult）
                    user_id: 用户 ID
                """
                try:
                    # 获取内部结果（包含完整信息）
                    match_service_instance = get_match_service()
                    internal_result = await match_service_instance.get_result_internal(user_id)

                    if not internal_result:
                        logger.error(f"无法获取用户 {user_id} 的内部匹配结果")
                        return

                    # 如果 session_id 已有值，说明会话已创建，跳过
                    if internal_result.session_id > 0:
                        logger.info(f"用户 {user_id} 会话已存在：session_id={internal_result.session_id}")
                        return

                    async with async_session_maker() as session:
                        # 解析真实身份信息
                        true_identity = internal_result.true_identity or ""
                        bot_level = None

                        if true_identity.startswith("Bot_"):
                            # 从 true_identity 提取 Bot 等级
                            bot_level = true_identity.replace("Bot_", "").lower()
                        elif true_identity.startswith("Honeypot_"):
                            # 钓鱼 Bot
                            pass
                        elif true_identity == "Human":
                            # 真人匹配
                            pass

                        # 创建会话记录
                        db_session = Session(
                            user_id=user_id,
                            opponent_type=internal_result.opponent_type,
                            true_identity=true_identity,
                            bot_level=bot_level,
                            is_honeypot=internal_result.is_honeypot or False,
                            opponent_user_id=internal_result.opponent_user_id,
                            ended_at=None,
                        )
                        session.add(db_session)
                        await session.commit()
                        await session.refresh(db_session)

                        # 更新内部结果中的 session_id
                        internal_result.session_id = db_session.id

                        # ✅ 重要：将更新后的结果存回 result_manager
                        # 这样前端轮询时才能获取到最新的 session_id
                        await match_service_instance.coordinator.result_manager.store(
                            user_id, internal_result
                        )

                        logger.info(f"创建会话：session_id={db_session.id}, user_id={user_id}")

                except Exception as e:
                    logger.error(f"创建会话失败：user_id={user_id}, error={e}", exc_info=True)

        match_service.set_session_creator(SessionCreator())

        match_service.start()  # 启动后台清理任务
        app.state.match_service = match_service
        set_match_service(match_service)  # 同时设置全局单例
        logger.info("✅ 匹配服务初始化成功")
    except Exception as e:
        logger.error(f"❌ 匹配服务初始化失败：{e}")
        raise

    yield

    # 关闭时清理
    logger.info("🔄 正在关闭应用...")

    # 停止会话超时清理任务
    try:
        from turing_test.backend.services.session_state import session_state_manager
        await session_state_manager.stop()
        logger.info("✅ 会话超时清理任务已停止")
    except Exception as e:
        logger.error(f"❌ 会话超时清理任务关闭失败：{e}")

    # 停止 WebSocket 心跳监控
    try:
        await manager.stop_heartbeat_monitor()
    except Exception as e:
        logger.error(f"❌ WebSocket 心跳监控关闭失败：{e}")

    # 停止匹配服务
    try:
        match_service = getattr(app.state, "match_service", None)
        if match_service:
            await match_service.stop()
            logger.info("✅ 匹配服务已停止")
    except Exception as e:
        logger.error(f"❌ 匹配服务关闭失败：{e}")

    # 关闭 AI Bot 池
    try:
        from turing_test.backend.services.ai_bot_service import shutdown_ai_bot_service
        await shutdown_ai_bot_service()
        logger.info("✅ 机器人池已关闭")
    except Exception as e:
        logger.error(f"❌ 机器人池关闭失败：{e}")

    # 关闭数据库
    try:
        await close_db()
        logger.info("✅ 数据库已关闭")
    except Exception as e:
        logger.error(f"❌ 数据库关闭失败：{e}")

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

# CORS 配置说明:
# - 生产环境必须通过环境变量 CONFIG_TURING_CORS_ORIGINS 显式配置允许的域名
# - 开发环境下允许 localhost 相关端口
# - 环境变量格式：逗号分隔的 URL 列表，如 "https://example.com,https://api.example.com"

import os as _os
import logging as _logging

_cors_env = _os.getenv("CONFIG_TURING_CORS_ORIGINS", "")

if _cors_env:
    # 生产环境：使用环境变量配置的域名
    CORS_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
    _logger = _logging.getLogger("uvicorn")
    _logger.info(f"生产环境 CORS 配置：允许 {len(CORS_ORIGINS)} 个域名")
else:
    # 开发环境：仅允许 localhost
    if settings.debug:
        CORS_ORIGINS = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
        # 从配置文件中读取额外配置
        try:
            extra_origins = settings.turing.cors.origins if hasattr(settings.turing, 'cors') else []
            CORS_ORIGINS.extend(extra_origins)
        except Exception:
            pass
        _logger = _logging.getLogger("uvicorn")
        _logger.warning("⚠️  开发环境 CORS 配置：允许 localhost 相关端口，生产环境必须设置 CONFIG_TURING_CORS_ORIGINS")
    else:
        # 生产环境未配置 CORS - 严格模式：拒绝所有来源
        CORS_ORIGINS = []
        _logger = _logging.getLogger("uvicorn")
        _logger.error(
            "❌ 生产环境 CORS 未配置！请在启动前设置环境变量:\n"
            "   export CONFIG_TURING_CORS_ORIGINS=\"https://your-domain.com,https://api.your-domain.com\"\n"
            "   当前将拒绝所有跨域请求"
        )

del _os

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    # 限制允许的 HTTP 方法，避免过度开放
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    # 限制允许的请求头
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
    # 暴露给客户端的响应头（包含 Set-Cookie 以支持 httpOnly Cookie 认证）
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Set-Cookie"],
    # 预检请求缓存时间（秒）
    max_age=600,
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
# 数据导出端点（用于免费服务器获取数据库）
# =============================================================================

from fastapi import Security, Query
from fastapi.security import APIKeyHeader
from starlette.responses import FileResponse
import os

API_KEY = APIKeyHeader(name="X-API-Key", auto_error=False)

# 从环境变量读取管理密钥（可选功能）
ADMIN_API_KEY = os.getenv("TURING_ADMIN_API_KEY", "")

@app.get(
    "/admin/export-data",
    tags=["数据导出"],
    summary="导出数据库文件",
    description="下载 SQLite 数据库文件（需要管理员 API Key）",
    responses={
        200: {"description": "数据库文件", "content": {"application/octet-stream": {}}},
        401: {"model": ErrorResponse, "description": "未授权"},
        404: {"model": ErrorResponse, "description": "数据库文件不存在"},
    },
)
async def export_database(
    api_key: str = Security(API_KEY),
    file: str = Query(default="turing.db", description="要下载的文件名，默认为 turing.db")
):
    """
    导出数据库文件供下载

    使用方法:
        curl -H "X-API-Key: YOUR_API_KEY" https://your-server.com/admin/export-data -o turing.db
    """
    # 如果设置了 ADMIN_API_KEY，则验证
    if ADMIN_API_KEY:
        if not api_key or api_key != ADMIN_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 API Key"
            )
    
    # 防止路径遍历攻击
    if ".." in file or file.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文件名"
        )
    
    # 数据库文件路径
    db_path = Path("data") / file

    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据库文件不存在：{file}"
        )
    
    logger.info(f"数据库导出请求 - 文件：{db_path}")
    
    return FileResponse(
        path=str(db_path),
        media_type="application/octet-stream",
        filename=file
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

# 配置路由
from turing_test.backend.api.config import router as config_router
app.include_router(config_router, prefix="/api/config", tags=["系统配置"])

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
