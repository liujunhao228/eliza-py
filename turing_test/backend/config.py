"""
Turing Test Backend 配置模块

此模块已废弃，所有配置已统一至项目根目录的 config.yaml
请使用以下方式访问配置:

    from config import settings

    # 访问 Turing 配置
    port = settings.turing.server.port
    db_url = settings.turing.database.url

    # 访问共享 LTP 配置
    enable_ltp = settings.shared_ltp.enable_cws
"""

import warnings
from typing import Any

# 导入统一配置
from config import settings as _unified_settings


# 向后兼容的配置项映射 (模块级常量)
APP_NAME = "Turing Test Backend"
APP_VERSION = "0.1.0"

# 服务器配置
HOST = str(_unified_settings.turing.server.host)
PORT = int(_unified_settings.turing.server.port)

# 数据库配置
DATABASE_URL = _unified_settings.turing.database.url

# 认证配置
SECRET_KEY = _unified_settings.turing.auth.secret_key
ALGORITHM = _unified_settings.turing.auth.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = _unified_settings.turing.auth.access_token_expire_minutes

# 匹配配置
MATCH_TIMEOUT = _unified_settings.turing.match.timeout
MIN_CHAT_TURNS = _unified_settings.turing.session.min_chat_turns

# AI Bot 配置
AI_BOT_NAME = _unified_settings.turing.ai_bot.name
TYPING_DELAY_BASE = _unified_settings.turing.ai_bot.typing_delay_base
TYPING_DELAY_PER_CHAR = _unified_settings.turing.ai_bot.typing_delay_per_char

# Bot 池配置
BOT_POOL_MIN_INSTANCES = _unified_settings.turing.bot_pool.min_instances
BOT_POOL_MAX_INSTANCES = _unified_settings.turing.bot_pool.max_instances
BOT_POOL_IDLE_TIMEOUT = _unified_settings.turing.bot_pool.idle_timeout
BOT_POOL_MAX_CONCURRENT = _unified_settings.turing.bot_pool.max_concurrent

# NLP 服务配置
ENABLE_LTP = _unified_settings.turing.nlp_service.enable_ltp
NLP_CACHE_SIZE = _unified_settings.turing.nlp_service.cache_size
NLP_CACHE_TTL = _unified_settings.turing.nlp_service.cache_ttl

# WebSocket 配置
WS_PING_INTERVAL = _unified_settings.turing.websocket.ping_interval
WS_PING_TIMEOUT = _unified_settings.turing.websocket.ping_timeout

# 性能配置
RESPONSE_TIMEOUT = _unified_settings.turing.performance.response_timeout
MAX_INPUT_LENGTH = _unified_settings.turing.performance.max_input_length

# 日志配置
LOG_LEVEL = _unified_settings.turing.log.level
LOG_FILE = _unified_settings.turing.log.file or "logs/turing.log"

# 邀请码配置
INVITE_CODE_LENGTH = _unified_settings.turing.auth.invite_code_length
INITIAL_SCORE = _unified_settings.turing.auth.initial_score

# 跨域配置 (硬编码，因为这是前端相关的配置)
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class CompatSettings:
    """
    向后兼容的配置包装器

    支持两种访问方式:
    1. 大写常量访问：settings.APP_NAME, settings.HOST
    2. 小写属性访问：settings.debug, settings.log_level (映射到统一配置)
    """

    # 映射表：大写属性 -> 模块级常量
    _CONSTANTS = {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
        "HOST": HOST,
        "PORT": PORT,
        "DATABASE_URL": DATABASE_URL,
        "SECRET_KEY": SECRET_KEY,
        "ALGORITHM": ALGORITHM,
        "ACCESS_TOKEN_EXPIRE_MINUTES": ACCESS_TOKEN_EXPIRE_MINUTES,
        "MATCH_TIMEOUT": MATCH_TIMEOUT,
        "MIN_CHAT_TURNS": MIN_CHAT_TURNS,
        "AI_BOT_NAME": AI_BOT_NAME,
        "TYPING_DELAY_BASE": TYPING_DELAY_BASE,
        "TYPING_DELAY_PER_CHAR": TYPING_DELAY_PER_CHAR,
        "BOT_POOL_MIN_INSTANCES": BOT_POOL_MIN_INSTANCES,
        "BOT_POOL_MAX_INSTANCES": BOT_POOL_MAX_INSTANCES,
        "BOT_POOL_IDLE_TIMEOUT": BOT_POOL_IDLE_TIMEOUT,
        "BOT_POOL_MAX_CONCURRENT": BOT_POOL_MAX_CONCURRENT,
        "ENABLE_LTP": ENABLE_LTP,
        "NLP_CACHE_SIZE": NLP_CACHE_SIZE,
        "NLP_CACHE_TTL": NLP_CACHE_TTL,
        "WS_PING_INTERVAL": WS_PING_INTERVAL,
        "WS_PING_TIMEOUT": WS_PING_TIMEOUT,
        "RESPONSE_TIMEOUT": RESPONSE_TIMEOUT,
        "MAX_INPUT_LENGTH": MAX_INPUT_LENGTH,
        "LOG_LEVEL": LOG_LEVEL,
        "LOG_FILE": LOG_FILE,
        "INVITE_CODE_LENGTH": INVITE_CODE_LENGTH,
        "INITIAL_SCORE": INITIAL_SCORE,
        "CORS_ORIGINS": CORS_ORIGINS,
        "DEBUG": _unified_settings.debug,
    }

    def __getattr__(self, name: str) -> Any:
        # 优先返回大写常量
        if name in self._CONSTANTS:
            return self._CONSTANTS[name]

        # 尝试映射到统一配置
        # 如：log_level -> log_level (通用配置)
        try:
            return getattr(_unified_settings, name, None)
        except AttributeError:
            return None

    def __setattr__(self, name: str, value: Any):
        # 不允许修改配置 (仅用于向后兼容的只读访问)
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            warnings.warn(
                f"修改配置 {name} 仅在当前会话有效，建议使用 config.yaml 管理配置",
                UserWarning,
                stacklevel=2
            )
            # 存储到实例字典
            super().__setattr__(name, value)


# 创建向后兼容的 settings 对象
settings = CompatSettings()


# 导出
__all__ = [
    "settings",
    # 向后兼容的配置项
    "APP_NAME",
    "APP_VERSION",
    "HOST",
    "PORT",
    "DATABASE_URL",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "MATCH_TIMEOUT",
    "MIN_CHAT_TURNS",
    "AI_BOT_NAME",
    "TYPING_DELAY_BASE",
    "TYPING_DELAY_PER_CHAR",
    "BOT_POOL_MIN_INSTANCES",
    "BOT_POOL_MAX_INSTANCES",
    "BOT_POOL_IDLE_TIMEOUT",
    "BOT_POOL_MAX_CONCURRENT",
    "ENABLE_LTP",
    "NLP_CACHE_SIZE",
    "NLP_CACHE_TTL",
    "WS_PING_INTERVAL",
    "WS_PING_TIMEOUT",
    "RESPONSE_TIMEOUT",
    "MAX_INPUT_LENGTH",
    "LOG_LEVEL",
    "LOG_FILE",
    "INVITE_CODE_LENGTH",
    "INITIAL_SCORE",
    "CORS_ORIGINS",
]
