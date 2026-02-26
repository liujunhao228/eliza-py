#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 模板注册中心
================

管理 AI Bot 配置模板的注册、查找和使用。

用法:
    registry = BotTemplateRegistry()
    registry.register(BotTemplate(id="default", name="默认 Bot", ...))
    template = registry.get("default")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from config.types import OpeningConfig


@dataclass
class BotTemplate:
    """
    Bot 配置模板

    定义一个 Bot 实例的完整配置。
    """
    id: str
    """模板唯一标识符"""

    name: str
    """Bot 显示名称"""

    description: str = ""
    """模板描述"""

    script_file: Optional[Path] = None
    """脚本文件路径"""

    rules_file: Optional[Path] = None
    """规则文件路径"""

    opening: Optional[OpeningConfig] = None
    """开场白配置（新格式）"""

    opening_script: Optional[Path] = None
    """开场白脚本文件路径（旧格式，向后兼容）"""

    cache_size: int = 50
    """缓存大小"""

    typing_delay_base: float = 1.0
    """基础打字延迟 (秒)"""

    typing_delay_per_char: float = 0.05
    """每字符额外延迟 (秒)"""

    meta: Dict[str, Any] = field(default_factory=dict)
    """额外元数据"""

    def __post_init__(self):
        """初始化后处理"""
        if self.meta is None:
            self.meta = {}

    def __str__(self) -> str:
        return f"BotTemplate(id={self.id}, name={self.name})"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
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
        if self.opening:
            result['opening'] = {
                'script': str(self.opening.script) if self.opening.script else None,
                'enabled': self.opening.enabled,
                'probability': self.opening.probability,
                'strategy': self.opening.strategy,
            }
        return result


