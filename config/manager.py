#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理器
================

提供统一的配置管理功能，支持:
- 多配置源 (YAML/ENV/内存)
- 配置验证
- Bot 配置管理
- 运行时配置覆盖
- 配置快照 (回滚)
- 配置变更监听

用法:
    from config.manager import ConfigManager, get_config_manager

    # 获取全局实例
    config_mgr = get_config_manager()

    # 访问配置
    port = config_mgr.get('turing.server.port')

    # 获取 Bot 配置
    bot_config = config_mgr.get_bot_config("default")
"""

import threading
import time
import yaml
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from .sources import ConfigSource, YamlConfigSource, EnvConfigSource, MemoryConfigSource
from .validator import ConfigValidator, build_default_validator, validate_bot_configs, validate_scripting_paths
from .bot_loader import BotConfig, BotConfigLoader
from .builder import ConfigBuilder
from .types import Settings, ScriptingConfig


class ConfigManager:
    """
    统一配置管理器

    特性:
    - 多配置源支持 (YAML/ENV/内存)
    - 配置验证
    - Bot 配置管理
    - 运行时配置覆盖
    - 配置快照 (回滚)
    - 配置变更监听

    配置源优先级 (从高到低):
    1. 内存配置 (运行时覆盖)
    2. 环境变量
    3. YAML 文件
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            project_root: 项目根目录
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = project_root
        self._sources: Dict[str, ConfigSource] = {}
        self._validator = build_default_validator()
        self._bot_configs: Dict[str, BotConfig] = {}
        self._memory_source = MemoryConfigSource()
        self._snapshots: List[Tuple[float, Dict[str, Any]]] = []
        self._lock = threading.RLock()
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._config: Dict[str, Any] = {}
        self._loaded = False
        self._settings: Optional[Settings] = None
        self._builder = ConfigBuilder(project_root)

        # 配置变更审计日志
        self._audit_log: List[Dict[str, Any]] = []
        self._audit_log_max_size = 1000  # 最多保留 1000 条审计记录

    def add_source(self, name: str, source: ConfigSource, priority: int = 0) -> 'ConfigManager':
        """
        添加配置源

        Args:
            name: 配置源名称
            source: 配置源实例
            priority: 优先级 (未使用，保留用于未来扩展)

        Returns:
            self (支持链式调用)
        """
        with self._lock:
            self._sources[name] = source
            logger.debug(f"已添加配置源：{name}")
        return self

    def remove_source(self, name: str) -> bool:
        """
        移除配置源

        Args:
            name: 配置源名称

        Returns:
            是否移除成功
        """
        with self._lock:
            if name in self._sources:
                del self._sources[name]
                logger.debug(f"已移除配置源：{name}")
                return True
            return False

    def load(self) -> Settings:
        """
        从所有配置源加载配置

        优先级：内存 > 环境变量 > YAML

        Returns:
            类型化配置对象

        Raises:
            ValueError: 配置验证失败时抛出
        """
        with self._lock:
            merged: Dict[str, Any] = {}

            # 1. 加载 YAML 配置 (最低优先级)
            yaml_source = self._sources.get('yaml')
            if yaml_source:
                yaml_data = yaml_source.load()
                merged = self._deep_merge(merged, yaml_data)
                logger.info(f"已加载 YAML 配置：{yaml_source.name}")

            # 2. 加载模块专属配置 (config.alice.yaml, config.turing.yaml)
            self._load_module_configs(merged)

            # 3. 加载环境变量 (覆盖 YAML)
            env_source = self._sources.get('env')
            if env_source:
                env_data = env_source.load()
                if env_data:
                    merged = self._deep_merge(merged, env_data)
                    logger.info(f"已加载环境变量配置 (共 {len(env_data)} 项)")

            # 4. 加载内存配置 (最高优先级)
            memory_data = self._memory_source.load()
            if memory_data:
                merged = self._deep_merge(merged, memory_data)

            # 5. 验证配置
            errors = self._validator.validate(merged)
            error_count = sum(1 for e in errors if e.severity == 'error')
            warning_count = sum(1 for e in errors if e.severity == 'warning')

            for error in errors:
                if error.severity == 'error':
                    logger.error(f"配置验证错误 [{error.path}]: {error.message}")
                else:
                    logger.warning(f"配置验证警告 [{error.path}]: {error.message}")

            if error_count > 0:
                raise ValueError(f"配置验证失败：共 {error_count} 个错误")

            self._config = merged

            # 6. 加载 Bot 配置
            self._load_bot_configs(merged)

            # 7. 保存快照
            self._save_snapshot()

            self._loaded = True
            self._notify_listeners(merged)

            # 8. 构建类型化配置对象
            self._settings = self._builder.build(merged)

            logger.info(
                f"配置加载完成 (共 {len(merged)} 项，Bot 配置：{len(self._bot_configs)} 个)"
            )
            return self._settings

    def _load_module_configs(self, merged: Dict[str, Any]) -> None:
        """加载模块专属配置 (config.alice.yaml, config.turing.yaml)"""
        modules_cfg = merged.get("modules", {})

        # Alice 模块配置
        alice_ref = modules_cfg.get("alice", {})
        alice_config_file = alice_ref.get("config_file", "config.alice.yaml")
        self._load_single_module_config(merged, "alice", alice_config_file)

        # Turing 模块配置
        turing_ref = modules_cfg.get("turing", {})
        turing_config_file = turing_ref.get("config_file", "config.turing.yaml")
        self._load_single_module_config(merged, "turing", turing_config_file)

    def _load_single_module_config(
        self,
        merged: Dict[str, Any],
        module_name: str,
        config_file: str
    ) -> None:
        """
        加载单个模块配置

        Args:
            merged: 合并后的配置字典
            module_name: 模块名称
            config_file: 配置文件路径
        """
        module_config = self.project_root / config_file
        if module_config.exists():
            with open(module_config, "r", encoding="utf-8") as f:
                module_data = yaml.safe_load(f) or {}
            # 合并到主配置
            if module_name not in merged:
                merged[module_name] = {}
            merged[module_name].update(module_data)
            logger.info(f"已加载模块配置：{module_name} ({config_file})")
        else:
            logger.warning(f"模块配置文件不存在：{module_config}")

    def _load_bot_configs(self, config: Dict[str, Any]) -> None:
        """从配置加载 Bot 配置"""
        paths_cfg = config.get('paths', {})
        bots_dir = paths_cfg.get('bots_dir', 'bots')

        loader = BotConfigLoader(self.project_root)
        bot_configs = loader.load_all(bots_dir)

        # 验证 Bot 配置
        bot_errors = validate_bot_configs([cfg.to_dict() for cfg in bot_configs])
        for error in bot_errors:
            logger.error(f"Bot 配置验证错误 [{error.path}]: {error.message}")

        if bot_errors:
            raise ValueError(f"Bot 配置验证失败：共 {len(bot_errors)} 个错误")

        # 存储 Bot 配置
        self._bot_configs = {cfg.id: cfg for cfg in bot_configs}
        logger.info(f"已加载 {len(self._bot_configs)} 个 Bot 配置")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键 (支持点分隔，如 "turing.server.port")
            default: 默认值

        Returns:
            配置值
        """
        with self._lock:
            return self._get_nested(self._config, key, default)

    def set(
        self,
        key: str,
        value: Any,
        persist: bool = False,
        notify: bool = True,
        source: str = "runtime"
    ) -> bool:
        """
        设置配置值 (运行时覆盖)

        Args:
            key: 配置键 (支持点分隔)
            value: 配置值
            persist: 是否持久化到 YAML 文件
            notify: 是否通知监听器
            source: 配置变更来源 (如 "runtime", "api", "admin")

        Returns:
            是否设置成功
        """
        with self._lock:
            # 获取旧值用于审计
            old_value = self._get_nested(self._config, key, None)

            # 更新内存源
            self._memory_source.update(key, value)

            # 构建嵌套字典并合并到 _config
            override_dict = {}
            self._set_nested(override_dict, key, value)
            self._config = self._deep_merge(self._config, override_dict)

            # 记录审计日志
            self._log_config_change(key, old_value, value, source)

            logger.debug(f"配置已更新 (运行时): {key} = {value}")

            if persist:
                self._persist_to_yaml(key, value)

            if notify:
                self._notify_listeners(self._config)

            # 重新构建 settings
            if self._loaded:
                try:
                    self._settings = self._builder.build(self._config)
                except Exception as e:
                    logger.warning(f"重新构建配置失败：{e}")

            return True

    def _log_config_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        source: str = "runtime"
    ):
        """
        记录配置变更审计日志

        Args:
            key: 配置键
            old_value: 旧值
            new_value: 新值
            source: 变更来源
        """
        import time
        from alice.utils.sanitizer import sanitize_value

        audit_entry = {
            "timestamp": time.time(),
            "action": "config_change",
            "key": key,
            "old_value": sanitize_value(old_value) if old_value is not None else None,
            "new_value": sanitize_value(new_value),
            "source": source,
        }

        self._audit_log.append(audit_entry)

        # 限制审计日志大小
        if len(self._audit_log) > self._audit_log_max_size:
            self._audit_log = self._audit_log[-self._audit_log_max_size:]

        logger.info(f"配置变更审计：{key} = {sanitize_value(new_value)} (来源：{source})")

    def _persist_to_yaml(self, key: str, value: Any) -> bool:
        """持久化配置到 YAML 文件"""
        yaml_source = self._sources.get('yaml')
        if not yaml_source:
            logger.warning("无法持久化：YAML 配置源未设置")
            return False

        try:
            current_yaml = yaml_source.load()
            self._set_nested(current_yaml, key, value)

            if yaml_source.save(current_yaml):
                logger.info(f"配置已持久化：{key}")
                return True
        except Exception as e:
            logger.error(f"持久化配置失败：{e}")

        return False

    def delete(self, key: str) -> bool:
        """
        删除配置项 (仅影响运行时覆盖)

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        with self._lock:
            return self._memory_source.delete(key)

    def get_bot_config(self, template_id: Optional[str] = None) -> Optional[BotConfig]:
        """
        获取 Bot 配置

        Args:
            template_id: 模板 ID (可选，不传则返回默认模板)

        Returns:
            Bot 配置，找不到则返回 None
        """
        if template_id is None:
            # 返回默认模板
            default_id = self.get('turing.bot_pool.default_template', 'default')
            return self._bot_configs.get(default_id)

        return self._bot_configs.get(template_id)

    def get_bot_config_or_raise(self, template_id: Optional[str] = None) -> BotConfig:
        """
        获取 Bot 配置 (失败则抛出异常)

        Args:
            template_id: 模板 ID

        Returns:
            Bot 配置

        Raises:
            ValueError: 配置不存在时抛出
        """
        config = self.get_bot_config(template_id)
        if config is None:
            template_id_str = template_id if template_id else "默认"
            raise ValueError(f"Bot 配置不存在：{template_id_str}")
        return config

    def list_bot_configs(self) -> List[str]:
        """
        列出所有 Bot 配置 ID

        Returns:
            模板 ID 列表
        """
        return list(self._bot_configs.keys())

    # =========================================================================
    # 脚本配置访问方法
    # =========================================================================

    def get_scripting_config(self) -> Optional[ScriptingConfig]:
        """
        获取脚本引擎配置

        Returns:
            ScriptingConfig 实例，未配置则返回 None
        """
        with self._lock:
            return self._settings.alice.scripting if self._settings else None

    def get_lua_script_dir(self) -> Optional[Path]:
        """
        获取 Lua 脚本目录

        Returns:
            Lua 脚本目录路径，未配置则返回 None
        """
        with self._lock:
            scripting = self._settings.alice.scripting if self._settings else None
            if scripting and scripting.lua:
                return scripting.lua.script_dir
            return None

    def get_yaml_script_file(self) -> Optional[Path]:
        """
        获取 YAML 脚本文件路径

        Returns:
            YAML 脚本文件路径，未配置则返回 None
        """
        with self._lock:
            scripting = self._settings.alice.scripting if self._settings else None
            if scripting and scripting.yaml:
                return scripting.yaml.script_file
            return None

    def list_lua_scripts(self) -> List[str]:
        """
        列出所有 Lua 脚本 ID

        Returns:
            脚本 ID 列表
        """
        lua_dir = self.get_lua_script_dir()
        if not lua_dir or not lua_dir.exists():
            return []
        return [f.stem for f in lua_dir.glob("*.lua")]

    def validate_scripting_paths(self) -> List:
        """
        验证脚本配置路径存在性

        Returns:
            验证错误列表
        """
        with self._lock:
            return validate_scripting_paths(self._config, self.project_root)

    def reload(self) -> bool:
        """
        重新加载配置

        注意：会清除所有运行时覆盖

        Returns:
            是否重新加载成功
        """
        with self._lock:
            # 清除运行时覆盖
            self._memory_source = MemoryConfigSource()

            # 重新加载
            try:
                self.load()
                logger.info("配置已重新加载 (运行时覆盖已清除)")
                return True
            except Exception as e:
                logger.error(f"重新加载配置失败：{e}")
                return False

    def rollback(self, to_timestamp: Optional[float] = None) -> bool:
        """
        回滚配置到指定时间点

        Args:
            to_timestamp: 目标时间戳 (None 则回滚到上一个状态)

        Returns:
            是否回滚成功
        """
        with self._lock:
            if not self._snapshots:
                logger.warning("没有可用的配置快照")
                return False

            if to_timestamp is None:
                # 回滚到上一个快照
                if len(self._snapshots) < 2:
                    logger.warning("没有可回滚的快照")
                    return False
                target = self._snapshots[-2]
            else:
                # 找到最近的早于指定时间的快照
                target = None
                for ts, snapshot in reversed(self._snapshots):
                    if ts <= to_timestamp:
                        target = (ts, snapshot)
                        break

            if target is None:
                logger.warning("未找到匹配的配置快照")
                return False

            self._config = target[1].copy()
            self._memory_source = MemoryConfigSource(self._config)
            logger.info(f"配置已回滚到时间点：{target[0]}")
            return True

    def get_history(self, limit: int = 10) -> List[Tuple[float, int]]:
        """
        获取配置历史

        Args:
            limit: 最多返回的记录数

        Returns:
            (时间戳，配置项数量) 列表
        """
        with self._lock:
            return [(ts, len(cfg)) for ts, cfg in self._snapshots[-limit:]]

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加配置变更监听器

        Args:
            callback: 回调函数，接收配置字典参数
        """
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
                logger.debug(f"已添加配置监听器")

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        移除配置变更监听器

        Args:
            callback: 回调函数

        Returns:
            是否移除成功
        """
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)
                logger.debug(f"已移除配置监听器")
                return True
            return False

    def clear_listeners(self):
        """清空所有监听器"""
        with self._lock:
            self._listeners.clear()

    # =========================================================================
    # 审计日志方法
    # =========================================================================

    def get_audit_log(
        self,
        limit: int = 100,
        key_filter: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取配置变更审计日志

        Args:
            limit: 最多返回的记录数
            key_filter: 按配置键过滤
            source_filter: 按变更来源过滤

        Returns:
            审计日志列表
        """
        with self._lock:
            logs = self._audit_log.copy()

        # 过滤
        if key_filter:
            logs = [log for log in logs if log.get('key') == key_filter]
        if source_filter:
            logs = [log for log in logs if log.get('source') == source_filter]

        # 按时间倒序排列，返回最新的
        logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return logs[-limit:]

    def clear_audit_log(self):
        """清空审计日志"""
        with self._lock:
            self._audit_log.clear()
        logger.debug("审计日志已清空")

    def export_audit_log(self, format: str = "json") -> str:
        """
        导出审计日志

        Args:
            format: 导出格式 (json, csv)

        Returns:
            格式化后的日志字符串
        """
        import json
        import csv
        import io

        with self._lock:
            logs = self._audit_log.copy()

        if format.lower() == "json":
            return json.dumps(logs, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            return output.getvalue()
        else:
            raise ValueError(f"不支持的导出格式：{format}")

    def _notify_listeners(self, config: Dict[str, Any]):
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener(config)
            except Exception as e:
                logger.error(f"配置监听器执行失败：{e}")

    def _save_snapshot(self):
        """保存配置快照"""
        self._snapshots.append((time.time(), self._config.copy()))
        # 限制快照数量
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]

    def get_all(self) -> Dict[str, Any]:
        """
        获取完整配置

        Returns:
            配置字典
        """
        with self._lock:
            return self._config.copy()

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节

        Args:
            section: 配置节名称 (如 "turing", "alice")

        Returns:
            配置节字典
        """
        with self._lock:
            return self._get_nested(self._config, section, {})

    @property
    def bot_configs(self) -> Dict[str, BotConfig]:
        """获取所有 Bot 配置 (只读)"""
        return self._bot_configs.copy()

    @property
    def validator(self) -> ConfigValidator:
        """获取配置验证器"""
        return self._validator

    @property
    def settings(self) -> Optional[Settings]:
        """获取类型化配置对象"""
        return self._settings

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _get_nested(d: Dict[str, Any], path: str, default: Any = None) -> Any:
        """获取嵌套字典的值"""
        keys = path.split('.')
        current = d
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @staticmethod
    def _set_nested(d: Dict[str, Any], path: str, value: Any):
        """设置嵌套字典的值"""
        keys = path.split(".")
        current = d
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value


# =============================================================================
# 全局单例
# =============================================================================

_config_manager: Optional[ConfigManager] = None
_config_lock = threading.Lock()


def get_config_manager(project_root: Optional[Path] = None) -> ConfigManager:
    """
    获取全局配置管理器实例 (懒加载)

    Args:
        project_root: 项目根目录 (仅首次调用时有效)

    Returns:
        ConfigManager 实例
    """
    global _config_manager

    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                root = project_root or Path(__file__).parent.parent
                _config_manager = ConfigManager(root)
                _config_manager.add_source('yaml', YamlConfigSource(
                    root / 'config.yaml'
                ))
                _config_manager.add_source('env', EnvConfigSource())
                _config_manager.load()

    return _config_manager


def reset_config_manager():
    """重置配置管理器 (用于测试)"""
    global _config_manager
    with _config_lock:
        _config_manager = None


# 延迟加载 settings，避免循环导入
class _SettingsProxy:
    """配置代理类，用于延迟加载"""
    
    def __getattr__(self, name: str) -> Any:
        return getattr(get_config_manager().settings, name)


settings = _SettingsProxy()


__all__ = [
    "ConfigManager",
    "get_config_manager",
    "reset_config_manager",
    "settings",
]
