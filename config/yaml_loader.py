#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 配置加载器
================

负责加载和合并 YAML 配置文件。

用法:
    from config.yaml_loader import YamlLoader

    loader = YamlLoader(project_root)
    config = loader.load()
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .bot_loader import BotConfig, BotConfigLoader


class YamlLoader:
    """
    YAML 配置加载器

    负责加载:
    - 主配置文件 (config.yaml)
    - 模块专属配置 (config.alice.yaml, config.turing.yaml)
    - Bot 配置文件 (bots/*.yaml)
    """

    def __init__(self, project_root: Path):
        """
        初始化 YAML 配置加载器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root
        self._config: Dict[str, Any] = {}
        self._bot_configs: List[BotConfig] = []

    def load(self) -> Tuple[Dict[str, Any], List[BotConfig]]:
        """
        加载所有 YAML 配置

        Returns:
            (配置字典，Bot 配置列表)
        """
        # 1. 加载主配置
        self._load_main_config()

        # 2. 加载模块专属配置
        self._load_module_configs()

        # 3. 加载 Bot 配置
        self._load_bot_configs()

        return self._config, self._bot_configs

    def _load_main_config(self) -> None:
        """加载主配置文件"""
        main_config = self.project_root / "config.yaml"
        if not main_config.exists():
            raise FileNotFoundError(
                f"主配置文件不存在：{main_config}\n"
                f"请创建 config.yaml 文件，可参考 config.yaml.example"
            )

        try:
            with open(main_config, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"已加载主配置：{main_config}")
        except yaml.YAMLError as e:
            logger.error(f"解析主配置文件失败：{e}")
            raise

    def _load_module_configs(self) -> None:
        """加载模块专属配置"""
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
            try:
                with open(module_config, "r", encoding="utf-8") as f:
                    module_data = yaml.safe_load(f) or {}
                # 合并到主配置
                if module_name not in self._config:
                    self._config[module_name] = {}
                self._config[module_name].update(module_data)
                logger.info(f"已加载模块配置：{module_name} ({config_file})")
            except yaml.YAMLError as e:
                logger.error(f"解析模块配置文件失败 {module_name}: {e}")
                raise
        else:
            logger.warning(f"模块配置文件不存在：{module_config}")

    def _load_bot_configs(self) -> None:
        """从配置加载 Bot 配置"""
        # 从配置中获取 bots_dir
        paths_cfg = self._config.get("paths", {})
        bots_dir = paths_cfg.get("bots_dir", "bots")

        # 使用 BotConfigLoader 加载
        loader = BotConfigLoader(self.project_root)
        self._bot_configs = loader.load_all(bots_dir)
        logger.info(f"已加载 {len(self._bot_configs)} 个 Bot 配置")

    def get_config(self) -> Dict[str, Any]:
        """获取配置字典"""
        return self._config.copy()

    def get_bot_configs(self) -> List[BotConfig]:
        """获取 Bot 配置列表"""
        return self._bot_configs.copy()

    def get_bot_config_by_id(self, template_id: str) -> Optional[BotConfig]:
        """
        根据 ID 获取 Bot 配置

        Args:
            template_id: 模板 ID

        Returns:
            Bot 配置，找不到则返回 None
        """
        for config in self._bot_configs:
            if config.id == template_id:
                return config
        return None


__all__ = [
    "YamlLoader",
]
