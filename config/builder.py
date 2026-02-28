#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置构建器
============

负责将原始配置字典构建为类型化配置对象。

用法:
    from config.builder import ConfigBuilder

    builder = ConfigBuilder(project_root)
    settings = builder.build(config_dict)
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import (
    Settings,
    PathsConfig,
    LtpConfig,
    AliceConfig,
    DatabaseConfig,
    AuthConfig,
    MatchConfig,
    MatchHoneypotConfig,
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
    CorsConfig,
    ModulesConfig,
    ModuleRefConfig,
    TuringModuleRefConfig,
    BotPoolRefConfig,
    ScoreConfig,
    MidGameConfig,
    MetaConversationConfig,
    ScriptingConfig,
    LuaScriptEngineConfig,
    YamlScriptEngineConfig,
    OpeningConfig,
)


def resolve_env_variables(value: str) -> str:
    """
    解析字符串中的环境变量

    支持格式:
    - ${ENV_VAR} - 直接获取环境变量
    - ${ENV_VAR:default} - 如果环境变量不存在，使用默认值

    Args:
        value: 包含环境变量的字符串

    Returns:
        解析后的字符串
    """
    if not isinstance(value, str):
        return value

    # 处理 ${VAR:default} 或 ${VAR} 格式
    # 分组 1: 变量名，分组 2: 默认值 (可选)
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

    def replace_env(match):
        env_var = match.group(1)
        default_value = match.group(2)
        value = os.environ.get(env_var)
        if value is not None:
            return value
        elif default_value is not None:
            return default_value
        else:
            return match.group(0)  # 返回原始字符串

    return re.sub(pattern, replace_env, value)


