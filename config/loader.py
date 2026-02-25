#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
统一管理所有配置，支持：
- 环境变量 (.env)
- YAML 配置文件
- 模块专属配置 (config.alice.yaml, config.turing.yaml)
- 环境变量覆盖
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 使用 python-dotenv 加载 .env 文件
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

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
    WebSocketConfig,
    LogConfig,
    ModulesConfig,
    ModuleRefConfig,
    TuringModuleRefConfig,
    BotPoolRefConfig,
    ScoreConfig,
    MidGameConfig,
    ScriptingConfig,
    LuaScriptEngineConfig,
    YamlScriptEngineConfig,
)
from .bot_loader import BotConfigLoader, BotConfig


class ConfigLoader:
    """
    配置加载器 - 无硬编码默认值

    加载优先级:
    1. 环境变量 (最高优先级)
    2. .env 文件
    3. config.*.yaml (模块专属配置)
    4. config.yaml (主配置)
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._env: Dict[str, str] = {}
        self._config: Dict[str, Any] = {}
        self._bot_configs: List[BotConfig] = []

    def load(self) -> Settings:
        """加载所有配置"""
        # 1. 加载 .env 文件
        self._load_dotenv()

        # 2. 加载环境变量
        self._env = dict(os.environ)

        # 3. 加载 YAML 配置
        self._load_yaml()

        # 4. 环境变量覆盖 (CONFIG_ 前缀)
        self._apply_env_overrides()

        # 5. 加载 Bot 配置
        self._load_bot_configs()

        # 6. 构建类型化配置对象
        return self._build_settings()

    def _load_dotenv(self) -> None:
        """加载 .env 文件"""
        if load_dotenv:
            # 尝试加载 .env 文件
            env_file = self.project_root / ".env"
            if env_file.exists():
                load_dotenv(env_file)

            # 也支持 .env.local (用于本地开发覆盖)
            env_local = self.project_root / ".env.local"
            if env_local.exists():
                load_dotenv(env_local)

    def _load_yaml(self) -> None:
        """加载 YAML 配置文件"""
        # 主配置文件 (必须存在)
        main_config = self.project_root / "config.yaml"
        if not main_config.exists():
            raise FileNotFoundError(
                f"主配置文件不存在：{main_config}\n"
                f"请创建 config.yaml 文件，可参考 config.yaml.example"
            )

        with open(main_config, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        # 加载模块专属配置
        self._load_module_configs()

    def _load_module_configs(self) -> None:
        """加载模块专属配置 (config.alice.yaml, config.turing.yaml)"""
        modules_cfg = self._config.get("modules", {})

        # Alice 模块配置
        alice_ref = modules_cfg.get("alice", {})
        alice_config_file = alice_ref.get("config_file", "config.alice.yaml")
        self._load_single_module_config("alice", alice_config_file)

        # Turing 模块配置
        turing_ref = modules_cfg.get("turing", {})
        turing_config_file = turing_ref.get("config_file", "config.turing.yaml")
        self._load_single_module_config("turing", turing_config_file)

    def _load_single_module_config(self, module_name: str, config_file: str) -> None:
        """
        加载单个模块配置

        Args:
            module_name: 模块名称
            config_file: 配置文件路径
        """
        module_config = self.project_root / config_file
        if module_config.exists():
            with open(module_config, "r", encoding="utf-8") as f:
                module_data = yaml.safe_load(f) or {}
            # 合并到主配置
            if module_name not in self._config:
                self._config[module_name] = {}
            self._config[module_name].update(module_data)
            logger_info(f"已加载模块配置：{module_name} ({config_file})")
        else:
            logger_warning(f"模块配置文件不存在：{module_config}")

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # 支持 CONFIG_ALICE_ENABLE_LTP=true 形式
        for key, value in self._env.items():
            if key.startswith("CONFIG_"):
                config_key = key[7:].lower()  # 移除 CONFIG_ 前缀
                self._set_nested_value(config_key, self._parse_value(value))

    def _set_nested_value(self, key: str, value: Any) -> None:
        """设置嵌套字典的值，支持 a.b.c 形式"""
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def _parse_value(self, value: str) -> Any:
        """字符串转类型"""
        v = value.strip()

        # 布尔值
        if v.lower() in ("true", "yes", "1", "on"):
            return True
        if v.lower() in ("false", "no", "0", "off"):
            return False

        # 整数
        try:
            return int(v)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(v)
        except ValueError:
            pass

        # 字符串 (去除引号)
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]

        return v

    def _load_bot_configs(self) -> None:
        """加载 Bot 配置"""
        # 从配置中获取 bots_dir
        paths_cfg = self._config.get("paths", {})
        bots_dir = paths_cfg.get("bots_dir", "bots")

        # 使用 BotConfigLoader 加载
        loader = BotConfigLoader(self.project_root)
        self._bot_configs = loader.load_all(bots_dir)

    def _get_required(self, d: Dict[str, Any], key: str, expected_type: type, path: str = "") -> Any:
        """获取必填配置项"""
        if key not in d:
            full_path = f"{path}.{key}" if path else key
            raise KeyError(f"缺少必填配置项：{full_path}")

        value = d[key]

        # 类型检查 (Path 特殊处理)
        if expected_type == Path:
            if not isinstance(value, str):
                full_path = f"{path}.{key}" if path else key
                raise TypeError(f"配置项 {full_path} 必须是字符串路径")
            return self.project_root / value if not Path(value).is_absolute() else Path(value)

        if not isinstance(value, expected_type):
            full_path = f"{path}.{key}" if path else key
            raise TypeError(
                f"配置项 {full_path} 类型错误，期望 {expected_type.__name__}, "
                f"实际 {type(value).__name__}"
            )

        return value

    def _get_optional(
        self,
        d: Dict[str, Any],
        key: str,
        expected_type: type,
        default: Any = None,
        path: str = ""
    ) -> Any:
        """获取可选配置项"""
        if key not in d:
            return default

        value = d[key]

        # 类型检查 (Path 特殊处理)
        if expected_type == Path:
            if not isinstance(value, str):
                full_path = f"{path}.{key}" if path else key
                raise TypeError(f"配置项 {full_path} 必须是字符串路径")
            return self.project_root / value if not Path(value).is_absolute() else Path(value)

        if not isinstance(value, expected_type):
            full_path = f"{path}.{key}" if path else key
            raise TypeError(
                f"配置项 {full_path} 类型错误，期望 {expected_type.__name__}, "
                f"实际 {type(value).__name__}"
            )

        return value

    def _build_settings(self, config: Optional[Dict[str, Any]] = None) -> Settings:
        """构建类型化配置对象

        Args:
            config: 配置字典，None 则使用 self._config
        """
        cfg = config if config is not None else self._config

        # 构建路径配置
        paths_cfg = cfg.get("paths", {})
        paths = self._build_paths_config(paths_cfg)

        # 构建模块引用配置
        modules = self._build_modules_config(cfg)

        # 构建 LTP 配置
        alice_cfg = cfg.get("alice", {})
        ltp_cfg = alice_cfg.get("ltp", {})
        ltp = self._build_ltp_config(ltp_cfg)

        # 构建 Alice 配置
        alice = self._build_alice_config(alice_cfg, paths, ltp)

        # 构建 Turing 配置
        turing_cfg = cfg.get("turing", {})
        turing = self._build_turing_config(turing_cfg, paths)

        # 获取 Sentry 配置（从环境变量优先读取）
        sentry_dsn = self._env.get("SENTRY_DSN", cfg.get("sentry_dsn", None))
        sentry_enabled = self._env.get("SENTRY_ENABLED", cfg.get("sentry_enabled", "false")).lower() in ("true", "yes", "1", "on")
        environment = self._env.get("ENVIRONMENT", cfg.get("environment", "production"))

        return Settings(
            debug=self._get_optional(cfg, "debug", bool, False),
            log_level=self._get_optional(cfg, "log_level", str, "INFO"),
            paths=paths,
            modules=modules,
            alice=alice,
            turing=turing,
            sentry_dsn=sentry_dsn,
            sentry_enabled=sentry_enabled,
            environment=environment,
        )

    def _build_modules_config(self, cfg: Dict[str, Any]) -> ModulesConfig:
        """构建模块引用配置"""
        modules_cfg = cfg.get("modules", {})

        alice_ref = modules_cfg.get("alice", {})
        alice_module = ModuleRefConfig(
            config_file=alice_ref.get("config_file", "config.alice.yaml"),
        )

        turing_ref = modules_cfg.get("turing", {})
        bot_pool_ref = turing_ref.get("bot_pool", {})
        turing_module = TuringModuleRefConfig(
            config_file=turing_ref.get("config_file", "config.turing.yaml"),
            bot_pool=BotPoolRefConfig(
                config_dir=bot_pool_ref.get("config_dir", "bots"),
                default_template=bot_pool_ref.get("default_template", "default"),
            ) if bot_pool_ref else None,
        )

        return ModulesConfig(
            alice=alice_module,
            turing=turing_module,
        )

    def _build_paths_config(self, cfg: Dict[str, Any]) -> PathsConfig:
        """构建路径配置"""
        project_root_str = self._get_required(cfg, "project_root", str, "paths")
        project_root = Path(project_root_str)
        if not project_root.is_absolute():
            project_root = self.project_root / project_root

        scripts_dir = None
        if "scripts_dir" in cfg:
            scripts_dir = Path(cfg["scripts_dir"])
            if not scripts_dir.is_absolute():
                scripts_dir = project_root / scripts_dir

        return PathsConfig(
            project_root=project_root,
            alice_dir=project_root / cfg.get("alice_dir", "alice"),
            turing_dir=project_root / cfg.get("turing_dir", "turing_test"),
            log_dir=project_root / cfg.get("log_dir", "logs"),
            data_dir=project_root / cfg.get("data_dir", "data"),
            bots_dir=project_root / cfg.get("bots_dir", "bots"),
            scripts_dir=scripts_dir,
        )

    def _build_ltp_config(self, cfg: Dict[str, Any]) -> LtpConfig:
        """构建 LTP 配置"""
        return LtpConfig(
            enable_cws=self._get_required(cfg, "enable_cws", bool, "ltp"),
            enable_pos=self._get_required(cfg, "enable_pos", bool, "ltp"),
            enable_ner=self._get_required(cfg, "enable_ner", bool, "ltp"),
            enable_dep=self._get_required(cfg, "enable_dep", bool, "ltp"),
            enable_sdp=self._get_required(cfg, "enable_sdp", bool, "ltp"),
            enable_srl=self._get_required(cfg, "enable_srl", bool, "ltp"),
            cache_size=self._get_optional(cfg, "cache_size", int, 50, "ltp"),
            max_length=self._get_optional(cfg, "max_length", int, 512, "ltp"),
        )

    def _build_alice_config(
        self,
        cfg: Dict[str, Any],
        paths: PathsConfig,
        ltp: LtpConfig
    ) -> AliceConfig:
        """构建 Alice 配置"""
        # 构建脚本引擎配置
        scripting = self._build_scripting_config(cfg.get("scripting", {}), paths)
        
        return AliceConfig(
            enable_ltp=self._get_required(cfg, "enable_ltp", bool, "alice"),
            enable_ner=self._get_required(cfg, "enable_ner", bool, "alice"),
            enable_log=self._get_required(cfg, "enable_log", bool, "alice"),
            ner_use_ltp=self._get_required(cfg, "ner_use_ltp", bool, "alice"),
            scripting=scripting,
            semantic_tags_file=self._get_optional(
                cfg, "semantic_tags_file", Path,
                paths.project_root / "alice" / "scripts" / "semantic_tags.yaml", "alice"
            ),
            context_max_items=self._get_required(cfg, "context_max_items", int, "alice"),
            conversation_history_max_turns=self._get_required(
                cfg, "conversation_history_max_turns", int, "alice"
            ),
            ltp_cache_size_limit=self._get_optional(cfg, "ltp_cache_size_limit", int, 100, "alice"),
            dialogue_log_max_entries=self._get_optional(cfg, "dialogue_log_max_entries", int, 1000, "alice"),
            performance_monitor_sample_rate=self._get_optional(
                cfg, "performance_monitor_sample_rate", float, 1.0, "alice"
            ),
            fallback_responses=self._get_optional(cfg, "fallback_responses", list, [], "alice"),
            greeting_responses=self._get_optional(cfg, "greeting_responses", list, [], "alice"),
            max_input_length=self._get_optional(cfg, "max_input_length", int, 500, "alice"),
            script_match_timeout=self._get_optional(cfg, "script_match_timeout", int, 100, "alice"),
            regex_cache_size=self._get_optional(cfg, "regex_cache_size", int, 100, "alice"),
            log_dir=paths.log_dir,
            log_max_size_mb=self._get_optional(cfg, "log_max_size_mb", int, 10, "alice"),
            log_backup_count=self._get_optional(cfg, "log_backup_count", int, 5, "alice"),
            log_level=self._get_optional(cfg, "log_level", str, "INFO", "alice"),
            ltp=ltp,
        )
    
    def _build_scripting_config(self, cfg: Dict[str, Any], paths: PathsConfig) -> ScriptingConfig:
        """
        构建脚本引擎配置
        
        Args:
            cfg: 脚本配置字典
            paths: 路径配置
        
        Returns:
            ScriptingConfig 实例
        """
        # Lua 配置
        lua_cfg = cfg.get("lua", {})
        lua_config = None
        if lua_cfg:
            script_dir_str = lua_cfg.get("script_dir", "scripts/lua")
            script_dir = Path(script_dir_str)
            if not script_dir.is_absolute():
                script_dir = paths.project_root / script_dir
            
            metadata_file = None
            if lua_cfg.get("metadata_file"):
                metadata_file = Path(lua_cfg["metadata_file"])
                if not metadata_file.is_absolute():
                    metadata_file = paths.project_root / metadata_file
            
            lua_config = LuaScriptEngineConfig(
                script_dir=script_dir,
                metadata_file=metadata_file,
                sandbox_mode=lua_cfg.get("sandbox_mode", True),
                max_execution_time=lua_cfg.get("max_execution_time", 1.0),
                cache_size=lua_cfg.get("cache_size", 100),
            )
        
        # YAML 配置
        yaml_cfg = cfg.get("yaml", {})
        yaml_config = None
        if yaml_cfg:
            script_file_str = yaml_cfg.get("script_file", "alice/scripts/demo.yaml")
            script_file = Path(script_file_str)
            if not script_file.is_absolute():
                script_file = paths.project_root / script_file
            yaml_config = YamlScriptEngineConfig(script_file=script_file)
        
        # 重组规则文件
        rules_file = None
        if cfg.get("rules_file"):
            rules_file = Path(cfg["rules_file"])
            if not rules_file.is_absolute():
                rules_file = paths.project_root / rules_file
        
        return ScriptingConfig(
            enable_lua=cfg.get("enable_lua", True),
            enable_yaml=cfg.get("enable_yaml", True),
            lua=lua_config,
            yaml=yaml_config,
            rules_file=rules_file,
        )

    def _build_turing_config(self, cfg: Dict[str, Any], paths: PathsConfig) -> TuringConfig:
        """构建 Turing 配置"""
        db_cfg = cfg.get("database", {})
        auth_cfg = cfg.get("auth", {})
        match_cfg = cfg.get("match", {})
        ai_bot_cfg = cfg.get("ai_bot", {})
        session_cfg = cfg.get("session", {})
        server_cfg = cfg.get("server", {})
        nlp_cfg = cfg.get("nlp_service", {})
        bot_pool_cfg = cfg.get("bot_pool", {})
        alice_bot_cfg = cfg.get("alice_bot", {})
        perf_cfg = cfg.get("performance", {})
        ws_cfg = cfg.get("websocket", {})
        log_cfg = cfg.get("log", {})
        score_cfg = cfg.get("score", {})
        mid_game_cfg = cfg.get("mid_game", {})
        meta_keywords = cfg.get("meta_keywords", [])

        # 构建 Bot 池配置
        bot_pool = BotPoolConfig(
            min_instances=self._get_required(bot_pool_cfg, "min_instances", int, "turing.bot_pool"),
            max_instances=self._get_required(bot_pool_cfg, "max_instances", int, "turing.bot_pool"),
            idle_timeout=self._get_required(bot_pool_cfg, "idle_timeout", int, "turing.bot_pool"),
            max_concurrent=self._get_required(bot_pool_cfg, "max_concurrent", int, "turing.bot_pool"),
            default_template=self._get_optional(bot_pool_cfg, "default_template", str, "default", "turing.bot_pool"),
        )

        # 构建积分配置 (可选)
        score = None
        if score_cfg:
            score = ScoreConfig(
                entry_fee=self._get_required(score_cfg, "entry_fee", int, "turing.score"),
                min_free_turns=self._get_required(score_cfg, "min_free_turns", int, "turing.score"),
                turn_penalty_rate=self._get_required(score_cfg, "turn_penalty_rate", float, "turing.score"),
                base_reward=score_cfg.get("base_reward", {}),
                confidence_multiplier=score_cfg.get("confidence_multiplier", {}),
                meta_multiplier=score_cfg.get("meta_multiplier", {}),
            )

        # 构建场中判断配置 (可选)
        mid_game = None
        if mid_game_cfg:
            mid_game = MidGameConfig(
                enabled=self._get_optional(mid_game_cfg, "enabled", bool, True, "turing.mid_game"),
                multiplier_correct=self._get_optional(mid_game_cfg, "multiplier_correct", float, 2.0, "turing.mid_game"),
                multiplier_wrong=self._get_optional(mid_game_cfg, "multiplier_wrong", float, 1.5, "turing.mid_game"),
                max_per_session=self._get_optional(mid_game_cfg, "max_per_session", int, 1, "turing.mid_game"),
            )

        return TuringConfig(
            database=DatabaseConfig(
                url=self._get_required(db_cfg, "url", str, "turing.database"),
            ),
            auth=AuthConfig(
                invite_code_length=self._get_required(auth_cfg, "invite_code_length", int, "turing.auth"),
                access_token_expire_minutes=self._get_optional(auth_cfg, "access_token_expire_minutes", int, 10080, "turing.auth"),
                algorithm=self._get_optional(auth_cfg, "algorithm", str, "HS256", "turing.auth"),
                secret_key=self._get_optional(auth_cfg, "secret_key", str, "your-secret-key-change-in-production", "turing.auth"),
                initial_score=self._get_optional(auth_cfg, "initial_score", int, 100, "turing.auth"),
            ),
            match=MatchConfig(
                timeout=self._get_required(match_cfg, "timeout", int, "turing.match"),
                time_distribution=match_cfg.get("time_distribution", {}),
                honeypot_probability=self._get_optional(match_cfg, "honeypot_probability", float, 0.15, "turing.match"),
                honeypot_high_meta_probability=self._get_optional(match_cfg, "honeypot_high_meta_probability", float, 0.30, "turing.match"),
            ),
            ai_bot=AiBotConfig(
                name=self._get_required(ai_bot_cfg, "name", str, "turing.ai_bot"),
                typing_delay_base=self._get_required(ai_bot_cfg, "typing_delay_base", float, "turing.ai_bot"),
                typing_delay_per_char=self._get_required(ai_bot_cfg, "typing_delay_per_char", float, "turing.ai_bot"),
            ),
            session=SessionConfig(
                min_chat_turns=self._get_required(session_cfg, "min_chat_turns", int, "turing.session"),
            ),
            server=ServerConfig(
                host=self._get_required(server_cfg, "host", str, "turing.server"),
                port=self._get_required(server_cfg, "port", int, "turing.server"),
            ),
            nlp_service=NlpServiceConfig(
                enable_ltp=self._get_required(nlp_cfg, "enable_ltp", bool, "turing.nlp_service"),
                cache_size=self._get_required(nlp_cfg, "cache_size", int, "turing.nlp_service"),
                cache_ttl=self._get_required(nlp_cfg, "cache_ttl", int, "turing.nlp_service"),
            ),
            bot_pool=bot_pool,
            alice_bot=AliceBotConfig(
                enable_plugins=self._get_required(alice_bot_cfg, "enable_plugins", bool, "turing.alice_bot"),
                cache_size=self._get_required(alice_bot_cfg, "cache_size", int, "turing.alice_bot"),
                context_max_turns=self._get_required(alice_bot_cfg, "context_max_turns", int, "turing.alice_bot"),
                script_file=self._get_required(alice_bot_cfg, "script_file", Path, "turing.alice_bot"),
                rules_file=self._get_required(alice_bot_cfg, "rules_file", Path, "turing.alice_bot"),
            ),
            performance=PerformanceConfig(
                response_timeout=self._get_required(perf_cfg, "response_timeout", float, "turing.performance"),
                max_input_length=self._get_required(perf_cfg, "max_input_length", int, "turing.performance"),
                base_typing_delay=self._get_required(perf_cfg, "base_typing_delay", float, "turing.performance"),
                chars_per_second=self._get_required(perf_cfg, "chars_per_second", float, "turing.performance"),
            ),
            websocket=WebSocketConfig(
                ping_interval=self._get_optional(ws_cfg, "ping_interval", int, 20, "turing.websocket"),
                ping_timeout=self._get_optional(ws_cfg, "ping_timeout", int, 30, "turing.websocket"),
            ),
            log=LogConfig(
                level=self._get_optional(log_cfg, "level", str, "INFO", "turing.log"),
                file=self._get_optional(log_cfg, "file", str, None, "turing.log"),
                max_size_mb=self._get_optional(log_cfg, "max_size_mb", int, 10, "turing.log"),
                backup_count=self._get_optional(log_cfg, "backup_count", int, 5, "turing.log"),
            ),
            score=score,
            mid_game=mid_game,
            meta_keywords=meta_keywords,
        )

    def get_bot_configs(self) -> List[BotConfig]:
        """获取已加载的 Bot 配置"""
        return self._bot_configs

    def get_bot_config_by_id(self, template_id: str) -> Optional[BotConfig]:
        """根据 ID 获取 Bot 配置"""
        for config in self._bot_configs:
            if config.id == template_id:
                return config
        return None


# 日志辅助函数 (避免循环依赖)
def logger_info(msg: str):
    try:
        from loguru import logger
        logger.info(msg)
    except ImportError:
        print(f"[INFO] {msg}")

def logger_warning(msg: str):
    try:
        from loguru import logger
        logger.warning(msg)
    except ImportError:
        print(f"[WARNING] {msg}")


# 全局单例
_project_root = Path(__file__).parent.parent
_loader = ConfigLoader(_project_root)
settings = _loader.load()
