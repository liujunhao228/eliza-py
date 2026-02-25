"""
Sentry 错误追踪中间件

集成 Sentry SDK，用于生产环境错误监控和性能追踪。
"""

from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.tracing import Transaction

# 获取当前事务/跨度的函数（不同版本 API 不同）
try:
    from sentry_sdk.tracing import get_current_span
except ImportError:
    try:
        from sentry_sdk import get_current_span
    except ImportError:
        # 如果都不可用，使用 None 作为回退
        get_current_span = None


# =============================================================================
# 配置
# =============================================================================

class SentryConfig:
    """Sentry 配置"""
    
    # DSN（从环境变量获取）
    DSN: Optional[str] = None
    
    # 环境名称
    ENVIRONMENT: str = "production"
    
    # 采样率
    TRACES_SAMPLE_RATE: float = 0.1  # 10% 的请求用于性能追踪
    PROFILES_SAMPLE_RATE: float = 0.1  # 10% 的请求用于性能分析
    
    # 是否启用
    ENABLED: bool = False
    
    # 需要忽略的异常类型
    IGNORE_EXCEPTIONS: tuple = None
    
    # 最大请求体大小
    MAX_REQUEST_BODY_SIZE: str = "medium"  # "never", "small", "medium", "always"
    
    # 需要脱敏的字段
    SENSITIVE_FIELDS: list = None
    
    @classmethod
    def get_ignore_exceptions(cls) -> tuple:
        """获取需要忽略的异常类型"""
        if cls.IGNORE_EXCEPTIONS is None:
            from fastapi import HTTPException
            from starlette.exceptions import HTTPException as StarletteHTTPException
            
            # 忽略 4xx 错误
            cls.IGNORE_EXCEPTIONS = (
                HTTPException,
                StarletteHTTPException,
            )
        return cls.IGNORE_EXCEPTIONS
    
    @classmethod
    def get_sensitive_fields(cls) -> list:
        """获取需要脱敏的字段"""
        if cls.SENSITIVE_FIELDS is None:
            cls.SENSITIVE_FIELDS = [
                "password",
                "token",
                "secret",
                "api_key",
                "apikey",
                "authorization",
                "cookie",
                "credential",
            ]
        return cls.SENSITIVE_FIELDS


# =============================================================================
# 错误追踪器
# =============================================================================

