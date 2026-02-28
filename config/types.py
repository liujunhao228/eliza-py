#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置类型定义

配置结构说明:
- paths: 路径配置
- alice: Alice 模块配置
- turing: Turing 测试模块配置
- modules: 模块引用配置
- scripting: 脚本引擎配置 (新增)
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
    bots_dir: Path
    scripts_dir: Optional[Path] = None


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
# 脚本引擎配置 (新增)
# =============================================================================

@dataclass
class LuaScriptEngineConfig:
    """
    Lua 脚本引擎配置
    
    Attributes:
        script_dir: Lua 脚本目录路径
        metadata_file: Lua 脚本元数据文件路径 (可选)
        sandbox_mode: 是否启用沙箱模式
        max_execution_time: 最大执行时间 (秒)
        cache_size: 脚本缓存大小
    """
    script_dir: Path = None  # type: ignore
    metadata_file: Optional[Path] = None
    sandbox_mode: bool = True
    max_execution_time: float = 1.0
    cache_size: int = 100
    
    def __post_init__(self):
        """后处理：设置默认值"""
        if self.script_dir is None:
            self.script_dir = Path("scripts/lua")


@dataclass
class YamlScriptEngineConfig:
    """
    YAML 脚本引擎配置

    Attributes:
        script_file: YAML 脚本文件路径
        opening_script_file: 开场白脚本文件路径
    """
    script_file: Path = None  # type: ignore
    opening_script_file: Optional[Path] = None

    def __post_init__(self):
        """后处理：设置默认值"""
        if self.script_file is None:
            self.script_file = Path("alice/scripts/demo.yaml")


@dataclass
class OpeningConfig:
    """
    Bot 开场白配置

    用于配置 Bot 实例的开场白行为，支持概率和策略控制。

    Attributes:
        script: 开场白脚本文件路径
        enabled: 是否启用开场白
        probability: 发送概率 (0.0 - 1.0)
        strategy: 策略类型 ("random" | "first_only" | "always" | "never")
    """
    script: Optional[Path] = None
    enabled: bool = True
    probability: float = 1.0
    strategy: str = "random"

    def __post_init__(self):
        """后处理：验证配置"""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability 必须在 0.0-1.0 之间")
        valid_strategies = ["random", "first_only", "always", "never"]
        if self.strategy not in valid_strategies:
            raise ValueError(f"无效的策略：{self.strategy}，有效值为 {valid_strategies}")


@dataclass
class ScriptingConfig:
    """
    脚本引擎统一配置
    
    整合 Lua 和 YAML 脚本引擎配置，提供统一的脚本管理接口。
    
    Attributes:
        enable_lua: 是否启用 Lua 脚本引擎
        enable_yaml: 是否启用 YAML 脚本引擎
        lua: Lua 脚本引擎配置
        yaml: YAML 脚本引擎配置
        rules_file: 重组规则文件路径
    """
    enable_lua: bool = True
    enable_yaml: bool = True
    lua: Optional[LuaScriptEngineConfig] = None
    yaml: Optional[YamlScriptEngineConfig] = None
    rules_file: Optional[Path] = None


# =============================================================================
# Alice 模块配置
# =============================================================================

@dataclass
class AliceConfig:
    """
    Alice 模块配置
    
    Attributes:
        enable_ltp: 是否启用 LTP 句法分析
        enable_ner: 是否启用 NER 实体识别
        enable_log: 是否启用对话日志
        ner_use_ltp: NER 是否使用 LTP 增强
        scripting: 脚本引擎配置
    """
    # 功能开关
    enable_ltp: bool = True
    enable_ner: bool = True
    enable_log: bool = True
    ner_use_ltp: bool = True
    
    # 脚本引擎配置
    scripting: ScriptingConfig = None  # type: ignore

    # 对话上下文配置
    context_max_items: int = 10
    conversation_history_max_turns: int = 20
    ltp_cache_size_limit: int = 100
    dialogue_log_max_entries: int = 1000

    # 性能配置
    performance_monitor_sample_rate: float = 1.0
    max_input_length: int = 500
    script_match_timeout: int = 100  # 毫秒
    regex_cache_size: int = 100

    # 预定义响应
    fallback_responses: List[str] = field(default_factory=list)
    greeting_responses: List[str] = field(default_factory=list)

    # 日志配置
    log_dir: Optional[Path] = None
    log_max_size_mb: int = 10
    log_backup_count: int = 5
    log_level: str = "INFO"

    # LTP 配置 (引用共享配置)
    ltp: Optional[LtpConfig] = None
    
    def __post_init__(self):
        """后处理：设置默认值"""
        if self.scripting is None:
            self.scripting = ScriptingConfig()


# =============================================================================
# Turing 测试模块配置
# =============================================================================

@dataclass
class DatabasePoolConfig:
    """数据库连接池配置"""
    size: int = 20
    max_overflow: int = 40
    recycle: int = 3600
    timeout: int = 30


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str
    pool: Optional[DatabasePoolConfig] = None


@dataclass
class AuthConfig:
    """认证配置"""
    invite_code_length: int
    access_token_expire_minutes: int = 10080  # 7 天
    algorithm: str = "HS256"
    secret_key: str = "your-secret-key-change-in-production"
    initial_score: int = 100


@dataclass
class TimeDistributionConfig:
    """时间分布配置"""
    min: float
    max: float
    probability: float


