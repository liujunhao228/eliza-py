"""
API 限流中间件

使用 slowapi 实现基于 IP 的速率限制，防止 API 滥用。

配置说明:
    - 开发环境：使用内存存储
    - 生产环境：使用 Redis 存储（通过环境变量 CONFIG_RATE_LIMIT_STORAGE 配置）

环境变量:
    CONFIG_RATE_LIMIT_STORAGE: Redis 连接 URL，如 "redis://localhost:6379"
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from loguru import logger

from config import settings

# 指定 UTF-8 编码加载 .env 文件，解决 Windows 上 GBK 编码问题
load_dotenv('.env', encoding='utf-8')


# =============================================================================
# 限流器配置
# =============================================================================

class RateLimiterConfig:
    """限流器配置"""
    
    # 默认限流策略
    DEFAULT_LIMIT: str = "100/minute"  # 每分钟 100 次请求
    
    # 不同端点的限流策略
    ENDPOINT_LIMITS: Dict[str, str] = {
        # 认证端点 - 更严格的限制（防止暴力破解）
        "POST /api/auth/login": "10/minute",
        "POST /api/auth/register": "5/minute",
        
        # 邀请码端点 - 中等限制
        "POST /api/invite-codes/*": "20/minute",
        "GET /api/invite-codes/*": "30/minute",
        
        # 匹配端点 - 中等限制
        "POST /api/match/*": "30/minute",
        
        # 聊天端点 - 较宽松的限制
        "POST /api/chat/*": "60/minute",
        
        # 健康检查 - 宽松限制
        "GET /health": "30/minute",
        
        # WebSocket 连接 - 严格限制
        "WS /*": "10/minute",
    }
    
    # 信任的代理头（用于获取真实 IP）
    TRUSTED_PROXIES: bool = True
    PROXY_HEADERS: list = None
    
    @classmethod
    def get_proxy_headers(cls) -> Optional[list]:
        """获取代理头配置"""
        if cls.PROXY_HEADERS is None:
            cls.PROXY_HEADERS = [
                "X-Forwarded-For",
                "X-Real-IP",
            ]
        return cls.PROXY_HEADERS if cls.TRUSTED_PROXIES else None


# =============================================================================
# 限流器设置
# =============================================================================

def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP

    支持通过代理头获取真实 IP（在部署到云环境时很有用）
    """
    # 首先尝试从请求头获取
    proxy_headers = RateLimiterConfig.get_proxy_headers()
    if proxy_headers:
        for header in proxy_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For 可能包含多个 IP，取第一个
                return ip.split(",")[0].strip()

    # 回退到默认方法
    return get_remote_address(request)


# =============================================================================
# 限流器存储配置
# =============================================================================

def get_storage_uri() -> str:
    """
    获取限流器存储 URI

    优先级:
    1. 环境变量 CONFIG_RATE_LIMIT_STORAGE
    2. 配置文件 settings.turing.rate_limit.storage
    3. 默认使用内存存储

    Returns:
        存储 URI 字符串
    """
    # 环境变量优先级最高
    env_storage = os.getenv("CONFIG_RATE_LIMIT_STORAGE")
    if env_storage:
        logger.info(f"使用环境变量配置的限流存储：{env_storage}")
        return env_storage

    # 尝试从配置文件读取
    try:
        config_storage = getattr(settings.turing, 'rate_limit', {}).get('storage')
        if config_storage:
            logger.info(f"使用配置文件配置的限流存储：{config_storage}")
            return config_storage
    except (AttributeError, TypeError):
        pass

    # 默认使用内存存储（开发环境）
    logger.warning("⚠️  限流存储使用内存模式，多实例部署请配置 Redis: "
                   "CONFIG_RATE_LIMIT_STORAGE=redis://localhost:6379")
    return "memory://"


# 创建限流器实例
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[RateLimiterConfig.DEFAULT_LIMIT],
    storage_uri=get_storage_uri(),  # 动态获取存储配置
)


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    自定义限流异常处理器
    
    返回友好的错误信息，并包含重试时间
    """
    logger.warning(
        f"限流触发：{request.method} {request.url.path} "
        f"IP: {get_client_ip(request)}"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "请求过于频繁，请稍后再试",
            "retry_after": getattr(exc, 'retry_after', None),
        }
    )


def setup_rate_limiter(app: FastAPI) -> None:
    """
    设置限流中间件
    
    Args:
        app: FastAPI 应用实例
    """
    # 添加限流器到应用状态
    app.state.limiter = limiter
    
    # 注册限流异常处理器
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
    
    # 添加限流中间件
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("✅ 限流中间件已启用")


# =============================================================================
# 限流装饰器
# =============================================================================

def rate_limit(limit: str, endpoint_name: Optional[str] = None):
    """
    自定义限流装饰器
    
    用于为特定端点设置不同的限流策略
    
    Args:
        limit: 限流字符串，如 "10/minute", "100/hour"
        endpoint_name: 端点名称（用于日志）
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        # 设置限流属性
        func.__rate_limit__ = limit
        func.__endpoint_name__ = endpoint_name
        
        # 应用 slowapi 限流
        return limiter.limit(limit)(func)
    
    return decorator


# =============================================================================
# 端点特定限流
# =============================================================================

def apply_endpoint_limits(app: FastAPI) -> None:
    """
    为特定端点应用限流配置
    
    这会覆盖默认的限流设置
    """
    # 注意：由于 FastAPI 路由在 main.py 中注册，
    # 限流装饰器需要在路由定义时应用
    # 这里仅提供配置信息
    
    logger.info(f"📊 限流配置：默认 {RateLimiterConfig.DEFAULT_LIMIT}")
    for endpoint, limit in RateLimiterConfig.ENDPOINT_LIMITS.items():
        logger.debug(f"   - {endpoint}: {limit}")
