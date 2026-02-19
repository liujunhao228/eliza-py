#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理器模块

集中管理所有配置项，支持：
- 多层级配置加载
- 动态配置更新
- 插件配置注册
- 配置验证
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from alice.exceptions import (
    InvalidConfigurationError,
    MissingConfigurationError,
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    统一配置管理器
    
    功能:
    - 集中管理所有配置项
    - 支持多层级配置（系统 > 用户 > 默认）
    - 支持插件配置动态注册
    - 配置变更通知
    - 配置持久化
    """

    def __init__(self, config_dirs: Optional[List[Path]] = None):
        """
        初始化配置管理器
        
        Args:
            config_dirs: 配置文件目录列表，按优先级排序
        """
        self._configs: Dict[str, Any] = {}
        self._config_dirs = config_dirs or []
        self._callbacks: Dict[str, List[callable]] = {}
        
        # 加载配置
        self._load_configs()

    def _load_configs(self) -> None:
        """从配置文件加载配置"""
        for config_dir in self._config_dirs:
            if not config_dir.exists():
                continue
            
            # 加载主配置文件
            main_config = config_dir / "config.json"
            if main_config.exists():
                self._load_json_config(main_config)
            
            # 加载插件配置
            plugins_config = config_dir / "plugins"
            if plugins_config.exists():
                self._load_plugin_configs(plugins_config)

    def _load_json_config(self, config_path: Path) -> None:
        """
        加载 JSON 配置文件

        Args:
            config_path: 配置文件路径

        Raises:
            InvalidConfigurationError: 配置文件格式错误
            MissingConfigurationError: 配置文件不存在
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self._merge_config(config)
                logger.info(f"配置已加载：{config_path}")
        except json.JSONDecodeError as e:
            raise InvalidConfigurationError(
                f"配置文件格式错误：{config_path.name}, "
                f"位置：第{e.lineno}行第{e.colno}列，"
                f"详情：{e.msg}"
            ) from e
        except FileNotFoundError as e:
            raise MissingConfigurationError(
                f"配置文件不存在：{config_path}, "
                f"请检查文件路径是否正确"
            ) from e
        except IOError as e:
            raise MissingConfigurationError(
                f"无法读取配置文件：{config_path}, "
                f"请检查文件权限"
            ) from e

    def _load_plugin_configs(self, plugins_dir: Path) -> None:
        """
        加载插件配置目录

        Args:
            plugins_dir: 插件配置目录

        Raises:
            InvalidConfigurationError: 插件配置文件格式错误
        """
        if not plugins_dir.exists():
            return

        for config_file in plugins_dir.glob("*.json"):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    plugin_config = json.load(f)
                    plugin_name = config_file.stem
                    self._configs[f"plugin.{plugin_name}"] = plugin_config
                    logger.info(f"插件配置已加载：{plugin_name}")
            except json.JSONDecodeError as e:
                raise InvalidConfigurationError(
                    f"插件配置文件格式错误：{config_file.name}, "
                    f"位置：第{e.lineno}行第{e.colno}列"
                ) from e
            except Exception as e:
                logger.error(f"加载插件配置失败 {config_file}: {e}")

    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        合并配置（新配置覆盖旧配置）
        
        Args:
            new_config: 新配置字典
        """
        self._configs.update(new_config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键（支持点号分隔，如 "plugin.curiosity.priority"）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._configs
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

    def set(self, key: str, value: Any, persist: bool = False) -> bool:
        """
        设置配置项
        
        Args:
            key: 配置键
            value: 配置值
            persist: 是否持久化到文件
            
        Returns:
            是否设置成功
        """
        keys = key.split(".")
        config = self._configs
        
        # 导航到父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        old_value = config.get(keys[-1])
        config[keys[-1]] = value
        
        # 触发回调
        self._notify_callbacks(key, old_value, value)
        
        # 持久化
        if persist:
            return self._persist_config()
        
        return True

    def register_plugin_config(self, plugin_name: str, config_dict: Dict[str, Any]) -> None:
        """
        注册插件配置
        
        Args:
            plugin_name: 插件名称
            config_dict: 配置字典
        """
        self._configs[f"plugin.{plugin_name}"] = config_dict
        logger.info(f"插件配置已注册：{plugin_name}")

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件配置字典
        """
        return self.get(f"plugin.{plugin_name}", {})

    def register_callback(self, key: str, callback: callable) -> None:
        """
        注册配置变更回调
        
        Args:
            key: 配置键
            callback: 回调函数 (old_value, new_value) -> None
        """
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def _notify_callbacks(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """通知配置变更回调"""
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                try:
                    callback(old_value, new_value)
                except Exception as e:
                    logger.error(f"配置回调执行失败 {key}: {e}")

    def _persist_config(self) -> bool:
        """
        持久化配置到文件

        Returns:
            是否持久化成功

        Raises:
            MissingConfigurationError: 无法写入配置文件
        """
        if not self._config_dirs:
            logger.warning("没有配置目录，无法持久化")
            return False

        config_path = self._config_dirs[0] / "config.json"

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._configs, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已持久化：{config_path}")
            return True
        except IOError as e:
            raise MissingConfigurationError(
                f"无法写入配置文件：{config_path}, "
                f"请检查目录权限"
            ) from e

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典副本
        """
        return self._configs.copy()

    def clear(self) -> None:
        """清空所有配置"""
        self._configs.clear()

    def reload(self) -> bool:
        """
        重新加载配置
        
        Returns:
            是否加载成功
        """
        old_configs = self._configs.copy()
        
        try:
            self._configs.clear()
            self._load_configs()
            logger.info("配置已重新加载")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败：{e}")
            # 恢复旧配置
            self._configs = old_configs
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取配置统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_keys": len(self._configs),
            "config_dirs": [str(d) for d in self._config_dirs],
            "plugins_registered": sum(
                1 for k in self._configs if k.startswith("plugin.")
            ),
        }
