#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
统一管理所有配置，支持：
- 环境变量 (.env)
- YAML 配置文件
- 环境变量覆盖
"""

import os
from pathlib import Path
from typing import Any, Dict, Union

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
)


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
        
        # 5. 构建类型化配置对象
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
        
        # 模块专属配置 (可选，用于覆盖主配置)
        for suffix in ["alice", "turing"]:
            module_config = self.project_root / f"config.{suffix}.yaml"
            if module_config.exists():
                with open(module_config, "r", encoding="utf-8") as f:
                    module_data = yaml.safe_load(f) or {}
                # 深度合并
                self._merge_config(suffix, module_data)
    
    def _merge_config(self, key: str, data: Dict[str, Any]) -> None:
        """深度合并配置"""
        if key not in self._config:
            self._config[key] = {}
        
        for k, v in data.items():
            if isinstance(v, dict) and k in self._config[key] and isinstance(self._config[key][k], dict):
                self._config[key][k].update(v)
            else:
                self._config[key][k] = v
    
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
    
    def _build_settings(self) -> Settings:
        """构建类型化配置对象"""
        paths_cfg = self._config.get("paths", {})
        alice_cfg = self._config.get("alice", {})
        turing_cfg = self._config.get("turing", {})
        
        # 构建路径配置
        paths = self._build_paths_config(paths_cfg)
        
        # 构建 LTP 配置
        ltp_cfg = alice_cfg.get("ltp", {})
        ltp = self._build_ltp_config(ltp_cfg)
        
        # 构建 Alice 配置
        alice = self._build_alice_config(alice_cfg, paths, ltp)
        
        # 构建 Turing 配置
        turing = self._build_turing_config(turing_cfg, paths)
        
        return Settings(
            debug=self._get_optional(self._config, "debug", bool, False),
            log_level=self._get_optional(self._config, "log_level", str, "INFO"),
            paths=paths,
            alice=alice,
            turing=turing,
        )
    
    def _build_paths_config(self, cfg: Dict[str, Any]) -> PathsConfig:
        """构建路径配置"""
        project_root = self._get_required(cfg, "project_root", str, "paths")
        # 如果是相对路径，相对于当前 config.yaml 所在位置
        if not Path(project_root).is_absolute():
            project_root = self.project_root / project_root
        
        return PathsConfig(
            project_root=Path(project_root),
            alice_dir=Path(cfg.get("alice_dir", Path(project_root) / "alice")),
            turing_dir=Path(cfg.get("turing_dir", Path(project_root) / "turing_test")),
            log_dir=Path(cfg.get("log_dir", Path(project_root) / "logs")),
            data_dir=Path(cfg.get("data_dir", Path(project_root) / "data")),
            scripts_dir=Path(cfg.get("scripts_dir", Path(project_root) / "alice" / "scripts")),
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
        return AliceConfig(
            enable_ltp=self._get_required(cfg, "enable_ltp", bool, "alice"),
            enable_ner=self._get_required(cfg, "enable_ner", bool, "alice"),
            enable_log=self._get_required(cfg, "enable_log", bool, "alice"),
            ner_use_ltp=self._get_required(cfg, "ner_use_ltp", bool, "alice"),
            hot_reload=self._get_required(cfg, "hot_reload", bool, "alice"),
            hot_reload_mode=self._get_optional(cfg, "hot_reload_mode", str, "auto", "alice"),
            hot_reload_poll_interval=self._get_optional(cfg, "hot_reload_poll_interval", float, 2.0, "alice"),
            script_file=self._get_required(cfg, "script_file", Path, "alice"),
            rules_file=self._get_required(cfg, "rules_file", Path, "alice"),
            semantic_tags_file=self._get_optional(
                cfg, "semantic_tags_file", Path,
                paths.scripts_dir / "semantic_tags.yaml", "alice"
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
        
        return TuringConfig(
            database=DatabaseConfig(
                url=self._get_required(db_cfg, "url", str, "turing.database"),
            ),
            auth=AuthConfig(
                invite_code_length=self._get_required(auth_cfg, "invite_code_length", int, "turing.auth"),
            ),
            match=MatchConfig(
                timeout=self._get_required(match_cfg, "timeout", int, "turing.match"),
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
            bot_pool=BotPoolConfig(
                min_instances=self._get_required(bot_pool_cfg, "min_instances", int, "turing.bot_pool"),
                max_instances=self._get_required(bot_pool_cfg, "max_instances", int, "turing.bot_pool"),
                idle_timeout=self._get_required(bot_pool_cfg, "idle_timeout", int, "turing.bot_pool"),
                max_concurrent=self._get_required(bot_pool_cfg, "max_concurrent", int, "turing.bot_pool"),
            ),
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
        )


# 全局单例
_project_root = Path(__file__).parent.parent
_loader = ConfigLoader(_project_root)
settings = _loader.load()
