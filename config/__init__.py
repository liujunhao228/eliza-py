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
    
    # 访问路径配置
    log_dir = settings.paths.log_dir
"""

from .loader import settings
from .types import (
    Settings,
    PathsConfig,
    LtpConfig,
    AliceConfig,
    DatabaseConfig,
    AuthConfig,
    MatchConfig,
    AiBotConfig,
    SessionConfig,
    ServerConfig,
    NlpServiceConfig,
    BotPoolConfig,
    AliceBotConfig,
    PerformanceConfig,
    TuringConfig,
)

__all__ = [
    "settings",
    "Settings",
    "PathsConfig",
    "LtpConfig",
    "AliceConfig",
    "DatabaseConfig",
    "AuthConfig",
    "MatchConfig",
    "AiBotConfig",
    "SessionConfig",
    "ServerConfig",
    "NlpServiceConfig",
    "BotPoolConfig",
    "AliceBotConfig",
    "PerformanceConfig",
    "TuringConfig",
]
