#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置源抽象模块
==============

定义配置源的抽象基类和具体实现。

支持的配置源:
- YAML 文件配置源
- 环境变量配置源
- 内存配置源 (用于运行时覆盖)
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from loguru import logger


class ConfigSource(ABC):
    """配置源抽象基类"""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """加载配置为字典"""
        pass

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> bool:
        """保存配置"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """配置源名称"""
        pass


class YamlConfigSource(ConfigSource):
    """
    YAML 文件配置源

    用于从 YAML 文件加载和保存配置。
    """

    def __init__(self, path: Path, required: bool = True):
        """
        初始化 YAML 配置源

        Args:
            path: YAML 文件路径
            required: 是否必须存在
        """
        self.path = path
        self.required = required

    def load(self) -> Dict[str, Any]:
        """从 YAML 文件加载配置"""
        if not self.path.exists():
            if self.required:
                raise FileNotFoundError(f"配置文件不存在：{self.path}")
            logger.warning(f"配置文件不存在 (非必填): {self.path}")
            return {}

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            logger.debug(f"已加载 YAML 配置：{self.path}")
            return data
        except yaml.YAMLError as e:
            logger.error(f"解析 YAML 配置失败：{self.path}, 错误：{e}")
            raise

    def save(self, data: Dict[str, Any]) -> bool:
        """保存配置到 YAML 文件"""
        try:
            # 确保目录存在
            self.path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            logger.info(f"配置已保存到：{self.path}")
            return True
        except Exception as e:
            logger.error(f"保存 YAML 配置失败：{e}")
            return False

    @property
    def name(self) -> str:
        return f"yaml:{self.path}"


class EnvConfigSource(ConfigSource):
    """
    环境变量配置源

    支持 CONFIG_ 前缀的环境变量，例如:
    - CONFIG_TURING_SERVER_PORT=8000
    - CONFIG_ALICE_ENABLE_LTP=true
    """

    def load(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        result = {}
        for key, value in os.environ.items():
            if key.startswith('CONFIG_'):
                config_key = key[7:].lower()  # 移除 CONFIG_ 前缀
                self._set_nested(result, config_key, self._parse_value(value))
        logger.debug(f"已加载环境变量配置 (共 {len(result)} 项)")
        return result

    def save(self, data: Dict[str, Any]) -> bool:
        """
        保存配置到环境变量

        注意：这仅在当前进程有效，无法持久化
        """
        try:
            for key, value in self._flatten(data).items():
                env_key = f"CONFIG_{key.upper().replace('.', '_')}"
                os.environ[env_key] = str(value)
            logger.debug(f"已更新环境变量配置")
            return True
        except Exception as e:
            logger.error(f"更新环境变量失败：{e}")
            return False

    @property
    def name(self) -> str:
        return "env"

    @staticmethod
    def _parse_value(value: str) -> Any:
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
        if (v.startswith('"') and v.endswith('"')) or \
           (v.startswith("'") and v.endswith("'")):
            return v[1:-1]

        return v

    @staticmethod
    def _flatten(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """扁平化嵌套字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict) and v:
                items.extend(EnvConfigSource._flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def _set_nested(d: Dict[str, Any], key: str, value: Any):
        """设置嵌套字典的值"""
        keys = key.split(".")
        current = d
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value


class MemoryConfigSource(ConfigSource):
    """
    内存配置源

    用于运行时配置覆盖，不持久化。
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        """
        初始化内存配置源

        Args:
            initial: 初始配置字典
        """
        self._data = initial.copy() if initial else {}

    def load(self) -> Dict[str, Any]:
        """获取当前内存中的配置"""
        return self._data.copy()

    def save(self, data: Dict[str, Any]) -> bool:
        """保存配置到内存"""
        self._data = data.copy()
        logger.debug(f"内存配置已更新 ({len(data)} 项)")
        return True

    def update(self, key: str, value: Any):
        """
        更新单个配置项

        Args:
            key: 配置键 (支持点分隔，如 "turing.server.port")
            value: 配置值
        """
        self._set_nested(self._data, key, value)
        logger.debug(f"内存配置已更新：{key} = {value}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._get_nested(self._data, key, default)

    def delete(self, key: str) -> bool:
        """
        删除配置项

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        keys = key.split(".")
        current = self._data
        for k in keys[:-1]:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False

        if keys[-1] in current:
            del current[keys[-1]]
            return True
        return False

    def clear(self):
        """清空所有配置"""
        self._data.clear()
        logger.debug("内存配置已清空")

    @property
    def name(self) -> str:
        return "memory"

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

    @staticmethod
    def _get_nested(d: Dict[str, Any], path: str, default: Any = None) -> Any:
        """获取嵌套字典的值"""
        keys = path.split(".")
        current = d
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current


__all__ = [
    "ConfigSource",
    "YamlConfigSource",
    "EnvConfigSource",
    "MemoryConfigSource",
]
