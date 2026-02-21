#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置类型定义
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Any, Dict


@dataclass
class PathsConfig:
    """路径配置"""
    project_root: Path
    alice_dir: Path
    turing_dir: Path
    log_dir: Path
    data_dir: Path
    scripts_dir: Path


@dataclass
class LtpConfig:
    """LTP 引擎配置"""
    enable_cws: bool
    enable_pos: bool
    enable_ner: bool
    enable_dep: bool
    enable_sdp: bool
    enable_srl: bool
    cache_size: int
    max_length: int


@dataclass
class AliceConfig:
    """Alice 模块配置"""
    enable_ltp: bool
    enable_ner: bool
    enable_log: bool
    ner_use_ltp: bool
    hot_reload: bool
    hot_reload_mode: str
    hot_reload_poll_interval: float
    script_file: Path
    rules_file: Path
    semantic_tags_file: Path
    context_max_items: int
    conversation_history_max_turns: int
    ltp_cache_size_limit: int
    dialogue_log_max_entries: int
    performance_monitor_sample_rate: float
    fallback_responses: List[str]
    greeting_responses: List[str]
    max_input_length: int
    script_match_timeout: int
    regex_cache_size: int
    log_dir: Path
    log_max_size_mb: int
    log_backup_count: int
    log_level: str
    ltp: LtpConfig


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str


@dataclass
class AuthConfig:
    """认证配置"""
    invite_code_length: int


@dataclass
class MatchConfig:
    """匹配配置"""
    timeout: int  # 秒


@dataclass
class AiBotConfig:
    """AI Bot 配置"""
    name: str
    typing_delay_base: float
    typing_delay_per_char: float


@dataclass
class SessionConfig:
    """会话配置"""
    min_chat_turns: int


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str
    port: int


@dataclass
class NlpServiceConfig:
    """NLP 服务配置"""
    enable_ltp: bool
    cache_size: int
    cache_ttl: int


@dataclass
class BotPoolConfig:
    """Bot 池配置"""
    min_instances: int
    max_instances: int
    idle_timeout: int
    max_concurrent: int


@dataclass
class AliceBotConfig:
    """AliceBot 配置（供 Turing 使用）"""
    enable_plugins: bool
    cache_size: int
    context_max_turns: int
    script_file: Path
    rules_file: Path


@dataclass
class PerformanceConfig:
    """性能配置"""
    response_timeout: float
    max_input_length: int
    base_typing_delay: float
    chars_per_second: float


@dataclass
class TuringConfig:
    """Turing 测试模块配置"""
    database: DatabaseConfig
    auth: AuthConfig
    match: MatchConfig
    ai_bot: AiBotConfig
    session: SessionConfig
    server: ServerConfig
    nlp_service: NlpServiceConfig
    bot_pool: BotPoolConfig
    alice_bot: AliceBotConfig
    performance: PerformanceConfig


@dataclass
class Settings:
    """全局配置根"""
    debug: bool
    log_level: str
    paths: PathsConfig
    alice: AliceConfig
    turing: TuringConfig
