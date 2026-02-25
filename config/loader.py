#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
============

统一配置加载入口，整合各子模块：
- EnvLoader: 环境变量加载
- YamlLoader: YAML 配置加载
- ConfigBuilder: 类型化配置构建

加载优先级:
1. YAML 配置文件 (基础)
2. 模块专属配置 (config.alice.yaml, config.turing.yaml)
3. 环境变量覆盖 (CONFIG_ 前缀)

用法:
    from config.loader import ConfigLoader

    loader = ConfigLoader(project_root)
    settings = loader.load()
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .env_loader import EnvLoader
from .yaml_loader import YamlLoader
from .builder import ConfigBuilder
from .types import Settings
from .bot_loader import BotConfig


class ConfigLoader:
    """
    统一配置加载器

    协调各子模块完成配置加载流程。
    """

    def __init__(self, project_root: Path):
        """
        初始化配置加载器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root
        self._env_loader = EnvLoader()
        self._yaml_loader = YamlLoader(project_root)
        self._builder = ConfigBuilder(project_root)
        self._settings: Optional[Settings] = None

    def load(self) -> Settings:
        """
        加载所有配置

        流程:
        1. 加载 .env 文件
        2. 加载 YAML 配置
        3. 应用环境变量覆盖
        4. 构建类型化配置对象

        Returns:
            Settings 实例

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析失败
            KeyError: 缺少必填配置
            TypeError: 配置类型错误
        """
        # 1. 加载 .env 文件
        self._env_loader.load_dotenv(self.project_root)

        # 2. 加载 YAML 配置
        config, bot_configs = self._yaml_loader.load()

        # 3. 应用环境变量覆盖
        config = self._env_loader.apply_overrides(config)

        # 4. 构建类型化配置对象
        self._settings = self._builder.build(config)

        logger.info(
            f"配置加载完成："
            f"Bot 配置={len(bot_configs)}, "
            f"调试模式={self._settings.debug}"
        )

        return self._settings

    def get_bot_configs(self) -> List[BotConfig]:
        """获取已加载的 Bot 配置"""
        return self._yaml_loader.get_bot_configs()

    def get_bot_config_by_id(self, template_id: str) -> Optional[BotConfig]:
        """根据 ID 获取 Bot 配置"""
        return self._yaml_loader.get_bot_config_by_id(template_id)

    @property
    def settings(self) -> Optional[Settings]:
        """获取已加载的 Settings 对象"""
        return self._settings


# 全局单例
_project_root = Path(__file__).parent.parent
_loader = ConfigLoader(_project_root)
settings = _loader.load()


__all__ = [
    "ConfigLoader",
    "settings",
]
