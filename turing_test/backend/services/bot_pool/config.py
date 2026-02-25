"""
Bot 模板配置模块

负责 Bot 模板配置的管理和解析。
"""

from pathlib import Path
from typing import Dict, Optional

from config import BotTemplate


class BotTemplateConfig:
    """Bot 模板配置管理器"""

    def __init__(self):
        self.templates: Dict[str, BotTemplate] = {}
        self.default_template: str = "default"

    def register(
        self,
        template_id: str,
        name: str,
        script_file: Optional[Path] = None,
        rules_file: Optional[Path] = None,
        enable_plugins: bool = True,
        cache_size: int = 100,
    ):
        """注册一个 Bot 模板"""
        self.templates[template_id] = BotTemplate(
            id=template_id,
            name=name,
            script_file=script_file,
            rules_file=rules_file,
            enable_plugins=enable_plugins,
            cache_size=cache_size,
        )

    def get(self, template_id: str) -> Optional[BotTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)

    def set_default(self, template_id: str):
        """设置默认模板"""
        if template_id not in self.templates:
            raise ValueError(f"模板不存在：{template_id}")
        self.default_template = template_id

    def get_default(self) -> BotTemplate:
        """获取默认模板"""
        template = self.templates.get(self.default_template)
        if not template:
            # 返回第一个可用的模板
            for t in self.templates.values():
                return t
            raise ValueError("没有可用的 Bot 模板")
        return template

    def list_templates(self) -> Dict[str, BotTemplate]:
        """列出所有模板"""
        return self.templates.copy()


def create_default_templates(
    script_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    enable_plugins: bool = True,
) -> Dict[str, BotTemplate]:
    """
    创建默认 Bot 模板

    Args:
        script_file: 脚本文件路径
        rules_file: 规则文件路径
        enable_plugins: 是否启用插件

    Returns:
        Bot 模板字典
    """
    templates = {
        "default": BotTemplate(
            id="default",
            name="Default",
            script_file=Path(script_file) if script_file else None,
            rules_file=Path(rules_file) if rules_file else None,
            enable_plugins=enable_plugins,
        )
    }
    return templates