@dataclass
class BotPoolBotConfig:
    """Bot 池中的 Bot 配置"""
    id: str
    weight: float
    description: str = ""
    name_prefix: Optional[str] = None


@dataclass
class BotPoolConfig:
    """Bot 池配置"""
    enabled: bool = True
    bots: List[Dict[str, Any]] = field(default_factory=list)
    # 兼容旧字段
    min_instances: int = 3
    max_instances: int = 10
    idle_timeout: int = 300
    max_concurrent: int = 5
    default_template: str = "default"


@dataclass
class HoneypotBotConfig:
    """钓鱼 Bot 配置"""
    id: str
    weight: float
    description: str = ""


@dataclass
class MatchHoneypotConfig:
    """匹配中的钓鱼 Bot 配置"""
    enabled: bool = True
    probability_in_bot_matches: float = 0.15  # Bot 局中 15% 是钓鱼
    bots: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MatchConfig:
    """匹配配置（概率分流版）"""
    # 核心概率配置
    human_probability: float = 0.30  # 30% 真人
    bot_probability: float = 0.70    # 70% Bot
    
    # 超时配置
    timeout_seconds: int = 10        # 真人等待超时 (秒)
    fake_delay_min_ms: int = 1000    # 假装延迟最小值 (毫秒)
    fake_delay_max_ms: int = 3000    # 假装延迟最大值 (毫秒)
    
    # 钓鱼 Bot 配置
    honeypot: Optional[MatchHoneypotConfig] = None
    
    # Bot 池配置
    bot_pool: Optional[BotPoolConfig] = None
    
    # 保留字段（兼容旧配置验证）
    timeout: int = 10  # 兼容旧字段
    fixed_wait_time: int = 3
    ai_control_group_rate: float = 0.2
    honeypot_probability: float = 0.15
    honeypot_high_meta_probability: float = 0.30
    time_distribution: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def __post_init__(self):
        """后处理：设置默认值"""
        if self.honeypot is None:
            self.honeypot = MatchHoneypotConfig()
        if self.bot_pool is None:
            self.bot_pool = BotPoolConfig()


@dataclass
class HoneypotConfig:
    """钓鱼机器人配置"""
    reply_delay_min: float = 2.0
    reply_delay_max: float = 8.0
    opening_delay_min: float = 5.0
    opening_delay_max: float = 15.0
    typing_delay_per_char: float = 0.05
    occasional_long_delay_probability: float = 0.1
    occasional_long_delay_min: float = 15.0
    occasional_long_delay_max: float = 60.0
    meta_delay_multiplier: float = 1.5
    early_session_delay_multiplier: float = 1.3


@dataclass
class AiBotConfig:
    """AI Bot 配置"""
    name: str
    typing_delay_base: float
    typing_delay_per_char: float
    honeypot: Optional[HoneypotConfig] = None


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
class ScoreConfig:
    """积分配置"""
    entry_fee: int
    min_free_turns: int
    turn_penalty_rate: float
    base_reward: Dict[str, int] = field(default_factory=dict)
    confidence_multiplier: Dict[str, float] = field(default_factory=dict)
    meta_multiplier: Dict[str, float] = field(default_factory=dict)


@dataclass
class MidGameConfig:
    """场中判断配置"""
    enabled: bool = True
    multiplier_correct: float = 2.0
    multiplier_wrong: float = 1.5
    max_per_session: int = 1


@dataclass
class MetaConversationConfig:
    """元对话配置"""
    enabled: bool = True
    keywords: List[str] = field(default_factory=list)


# 注意：BotPoolConfig 已在上面定义为匹配配置的一部分
# 这里保留一个简化的引用配置用于 TuringConfig


@dataclass
class AliceBotConfig:
    """AliceBot 配置（供 Turing 使用）"""
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
class WebSocketConfig:
    """WebSocket 配置"""
    ping_interval: int = 20  # 秒
    ping_timeout: int = 30   # 秒


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    file: Optional[str] = None
    max_size_mb: int = 10
    backup_count: int = 5


@dataclass
class CorsConfig:
    """CORS 跨域配置"""
    origins: List[str] = field(default_factory=list)


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
    cors: CorsConfig = None  # type: ignore
    score: Optional[ScoreConfig] = None
    mid_game: Optional[MidGameConfig] = None
    meta_conversation: MetaConversationConfig = None  # type: ignore
    # 保留 meta_keywords 字段以兼容旧配置
    meta_keywords: List[str] = field(default_factory=list)


# =============================================================================
# 模块引用配置
# =============================================================================

@dataclass
class ModuleRefConfig:
    """模块引用配置"""
    config_file: str


@dataclass
class BotPoolRefConfig:
    """Bot 池引用配置"""
    config_dir: str
    default_template: str


@dataclass
class TuringModuleRefConfig:
    """Turing 模块引用配置"""
    config_file: str
    bot_pool: Optional[BotPoolRefConfig] = None


@dataclass
class ModulesConfig:
    """模块配置"""
    alice: ModuleRefConfig
    turing: TuringModuleRefConfig


# =============================================================================
# 全局配置根
# =============================================================================

@dataclass
class Settings:
    """全局配置根"""
    debug: bool
    log_level: str
    paths: PathsConfig
    modules: ModulesConfig
    alice: AliceConfig
    turing: TuringConfig

    # 错误追踪配置
    sentry_dsn: Optional[str] = None
    sentry_enabled: bool = False
    environment: str = "production"

    # 前端 URL 配置
    frontend_url: str = "http://localhost:5173"