class ErrorTracker:
    """错误追踪器"""
    
    _initialized: bool = False
    
    @classmethod
    def initialize(cls, dsn: Optional[str] = None, environment: str = "production") -> bool:
        """
        初始化 Sentry
        
        Args:
            dsn: Sentry DSN
            environment: 环境名称
        
        Returns:
            是否初始化成功
        """
        if cls._initialized:
            logger.warning("Sentry 已经初始化，跳过")
            return False
        
        if not dsn:
            logger.info("⚠️  Sentry DSN 未配置，错误追踪已禁用")
            return False
        
        try:
            # 配置日志集成
            logging_integration = LoggingIntegration(
                level=logging.INFO,  # 捕获 INFO 级别以上的日志
                event_level=logging.ERROR,  # 将 ERROR 级别以上的日志作为事件发送
            )
            
            # 初始化 Sentry
            sentry_sdk.init(
                dsn=dsn,
                integrations=[
                    FastApiIntegration(),
                    logging_integration,
                    SqlalchemyIntegration(),
                ],
                environment=environment,
                traces_sample_rate=SentryConfig.TRACES_SAMPLE_RATE,
                profiles_sample_rate=SentryConfig.PROFILES_SAMPLE_RATE,
                max_request_body_size=SentryConfig.MAX_REQUEST_BODY_SIZE,
                send_default_pii=False,  # 不发送个人身份信息
                ignore_errors=SentryConfig.get_ignore_exceptions(),
                before_send=cls._before_send,
                before_send_transaction=cls._before_send_transaction,
            )
            
            cls._initialized = True
            logger.info(f"✅ Sentry 错误追踪已启用 (environment={environment})")
            return True
            
        except Exception as e:
            logger.error(f"Sentry 初始化失败：{e}")
            return False
    
    @classmethod
    def _before_send(cls, event: dict, hint: dict) -> Optional[dict]:
        """
        在发送事件前处理
        
        用于脱敏敏感信息
        """
        # 脱敏请求数据
        if "request" in event:
            event["request"] = cls._sanitize_request(event["request"])
        
        # 脱敏用户数据
        if "user" in event:
            event["user"] = cls._sanitize_user(event["user"])
        
        return event
    
    @classmethod
    def _before_send_transaction(cls, transaction: dict, hint: dict) -> Optional[dict]:
        """
        在发送事务前处理
        
        用于脱敏敏感信息
        """
        # 脱敏请求数据
        if "request" in transaction:
            transaction["request"] = cls._sanitize_request(transaction["request"])
        
        return transaction
    
    @classmethod
    def _sanitize_request(cls, request_data: dict) -> dict:
        """脱敏请求数据"""
        sensitive_fields = SentryConfig.get_sensitive_fields()
        
        # 脱敏 headers
        if "headers" in request_data:
            for field in sensitive_fields:
                for key in list(request_data["headers"].keys()):
                    if field.lower() in key.lower():
                        request_data["headers"][key] = "***REDACTED***"
        
        # 脱敏 cookies
        if "cookies" in request_data:
            for field in sensitive_fields:
                for key in list(request_data["cookies"].keys()):
                    if field.lower() in key.lower():
                        request_data["cookies"][key] = "***REDACTED***"
        
        # 脱敏 data
        if "data" in request_data and isinstance(request_data["data"], dict):
            for field in sensitive_fields:
                if field in request_data["data"]:
                    request_data["data"][field] = "***REDACTED***"
        
        return request_data
    
    @classmethod
    def _sanitize_user(cls, user_data: dict) -> dict:
        """脱敏用户数据"""
        # 移除敏感字段
        sensitive_fields = ["email", "username", "ip_address"]
        for field in sensitive_fields:
            if field in user_data:
                # 哈希处理而不是完全移除
                import hashlib
                value = str(user_data[field])
                user_data[field] = hashlib.sha256(value.encode()).hexdigest()[:8]
        
        return user_data


# =============================================================================
# 上下文管理
# =============================================================================

def set_user_context(user_id: Optional[str] = None, username: Optional[str] = None):
    """
    设置用户上下文
    
    Args:
        user_id: 用户 ID
        username: 用户名
    """
    if not SentryConfig.ENABLED:
        return
    
    user_data = {}
    if user_id:
        user_data["id"] = user_id
    if username:
        user_data["username"] = username
    
    sentry_sdk.set_user(user_data)


def set_tag(key: str, value: str):
    """
    设置标签
    
    Args:
        key: 标签键
        value: 标签值
    """
    if not SentryConfig.ENABLED:
        return
    
    sentry_sdk.set_tag(key, value)


def set_context(name: str, data: dict):
    """
    设置上下文
    
    Args:
        name: 上下文名称
        data: 上下文数据
    """
    if not SentryConfig.ENABLED:
        return
    
    sentry_sdk.set_context(name, data)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", **kwargs):
    """
    添加面包屑日志
    
    Args:
        message: 日志消息
        category: 分类
        level: 日志级别
        **kwargs: 额外数据
    """
    if not SentryConfig.ENABLED:
        return
    
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        **kwargs
    )


# =============================================================================
# 异常捕获
# =============================================================================

def capture_exception(exception: Exception, **kwargs):
    """
    捕获异常
    
    Args:
        exception: 异常对象
        **kwargs: 额外上下文数据
    """
    if not SentryConfig.ENABLED:
        logger.error(f"未捕获异常：{exception}")
        return
    
    # 添加额外上下文
    for key, value in kwargs.items():
        sentry_sdk.set_extra(key, value)
    
    sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", **kwargs):
    """
    捕获消息
    
    Args:
        message: 消息内容
        level: 日志级别
        **kwargs: 额外上下文数据
    """
    if not SentryConfig.ENABLED:
        logger.info(message)
        return
    
    sentry_sdk.capture_message(message, level=level)