class BotTemplateRegistry:
    """
    Bot 模板注册中心

    管理 Bot 配置模板的注册、查找和使用。

    特性:
    - 模板注册/注销
    - 默认模板设置
    - 从配置批量加载
    - 模板查询

    用法:
        registry = BotTemplateRegistry()

        # 注册模板
        registry.register(BotTemplate(
            id="default",
            name="默认 Bot",
            script_file=Path("alice/scripts/demo.yaml"),
            rules_file=Path("alice/scripts/rules/mapping.yaml"),
        ))

        # 获取模板
        template = registry.get("default")
        template = registry.get_or_default()  # 获取默认模板

        # 从配置加载
        registry.load_from_config(config['turing']['ai_bot_templates'], project_root)
    """

    def __init__(self):
        self._templates: Dict[str, BotTemplate] = {}
        self._default_template_id: Optional[str] = None

    def register(self, template: BotTemplate) -> bool:
        """
        注册一个 Bot 模板

        Args:
            template: Bot 模板

        Returns:
            是否注册成功
        """
        if not template.id:
            logger.error("注册 Bot 模板失败：模板 ID 不能为空")
            return False

        if template.id in self._templates:
            logger.warning(f"Bot 模板已存在，将被覆盖：{template.id}")

        self._templates[template.id] = template
        logger.debug(f"Bot 模板已注册：{template.id}")
        return True

    def unregister(self, template_id: str) -> bool:
        """
        注销一个 Bot 模板

        Args:
            template_id: 模板 ID

        Returns:
            是否注销成功
        """
        if template_id in self._templates:
            del self._templates[template_id]
            logger.debug(f"Bot 模板已注销：{template_id}")

            # 如果注销的是默认模板，清除默认设置
            if self._default_template_id == template_id:
                self._default_template_id = None

            return True

        logger.warning(f"注销 Bot 模板失败，模板不存在：{template_id}")
        return False

    def get(self, template_id: str) -> Optional[BotTemplate]:
        """
        获取 Bot 模板

        Args:
            template_id: 模板 ID

        Returns:
            Bot 模板，不存在则返回 None
        """
        return self._templates.get(template_id)

    def get_or_default(self, template_id: Optional[str] = None) -> Optional[BotTemplate]:
        """
        获取指定模板，如果未指定则返回默认模板

        Args:
            template_id: 模板 ID (可选)

        Returns:
            Bot 模板，如果都找不到则返回 None
        """
        # 如果指定了 template_id，优先返回
        if template_id is not None:
            template = self._templates.get(template_id)
            if template:
                return template
            logger.warning(f"Bot 模板不存在：{template_id}，尝试使用默认模板")

        # 使用默认模板
        if self._default_template_id is not None:
            template = self._templates.get(self._default_template_id)
            if template:
                return template

        # 返回第一个可用的模板
        if self._templates:
            template = next(iter(self._templates.values()))
            logger.debug(f"使用第一个可用模板：{template.id}")
            return template

        return None

    def set_default(self, template_id: str) -> bool:
        """
        设置默认模板

        Args:
            template_id: 模板 ID

        Returns:
            是否设置成功
        """
        if template_id in self._templates:
            self._default_template_id = template_id
            logger.info(f"默认 Bot 模板已设置：{template_id}")
            return True

        logger.error(f"设置默认模板失败，模板不存在：{template_id}")
        return False

    def list_templates(self) -> List[str]:
        """
        列出所有模板 ID

        Returns:
            模板 ID 列表
        """
        return list(self._templates.keys())

    def count(self) -> int:
        """
        获取模板数量

        Returns:
            模板数量
        """
        return len(self._templates)

    def load_from_config(
        self,
        templates_config: List[Dict[str, Any]],
        project_root: Optional[Path] = None
    ) -> int:
        """
        从配置加载模板

        Args:
            templates_config: 配置列表
            project_root: 项目根目录 (用于解析相对路径)

        Returns:
            成功加载的模板数量
        """
        count = 0
        for cfg in templates_config:
            template_id = cfg.get('id', '')
            if not template_id:
                logger.warning(f"跳过无效配置 (缺少 id): {cfg}")
                continue

            # 解析路径
            script_file = None
            rules_file = None

            if 'script_file' in cfg:
                script_path = Path(cfg['script_file'])
                if project_root and not script_path.is_absolute():
                    script_path = project_root / script_path
                script_file = script_path

            if 'rules_file' in cfg:
                rules_path = Path(cfg['rules_file'])
                if project_root and not rules_path.is_absolute():
                    rules_path = project_root / rules_path
                rules_file = rules_path

            template = BotTemplate(
                id=template_id,
                name=cfg.get('name', template_id),
                description=cfg.get('description', ''),
                script_file=script_file,
                rules_file=rules_file,
                cache_size=cfg.get('cache_size', 50),
                typing_delay_base=cfg.get('typing_delay_base', 1.0),
                typing_delay_per_char=cfg.get('typing_delay_per_char', 0.05),
                meta=cfg.get('meta', {}),
            )

            self.register(template)
            count += 1

        logger.info(f"从配置加载了 {count} 个 Bot 模板")
        return count

    def clear(self):
        """清空所有模板"""
        self._templates.clear()
        self._default_template_id = None
        logger.debug("Bot 模板注册中心已清空")

    @property
    def default_template_id(self) -> Optional[str]:
        """获取默认模板 ID"""
        return self._default_template_id

    @property
    def templates(self) -> Dict[str, BotTemplate]:
        """获取所有模板 (只读)"""
        return self._templates.copy()


# 全局单例
_registry: Optional[BotTemplateRegistry] = None


def get_bot_registry() -> BotTemplateRegistry:
    """
    获取全局 Bot 模板注册中心实例

    Returns:
        BotTemplateRegistry 实例
    """
    global _registry
    if _registry is None:
        _registry = BotTemplateRegistry()
    return _registry


def reset_bot_registry():
    """重置 Bot 模板注册中心 (用于测试)"""
    global _registry
    _registry = None


__all__ = [
    "BotTemplate",
    "BotTemplateRegistry",
    "get_bot_registry",
    "reset_bot_registry",
]
