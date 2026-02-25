#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量加载器
================

负责加载和解析环境变量配置。

用法:
    from config.env_loader import EnvLoader

    loader = EnvLoader()
    env_config = loader.load()
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class EnvLoader:
    """
    环境变量加载器

    支持 CONFIG_ 前缀的环境变量，例如:
    - CONFIG_TURING_SERVER_PORT=8000
    - CONFIG_ALICE_ENABLE_LTP=true
    """

    def __init__(self):
        """初始化环境变量加载器"""
        self._env: Dict[str, str] = {}

    def load(self) -> Dict[str, Any]:
        """
        从环境变量加载配置

        Returns:
            配置字典
        """
        self._env = dict(os.environ)
        return self._parse_env_vars()

    def load_dotenv(self, project_root: Path) -> None:
        """
        加载 .env 文件

        Args:
            project_root: 项目根目录
        """
        # 使用 python-dotenv 加载 .env 文件
        try:
            from dotenv import load_dotenv

            # 尝试加载 .env 文件
            env_file = project_root / ".env"
            if env_file.exists():
                load_dotenv(env_file)

            # 也支持 .env.local (用于本地开发覆盖)
            env_local = project_root / ".env.local"
            if env_local.exists():
                load_dotenv(env_local)
        except ImportError:
            # python-dotenv 未安装，跳过
            pass

    def _parse_env_vars(self) -> Dict[str, Any]:
        """
        解析环境变量为配置字典

        Returns:
            配置字典
        """
        result = {}
        for key, value in self._env.items():
            if key.startswith('CONFIG_'):
                config_key = key[7:].lower()  # 移除 CONFIG_ 前缀
                self._set_nested(result, config_key, self._parse_value(value))
        return result

    def _parse_value(self, value: str) -> Any:
        """
        字符串转类型

        Args:
            value: 字符串值

        Returns:
            转换后的值
        """
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

    def _set_nested(self, d: Dict[str, Any], key: str, value: Any) -> None:
        """
        设置嵌套字典的值

        Args:
            d: 目标字典
            key: 配置键 (支持点分隔，如 "turing.server.port")
            value: 配置值
        """
        keys = key.split(".")
        current = d
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def apply_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用环境变量覆盖到现有配置

        Args:
            config: 原始配置字典

        Returns:
            覆盖后的配置字典
        """
        env_config = self.load()
        return self._deep_merge(config, env_config)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = EnvLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


__all__ = [
    "EnvLoader",
]
