#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置类型定义

配置结构说明:
- paths: 路径配置
- alice: Alice 模块配置
- turing: Turing 测试模块配置
- shared: 共享配置 (LTP、NLP 等)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Any, Dict


# =============================================================================
# 路径配置
# =============================================================================

@dataclass
class PathsConfig:
    """路径配置"""
    project_root: Path
    alice_dir: Path
    turing_dir: Path
    log_dir: Path
    data_dir: Path
    scripts_dir: Path


# =============================================================================
# 共享配置 - LTP 引擎
# =============================================================================

@dataclass
class LtpConfig:
    """
    LTP 引擎配置 (共享)
    
    用于 Alice 和 Turing 共享的 LTP 句法分析配置
    """
    # 任务启用开关
    enable_cws: bool = True           # 词分词
    enable_pos: bool = True           # 词性标注
    enable_ner: bool = True           # 命名实体识别
    enable_dep: bool = True           # 依存句法分析
    enable_sdp: bool = True           # 语义依存分析
    enable_srl: bool = True           # 语义角色标注
    
    # 性能配置
    cache_size: int = 50
    max_length: int = 512
    
    # 模型配置
    model_path: Optional[str] = None
    device: Optional[str] = None      # 'cpu', 'cuda', 'cuda:0'
    batch_size: int = 32
    
    # 缓存目录
    cache_dir: Optional[str] = None
    
    def get_enabled_tasks(self) -> List[str]:
        """获取启用的任务列表"""
        tasks = []
        if self.enable_cws:
            tasks.append('cws')
        if self.enable_pos:
            tasks.append('pos')
        if self.enable_ner:
            tasks.append('ner')
        if self.enable_dep:
            tasks.append('dep')
        if self.enable_sdp:
            tasks.append('sdp')
        if self.enable_srl:
            tasks.append('srl')
        return tasks


# =============================================================================
# Alice 模块配置
# =============================================================================

@dataclass
class AliceConfig:
    """Alice 模块配置"""
    # 功能开关
    enable_ltp: bool
    enable_ner: bool
    enable_log: bool
    ner_use_ltp: bool
    hot_reload: bool
    hot_reload_mode: str
    hot_reload_poll_interval: float
    
    # 文件路径
    script_file: Path
    rules_file: Path
    semantic_tags_file: Path
    
    # 对话上下文配置
    context_max_items: int
    conversation_history_max_turns: int
    ltp_cache_size_limit: int
    dialogue_log_max_entries: int
    
    # 性能配置
    performance_monitor_sample_rate: float
    max_input_length: int
    script_match_timeout: int
    regex_cache_size: int
    
    # 预定义响应
    fallback_responses: List[str]
    greeting_responses: List[str]
    
    # 日志配置
    log_dir: Path
    log_max_size_mb: int
    log_backup_count: int
    log_level: str
    
    # LTP 配置 (引用共享配置)
    ltp: LtpConfig


# =============================================================================
# Turing 测试模块配置
# =============================================================================

@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str


@dataclass
class AuthConfig:
    """认证配置"""
    invite_code_length: int
    access_token_expire_minutes: int = 10080  # 7 天
    algorithm: str = "HS256"
    secret_key: str = "your-secret-key-change-in-production"
    initial_score: int = 100


@dataclass
class MatchConfig:
    """匹配配置"""
    timeout: int  # 秒
    # 匹配时间分布（真人/AI 使用相同分布，消除时间线索）
    time_distribution: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "fast": {"min": 0, "max": 3, "probability": 0.5},
        "normal": {"min": 3, "max": 8, "probability": 0.3},
        "slow": {"min": 8, "max": 15, "probability": 0.15},
        "very_slow": {"min": 15, "max": 30, "probability": 0.05},
    })
    # 钓鱼机器人配置
    honeypot_probability: float = 0.15
    honeypot_high_meta_probability: float = 0.30


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
    """NLP 服务配置 (共享)"""
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
    """性能配置 (共享)"""
    response_timeout: float
    max_input_length: int
    base_typing_delay: float
    chars_per_second: float


@dataclass
class WebSocketConfig:
    """WebSocket 配置"""
    ping_interval: int = 20  # 秒
    ping_timeout: int = 30   # 秒


@dataclass
class LogConfig:
    """日志配置 (共享)"""
    level: str = "INFO"
    file: Optional[str] = None
    max_size_mb: int = 10
    backup_count: int = 5


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
    websocket: WebSocketConfig
    log: LogConfig


# =============================================================================
# 全局配置根
# =============================================================================

@dataclass
class Settings:
    """全局配置根"""
    debug: bool
    log_level: str
    paths: PathsConfig
    alice: AliceConfig
    turing: TuringConfig
    shared_ltp: LtpConfig = field(default_factory=LtpConfig)