def resolve_config_env_values(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归解析配置字典中的环境变量

    Args:
        config: 配置字典

    Returns:
        解析后的配置字典
    """
    resolved = {}
    for key, value in config.items():
        if isinstance(value, str):
            resolved[key] = resolve_env_variables(value)
        elif isinstance(value, dict):
            resolved[key] = resolve_config_env_values(value)
        elif isinstance(value, list):
            resolved[key] = [
                resolve_env_variables(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            resolved[key] = value
    return resolved


class ConfigBuilder:
    """
    配置构建器

    将原始配置字典构建为类型化的 Settings 对象。
    """

    def __init__(self, project_root: Path):
        """
        初始化配置构建器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root

    def build(self, config: Dict[str, Any]) -> Settings:
        """
        构建类型化配置对象

        Args:
            config: 配置字典

        Returns:
            Settings 实例

        Raises:
            KeyError: 缺少必填配置项时
            TypeError: 配置类型错误时
            ValueError: 配置值无效时
        """
        try:
            # 解析环境变量
            config = resolve_config_env_values(config)

            # 构建路径配置
            paths_cfg = config.get("paths", {})
            paths = self._build_paths_config(paths_cfg)

            # 构建模块引用配置
            modules = self._build_modules_config(config)

            # 构建 LTP 配置
            alice_cfg = config.get("alice", {})
            ltp_cfg = alice_cfg.get("ltp", {})
            ltp = self._build_ltp_config(ltp_cfg)

            # 构建 Alice 配置
            alice = self._build_alice_config(alice_cfg, paths, ltp)

            # 构建 Turing 配置
            turing_cfg = config.get("turing", {})
            turing = self._build_turing_config(turing_cfg, paths)

            # 获取 Sentry 配置（从环境变量优先读取）
            sentry_dsn = config.get("sentry_dsn", None)
            sentry_enabled = config.get("sentry_enabled", False)
            environment = config.get("environment", "production")

            return Settings(
                debug=self._get_optional(config, "debug", bool, False),
                log_level=self._get_optional(config, "log_level", str, "INFO"),
                paths=paths,
                modules=modules,
                alice=alice,
                turing=turing,
                sentry_dsn=sentry_dsn,
                sentry_enabled=sentry_enabled,
                environment=environment,
            )

        except KeyError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"配置构建失败：缺少配置项 {e}")
            raise
        except TypeError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"配置构建失败：类型错误 {e}")
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"配置构建失败：{e}", exc_info=True)
            raise

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
            
            opening_script_file = None
            if yaml_cfg.get("opening_script_file"):
                opening_script_file = Path(yaml_cfg["opening_script_file"])
                if not opening_script_file.is_absolute():
                    opening_script_file = paths.project_root / opening_script_file
            
            yaml_config = YamlScriptEngineConfig(
                script_file=script_file,
                opening_script_file=opening_script_file,
            )

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

    def _build_honeypot_config(self, cfg: Dict[str, Any]) -> HoneypotConfig:
        """构建钓鱼机器人配置"""
        return HoneypotConfig(
            reply_delay_min=self._get_optional(cfg, "reply_delay_min", float, 2.0, "turing.ai_bot.honeypot"),
            reply_delay_max=self._get_optional(cfg, "reply_delay_max", float, 8.0, "turing.ai_bot.honeypot"),
            opening_delay_min=self._get_optional(cfg, "opening_delay_min", float, 5.0, "turing.ai_bot.honeypot"),
            opening_delay_max=self._get_optional(cfg, "opening_delay_max", float, 15.0, "turing.ai_bot.honeypot"),
            typing_delay_per_char=self._get_optional(cfg, "typing_delay_per_char", float, 0.05, "turing.ai_bot.honeypot"),
            occasional_long_delay_probability=self._get_optional(cfg, "occasional_long_delay_probability", float, 0.1, "turing.ai_bot.honeypot"),
            occasional_long_delay_min=self._get_optional(cfg, "occasional_long_delay_min", float, 15.0, "turing.ai_bot.honeypot"),
            occasional_long_delay_max=self._get_optional(cfg, "occasional_long_delay_max", float, 60.0, "turing.ai_bot.honeypot"),
            meta_delay_multiplier=self._get_optional(cfg, "meta_delay_multiplier", float, 1.5, "turing.ai_bot.honeypot"),
            early_session_delay_multiplier=self._get_optional(cfg, "early_session_delay_multiplier", float, 1.3, "turing.ai_bot.honeypot"),
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
        cors_cfg = cfg.get("cors", {})
        score_cfg = cfg.get("score", {})
        mid_game_cfg = cfg.get("mid_game", {})
        meta_keywords = cfg.get("meta_keywords", [])
        meta_conversation_cfg = cfg.get("meta_conversation", {})

        # 构建元对话配置
        meta_conversation = MetaConversationConfig(
            enabled=self._get_optional(meta_conversation_cfg, "enabled", bool, True, "turing.meta_conversation"),
            keywords=self._get_optional(meta_conversation_cfg, "keywords", list, None, "turing.meta_conversation") or meta_keywords or [
                '真人', '机器', 'AI', '机器人', '人工智能', '程序', '算法'
            ],
        )

        # 安全提示：secret_key 必须从环境变量读取，YAML 中不应存储
        import os
        secret_key_from_env = os.environ.get("CONFIG_TURING_AUTH_SECRET_KEY")
        if not secret_key_from_env:
            # 尝试从配置读取（仅用于向后兼容，不推荐）
            secret_key = self._get_optional(auth_cfg, "secret_key", str, None, "turing.auth")
            if secret_key is None:
                logger = logging.getLogger(__name__)
                logger.error(
                    "❌ CONFIG_TURING_AUTH_SECRET_KEY 环境变量未设置！\n"
                    "   生成安全密钥：python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
                    "   或在 .env 文件中设置：CONFIG_TURING_AUTH_SECRET_KEY=your-secret-key"
                )
                raise ValueError("CONFIG_TURING_AUTH_SECRET_KEY 未设置")
        else:
            secret_key = secret_key_from_env

        # 构建匹配配置（概率分流版）
        match = MatchConfig(
            human_probability=self._get_optional(match_cfg, "human_probability", float, 0.30, "turing.match"),
            bot_probability=self._get_optional(match_cfg, "bot_probability", float, 0.70, "turing.match"),
            timeout_seconds=self._get_optional(match_cfg, "timeout_seconds", int, 10, "turing.match"),
            fake_delay_min_ms=self._get_optional(match_cfg, "fake_delay_min_ms", int, 1000, "turing.match"),
            fake_delay_max_ms=self._get_optional(match_cfg, "fake_delay_max_ms", int, 3000, "turing.match"),
            # 兼容旧字段
            timeout=self._get_optional(match_cfg, "timeout", int, 10, "turing.match"),
            fixed_wait_time=self._get_optional(match_cfg, "fixed_wait_time", int, 3, "turing.match"),
            ai_control_group_rate=self._get_optional(match_cfg, "ai_control_group_rate", float, 0.2, "turing.match"),
            honeypot_probability=self._get_optional(match_cfg, "honeypot_probability", float, 0.15, "turing.match"),
            honeypot_high_meta_probability=self._get_optional(match_cfg, "honeypot_high_meta_probability", float, 0.30, "turing.match"),
            time_distribution=match_cfg.get("time_distribution", {}),
        )

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
                secret_key=secret_key,  # 从环境变量读取
                initial_score=self._get_optional(auth_cfg, "initial_score", int, 100, "turing.auth"),
            ),
            match=MatchConfig(
                timeout=self._get_required(match_cfg, "timeout", int, "turing.match"),
                fixed_wait_time=self._get_optional(match_cfg, "fixed_wait_time", int, 3, "turing.match"),
                ai_control_group_rate=self._get_optional(match_cfg, "ai_control_group_rate", float, 0.2, "turing.match"),
                honeypot_probability=self._get_optional(match_cfg, "honeypot_probability", float, 0.15, "turing.match"),
                honeypot_high_meta_probability=self._get_optional(match_cfg, "honeypot_high_meta_probability", float, 0.30, "turing.match"),
                time_distribution=match_cfg.get("time_distribution", {}),
            ),
            ai_bot=AiBotConfig(
                name=self._get_required(ai_bot_cfg, "name", str, "turing.ai_bot"),
                typing_delay_base=self._get_required(ai_bot_cfg, "typing_delay_base", float, "turing.ai_bot"),
                typing_delay_per_char=self._get_required(ai_bot_cfg, "typing_delay_per_char", float, "turing.ai_bot"),
                honeypot=self._build_honeypot_config(ai_bot_cfg.get("honeypot", {})),
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
            cors=CorsConfig(
                origins=cors_cfg.get("origins", []),
            ),
            score=score,
            mid_game=mid_game,
            meta_conversation=meta_conversation,
            meta_keywords=meta_keywords,
        )

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


__all__ = [
    "ConfigBuilder",
]
