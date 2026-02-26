#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 配置加载器
==============

从 bots/ 目录加载 Bot 配置文件。

用法:
    from config.bot_loader import BotConfigLoader
    
    loader = BotConfigLoader()
    configs = loader.load_all("bots/")
    
    for config in configs:
        print(f"加载 Bot: {config.name}")
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from config.types import OpeningConfig


@dataclass
class BotConfig:
    """
    Bot 配置文件类型定义

    定义从 bots/*.yaml 文件加载的 Bot 配置。
    """
    id: str
    name: str
    description: str = ""
    script_file: Optional[Path] = None
    rules_file: Optional[Path] = None
    opening: Optional[OpeningConfig] = None
    cache_size: int = 50
    typing_delay_base: float = 1.0
    typing_delay_per_char: float = 0.05
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'script_file': str(self.script_file) if self.script_file else None,
            'rules_file': str(self.rules_file) if self.rules_file else None,
            'cache_size': self.cache_size,
            'typing_delay_base': self.typing_delay_base,
            'typing_delay_per_char': self.typing_delay_per_char,
            'meta': self.meta,
        }


class BotConfigLoader:
    """
    Bot 配置加载器

    从指定目录加载所有 Bot 配置文件。

    用法:
        loader = BotConfigLoader(project_root)
        configs = loader.load_all()
        
        # 或者加载单个文件
        config = loader.load_file("bots/default.yaml")
    """

    def __init__(self, project_root: Path):
        """
        初始化 Bot 配置加载器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root

    def load_all(self, bots_dir: Optional[str] = None) -> List[BotConfig]:
        """
        加载目录下所有 Bot 配置

        Args:
            bots_dir: Bot 配置目录相对路径 (默认：bots/)

        Returns:
            Bot 配置列表
        """
        if bots_dir is None:
            bots_dir = "bots"

        bots_path = self.project_root / bots_dir
        configs = []

        if not bots_path.exists():
            logger.warning(f"Bot 配置目录不存在：{bots_path}")
            return configs

        if not bots_path.is_dir():
            logger.error(f"Bot 配置路径不是目录：{bots_path}")
            return configs

        # 加载所有 YAML 文件
        yaml_files = sorted(bots_path.glob("*.yaml"))
        for yaml_file in yaml_files:
            try:
                config = self.load_file(yaml_file)
                if config:
                    configs.append(config)
            except Exception as e:
                logger.error(f"加载 Bot 配置失败 {yaml_file}: {e}")

        logger.info(f"从 {bots_path} 加载了 {len(configs)} 个 Bot 配置")
        return configs

    def load_file(self, path: Path) -> Optional[BotConfig]:
        """
        加载单个 Bot 配置文件

        Args:
            path: YAML 文件路径

        Returns:
            Bot 配置对象，加载失败则返回 None
        """
        if not path.exists():
            logger.error(f"Bot 配置文件不存在：{path}")
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Bot 配置文件为空：{path}")
                return None

            return self._build_bot_config(data, path.parent)

        except yaml.YAMLError as e:
            logger.error(f"解析 Bot 配置文件失败 {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载 Bot 配置文件失败 {path}: {e}")
            return None

    def _build_bot_config(self, data: Dict[str, Any], base_dir: Path) -> Optional[BotConfig]:
        """
        从字典构建 BotConfig 对象

        Args:
            data: 配置字典
            base_dir: 基础目录 (用于解析相对路径)

        Returns:
            BotConfig 对象
        """
        # 必填字段验证
        required_fields = ['id', 'name']
        for field in required_fields:
            if field not in data:
                logger.error(f"Bot 配置缺少必填字段：{field}")
                return None

        bot_id = data.get('id')
        name = data.get('name', bot_id)

        # 数值字段验证
        if 'cache_size' in data:
            cache_size = data['cache_size']
            if not isinstance(cache_size, int) or cache_size <= 0:
                logger.error("Bot 配置 cache_size 必须是正整数")
                return None

        if 'typing_delay_base' in data:
            delay = data['typing_delay_base']
            if not isinstance(delay, (int, float)) or delay < 0:
                logger.error("Bot 配置 typing_delay_base 必须是非负数")
                return None

        if 'typing_delay_per_char' in data:
            delay = data['typing_delay_per_char']
            if not isinstance(delay, (int, float)) or delay < 0:
                logger.error("Bot 配置 typing_delay_per_char 必须是非负数")
                return None

        # 解析路径
        script_file = None
        rules_file = None

        if 'script_file' in data:
            script_path = Path(data['script_file'])
            if not script_path.is_absolute():
                script_path = self.project_root / script_path
            script_file = script_path

        if 'rules_file' in data:
            rules_path = Path(data['rules_file'])
            if not rules_path.is_absolute():
                rules_path = self.project_root / rules_path
            rules_file = rules_path

        # 解析开场白配置
        opening = None
        opening_data = data.get('opening')
        opening_script = data.get('opening_script')  # 向后兼容：旧格式
        
        if opening_data and isinstance(opening_data, dict):
            # 新格式：opening: { script, enabled, probability, strategy }
            script_path = None
            if opening_data.get('script'):
                script_path = Path(opening_data['script'])
                if not script_path.is_absolute():
                    script_path = self.project_root / script_path
            
            try:
                opening = OpeningConfig(
                    script=script_path,
                    enabled=opening_data.get('enabled', True),
                    probability=opening_data.get('probability', 1.0),
                    strategy=opening_data.get('strategy', 'random'),
                )
            except ValueError as e:
                logger.error(f"Bot {bot_id} 开场白配置无效：{e}")
        elif opening_script:
            # 旧格式：opening_script: scripts/opening.yaml
            script_path = Path(opening_script)
            if not script_path.is_absolute():
                script_path = self.project_root / script_path
            opening = OpeningConfig(script=script_path, enabled=True, probability=1.0)

        return BotConfig(
            id=bot_id,
            name=name,
            description=data.get('description', ''),
            script_file=script_file,
            rules_file=rules_file,
            opening=opening,
            cache_size=data.get('cache_size', 50),
            typing_delay_base=data.get('typing_delay_base', 1.0),
            typing_delay_per_char=data.get('typing_delay_per_char', 0.05),
            meta=data.get('meta', {}),
        )

    def load_by_id(self, bots_dir: str, template_id: str) -> Optional[BotConfig]:
        """
        根据 ID 加载 Bot 配置

        Args:
            bots_dir: Bot 配置目录
            template_id: 模板 ID

        Returns:
            Bot 配置对象，找不到则返回 None
        """
        configs = self.load_all(bots_dir)
        for config in configs:
            if config.id == template_id:
                return config
        return None


# 便捷函数
def load_bot_configs(project_root: Path, bots_dir: str = "bots") -> List[BotConfig]:
    """
    便捷函数：加载所有 Bot 配置

    Args:
        project_root: 项目根目录
        bots_dir: Bot 配置目录

    Returns:
        Bot 配置列表
    """
    loader = BotConfigLoader(project_root)
    return loader.load_all(bots_dir)


__all__ = [
    "BotConfig",
    "BotConfigLoader",
    "load_bot_configs",
]
