#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置模块

用法:
    from config import settings

    # 访问 Alice 配置
    if settings.alice.enable_ltp:
        ...

    # 访问 Turing 配置
    port = settings.turing.server.port

    # 获取 Bot 配置
    from config import get_config_manager
    config_mgr = get_config_manager()
    bot_config = config_mgr.get_bot_config("default")
"""

from .loader import settings
from .manager import (
    ConfigManager,
    get_config_manager,
    reset_config_manager,
)
from .types import (
    Settings,
    PathsConfig,
    LtpConfig,
    AliceConfig,
    DatabaseConfig,
    AuthConfig,
    MatchConfig,
    AiBotConfig,
    HoneypotConfig,
    SessionConfig,
    ServerConfig,
    NlpServiceConfig,
    BotPoolConfig,
    AliceBotConfig,
    PerformanceConfig,
    TuringConfig,
    WebSocketConfig,
    LogConfig,
    ModulesConfig,
    ModuleRefConfig,
    TuringModuleRefConfig,
    BotPoolRefConfig,
    ScoreConfig,
    MidGameConfig,
    # 脚本引擎配置
    ScriptingConfig,
    LuaScriptEngineConfig,
    YamlScriptEngineConfig,
)
from .bot_loader import (
    BotConfig,
    BotConfigLoader,
    load_bot_configs,
)
from .bot_registry import (
    BotTemplate,
    BotTemplateRegistry,
    get_bot_registry,
    reset_bot_registry,
)
from .validator import (
    ValidationError,
    ConfigValidator,
    build_default_validator,
    build_strict_validator,
    validate_bot_configs,
    validate_scripting_paths,
)
from .builder import (
    ConfigBuilder,
)
from .env_loader import (
    EnvLoader,
)
from .yaml_loader import (
    YamlLoader,
)

__all__ = [
    # 配置访问
    "settings",
    "ConfigManager",
    "get_config_manager",
    "reset_config_manager",
    # 类型定义
    "Settings",
    "PathsConfig",
    "LtpConfig",
    "AliceConfig",
    "DatabaseConfig",
    "AuthConfig",
    "MatchConfig",
    "AiBotConfig",
    "HoneypotConfig",
    "SessionConfig",
    "ServerConfig",
    "NlpServiceConfig",
    "BotPoolConfig",
    "AliceBotConfig",
    "PerformanceConfig",
    "TuringConfig",
    "WebSocketConfig",
    "LogConfig",
    "ModulesConfig",
    "ModuleRefConfig",
    "TuringModuleRefConfig",
    "BotPoolRefConfig",
    "ScoreConfig",
    "MidGameConfig",
    # 脚本引擎配置
    "ScriptingConfig",
    "LuaScriptEngineConfig",
    "YamlScriptEngineConfig",
    # Bot 配置
    "BotConfig",
    "BotConfigLoader",
    "load_bot_configs",
    "BotTemplate",
    "BotTemplateRegistry",
    "get_bot_registry",
    "reset_bot_registry",
    # 验证器
    "ValidationError",
    "ConfigValidator",
    "build_default_validator",
    "build_strict_validator",
    "validate_bot_configs",
    "validate_scripting_paths",
    # 配置构建器
    "ConfigBuilder",
    # 配置加载器
    "EnvLoader",
    "YamlLoader",
]