# =============================================================================
# 性能追踪
# =============================================================================

def start_transaction(name: str, op: str = "function") -> Optional[Transaction]:
    """
    开始事务追踪
    
    Args:
        name: 事务名称
        op: 操作类型
    
    Returns:
        事务对象
    """
    if not SentryConfig.ENABLED:
        return None
    
    return sentry_sdk.start_transaction(name=name, op=op)


def get_current_transaction() -> Optional[Transaction]:
    """获取当前事务"""
    if not SentryConfig.ENABLED:
        return None
    
    if get_current_span is None:
        return None

    return get_current_span()


# =============================================================================
# 设置函数
# =============================================================================

def setup_error_tracker(app: FastAPI, dsn: Optional[str] = None) -> bool:
    """
    设置错误追踪
    
    Args:
        app: FastAPI 应用实例
        dsn: Sentry DSN
    
    Returns:
        是否设置成功
    """
    # 从配置获取 DSN
    if dsn is None:
        try:
            from config import settings
            # 优先使用 settings.sentry_dsn
            dsn = getattr(settings, 'sentry_dsn', None)
            
            # 如果配置中未启用，检查是否传入了 DSN
            if not getattr(settings, 'sentry_enabled', False) and not dsn:
                logger.info("⚠️  Sentry DSN 未配置，错误追踪已禁用")
                logger.info("   生产环境建议配置 SENTRY_DSN 以启用错误监控")
                SentryConfig.ENABLED = False
                return False
        except Exception as e:
            logger.warning(f"读取配置失败：{e}")
            SentryConfig.ENABLED = False
            return False
    
    # 检查是否启用
    enabled = bool(dsn)
    SentryConfig.ENABLED = enabled
    
    if not enabled:
        logger.info("⚠️  Sentry DSN 未配置，错误追踪已禁用")
        logger.info("   生产环境建议配置 SENTRY_DSN 以启用错误监控")
        return False
    
    # 获取环境
    environment = "production"
    try:
        from config import settings
        environment = getattr(settings, 'environment', 'production')
        if getattr(settings, 'debug', False):
            environment = "development"
    except Exception:
        pass
    
    SentryConfig.ENVIRONMENT = environment
    
    # 初始化
    success = ErrorTracker.initialize(dsn=dsn, environment=environment)
    
    if success:
        # 添加中间件用于自动捕获请求异常
        @app.middleware("http")
        async def sentry_exception_middleware(request: Request, call_next):
            try:
                return await call_next(request)
            except Exception as e:
                # 设置请求上下文
                set_tag("request.method", request.method)
                set_tag("request.path", request.url.path)
                set_context("request", {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                })
                
                # 尝试获取用户信息
                try:
                    # 从请求头获取用户 ID（如果已认证）
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        # 这里可以解析 JWT 获取用户 ID
                        set_tag("user.authenticated", "true")
                except Exception:
                    pass
                
                # 捕获异常
                capture_exception(e)
                raise
    
    return success


# =============================================================================
# 健康检查端点增强
# =============================================================================

def add_sentry_status_endpoint(app: FastAPI):
    """
    添加 Sentry 状态端点
    
    用于检查 Sentry 是否正常工作
    """
    from fastapi import HTTPException
    
    @app.get("/sentry-debug")
    async def trigger_error():
        """触发一个测试错误用于验证 Sentry 集成"""
        if not SentryConfig.ENABLED:
            raise HTTPException(
                status_code=500,
                detail="Sentry 未启用"
            )
        
        capture_message("Sentry 测试消息", level="info")
        return {"message": "测试消息已发送到 Sentry"}
