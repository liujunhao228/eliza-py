#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本解析器模块

负责解析 YAML 脚本文件并提取意图定义。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from alice.scripting.base import ScriptConfig

logger = logging.getLogger(__name__)


@dataclass
class ScriptIntent:
    """
    脚本意图定义

    Attributes:
        name: 意图名称
        priority: 优先级 (0-100)
        condition: 匹配条件
        templates: 响应模板列表
        reassembly_rules: 重组规则
        keyword_only: 是否仅关键词匹配
        end_action: 结束对话动作 ("none" | "direct" | "farewell")
        end_reason: 结束原因 (使用 EndReason 枚举值，如 "bot_max_turns", "user_gave_up" 等)
        usage_count: 使用次数统计
        last_used: 最后使用时间
    """
    name: str
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None
    templates: List[str] = field(default_factory=list)
    reassembly_rules: List[str] = field(default_factory=list)
    keyword_only: bool = False
    end_action: str = "none"  # "none" | "direct" | "farewell"
    end_reason: str = ""  # 使用 EndReason 枚举值
    usage_count: int = 0
    last_used: Optional[str] = None


class YAMLScriptParser:
    """
    YAML 脚本解析器

    负责：
    - 解析 YAML 文件内容
    - 提取意图定义
    - 验证意图数据结构
    """

    def __init__(self):
        """初始化解析器"""
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML 未安装，请运行：pip install pyyaml")

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        解析 YAML 文件

        Args:
            file_path: YAML 文件路径

        Returns:
            解析后的脚本数据列表

        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML 格式错误
        """
        if not file_path.exists():
            raise FileNotFoundError(f"YAML 脚本文件不存在：{file_path}")

        content = file_path.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        if not data:
            logger.warning(f"YAML 脚本内容为空：{file_path}")
            return []

        if not isinstance(data, list):
            logger.error(f"YAML 脚本格式错误：期望列表格式：{file_path}")
            return []

        return data

    def parse_intents(
        self,
        scripts_data: List[Dict[str, Any]],
        config: ScriptConfig,
    ) -> Dict[str, ScriptIntent]:
        """
        解析意图数据

        Args:
            scripts_data: 脚本数据列表
            config: 脚本配置

        Returns:
            意图字典

        意图数据格式:
            - intent: 意图名称
              priority: 优先级 (可选)
              condition: 匹配条件 (可选)
              templates: 响应模板列表
              reassembly_rules: 重组规则 (可选)
              keyword_only: 是否仅关键词匹配 (可选)
        """
        intents = {}

        for idx, script_data in enumerate(scripts_data):
            if not isinstance(script_data, dict):
                logger.warning(f"跳过无效的意图数据 (索引：{idx})")
                continue

            if "intent" not in script_data:
                logger.warning(f"意图缺少 'intent' 字段 (索引：{idx})")
                continue

            if "templates" not in script_data:
                logger.warning(f"意图缺少 'templates' 字段：{script_data.get('intent')}")
                continue

            templates = script_data.get("templates", [])
            if not isinstance(templates, list) or not templates:
                logger.warning(f"意图 'templates' 必须是非空列表：{script_data.get('intent')}")
                continue

            # 生成意图名称（使用脚本 ID 前缀避免冲突）
            intent_name = f"{config.script_id}_{script_data['intent']}"

            intent = ScriptIntent(
                name=intent_name,
                priority=script_data.get("priority", config.priority),
                condition=script_data.get("condition"),
                templates=templates,
                reassembly_rules=script_data.get("reassembly_rules", []),
                keyword_only=script_data.get("keyword_only", False),
                end_action=script_data.get("end_action", "none"),
                end_reason=script_data.get("end_reason", ""),
            )

            intents[intent_name] = intent

        return intents

    def validate_intent_data(self, script_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证意图数据

        Args:
            script_data: 意图数据

        Returns:
            (是否有效，错误信息)
        """
        if "intent" not in script_data:
            return False, "缺少 'intent' 字段"

        if "templates" not in script_data:
            return False, "缺少 'templates' 字段"

        templates = script_data.get("templates", [])
        if not isinstance(templates, list) or not templates:
            return False, "'templates' 必须是非空列表"

        return True, ""
