"""
请求日志中间件

记录所有 HTTP 请求的详细信息，包括请求时间、响应时间、状态码等。
"""

import time
import json
from typing import Callable, Awaitable
from fastapi import FastAPI, Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


# =============================================================================
# 配置
# =============================================================================

class RequestLoggerConfig:
    """请求日志配置"""
    
    # 是否启用日志
    ENABLED: bool = True
    
    # 是否记录请求体
    LOG_REQUEST_BODY: bool = False
    
    # 是否记录响应体
    LOG_RESPONSE_BODY: bool = False
    
    # 请求体最大记录长度（超过则截断）
    MAX_BODY_LENGTH: int = 1000
    
    # 需要忽略的路径（不记录日志）
    IGNORE_PATHS: list = None
    
    # 需要忽略的 HTTP 方法
    IGNORE_METHODS: list = None
    
    # 慢请求阈值（毫秒）
    SLOW_REQUEST_THRESHOLD: int = 1000
    
    @classmethod
    def get_ignore_paths(cls) -> list:
        """获取需要忽略的路径"""
        if cls.IGNORE_PATHS is None:
            cls.IGNORE_PATHS = [
                "/health",
                "/docs",
                "/redoc",
                "/openapi.json",
            ]
        return cls.IGNORE_PATHS
    
    @classmethod
    def get_ignore_methods(cls) -> list:
        """获取需要忽略的 HTTP 方法"""
        if cls.IGNORE_METHODS is None:
            cls.IGNORE_METHODS = ["OPTIONS", "HEAD"]
        return cls.IGNORE_METHODS


# =============================================================================
# 请求日志中间件
# =============================================================================

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    记录每个请求的详细信息：
    - 请求方法、路径、IP
    - 请求头（敏感信息已脱敏）
    - 请求体（可选）
    - 响应状态码、大小
    - 响应时间
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """处理请求"""
        
        # 检查是否需要忽略
        if self._should_ignore(request):
            return await call_next(request)
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求信息
        request_info = self._extract_request_info(request)
        
        # 记录请求日志
        logger.info(
            f"📥 请求开始 | "
            f"{request_info['method']} {request_info['path']} | "
            f"IP: {request_info['client_ip']} | "
            f"Request ID: {request_info['request_id']}"
        )
        
        # 记录请求体（如果启用）
        if RequestLoggerConfig.LOG_REQUEST_BODY and request_info.get("body"):
            logger.debug(f"请求体：{request_info['body']}")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000  # 毫秒
            
            # 提取响应信息
            response_info = {
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
                "content_length": int(response.headers.get("content-length", 0)),
            }
            
            # 记录响应日志
            log_level = self._get_log_level(response.status_code, process_time)
            log_message = (
                f"📤 请求完成 | "
                f"{request_info['method']} {request_info['path']} | "
                f"Status: {response_info['status_code']} | "
                f"Time: {response_info['process_time_ms']}ms | "
                f"Size: {response_info['content_length']}B"
            )
            
            # 根据状态码和处理时间选择日志级别
            if log_level == "warning":
                logger.warning(log_message)
            elif log_level == "error":
                logger.error(log_message)
            else:
                logger.info(log_message)
            
            # 记录慢请求
            if process_time > RequestLoggerConfig.SLOW_REQUEST_THRESHOLD:
                logger.warning(
                    f"🐢 慢请求警告 | "
                    f"{request_info['method']} {request_info['path']} | "
                    f"耗时：{process_time:.2f}ms"
                )
            
            # 添加响应头（用于调试）
            response.headers["X-Process-Time"] = str(round(process_time, 2))
            response.headers["X-Request-ID"] = request_info["request_id"]
            
            return response
            
        except Exception as e:
            # 记录异常
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"❌ 请求异常 | "
                f"{request_info['method']} {request_info['path']} | "
                f"Time: {process_time:.2f}ms | "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def _should_ignore(self, request: Request) -> bool:
        """检查是否应该忽略此请求"""
        if not RequestLoggerConfig.ENABLED:
            return True
        
        # 检查路径
        if request.url.path in RequestLoggerConfig.get_ignore_paths():
            return True
        
        # 检查方法
        if request.method in RequestLoggerConfig.get_ignore_methods():
            return True
        
        return False
    
    def _extract_request_info(self, request: Request) -> dict:
        """提取请求信息"""
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)
        
        # 生成请求 ID
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
        
        info = {
            "method": request.method,
            "path": str(request.url.path),
            "query": str(request.url.query) if request.url.query else None,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "request_id": request_id,
            "content_type": request.headers.get("content-type", None),
            "content_length": int(request.headers.get("content-length", 0)),
        }
        
        return info
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        # 尝试从代理头获取
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 回退到直接连接
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_log_level(self, status_code: int, process_time: float) -> str:
        """根据状态码和处理时间确定日志级别"""
        if status_code >= 500:
            return "error"
        elif status_code >= 400 or process_time > RequestLoggerConfig.SLOW_REQUEST_THRESHOLD:
            return "warning"
        return "info"


# =============================================================================
# 敏感信息脱敏
# =============================================================================

def sanitize_headers(headers: dict) -> dict:
    """
    脱敏请求头中的敏感信息
    
    Args:
        headers: 原始请求头字典
    
    Returns:
        脱敏后的请求头字典
    """
    sensitive_keys = [
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    ]
    
    sanitized = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_body(body: str, max_length: int = None) -> str:
    """
    脱敏请求体中的敏感信息
    
    Args:
        body: 原始请求体
        max_length: 最大记录长度
    
    Returns:
        脱敏后的请求体
    """
    if max_length is None:
        max_length = RequestLoggerConfig.MAX_BODY_LENGTH
    
    if len(body) > max_length:
        body = body[:max_length] + "... (truncated)"
    
    # 尝试解析 JSON 并脱敏敏感字段
    try:
        data = json.loads(body)
        sensitive_fields = [
            "password",
            "token",
            "secret",
            "api_key",
            "apikey",
            "auth",
            "credential",
        ]
        
        for field in sensitive_fields:
            if field in data:
                data[field] = "***REDACTED***"
        
        return json.dumps(data, ensure_ascii=False)
    except json.JSONDecodeError:
        return body


# =============================================================================
# 设置函数
# =============================================================================

def setup_request_logger(app: FastAPI) -> None:
    """
    设置请求日志中间件
    
    Args:
        app: FastAPI 应用实例
    """
    if RequestLoggerConfig.ENABLED:
        app.add_middleware(RequestLoggerMiddleware)
        logger.info("✅ 请求日志中间件已启用")
        
        # 记录配置信息
        logger.debug(f"   - 记录请求体：{RequestLoggerConfig.LOG_REQUEST_BODY}")
        logger.debug(f"   - 记录响应体：{RequestLoggerConfig.LOG_RESPONSE_BODY}")
        logger.debug(f"   - 慢请求阈值：{RequestLoggerConfig.SLOW_REQUEST_THRESHOLD}ms")
        logger.debug(f"   - 忽略路径：{RequestLoggerConfig.get_ignore_paths()}")
    else:
        logger.info("⚠️  请求日志中间件已禁用")
