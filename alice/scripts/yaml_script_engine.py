#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本引擎 v2 模块

支持 YAML 格式的脚本配置，提供更灵活的脚本定义和优先级调度。

脚本模块:
- 叙事助推 (Narrative Continuity)
- 实体深度挖掘 (Entity Deep-Dive)
- 情感镜像与验证 (Emotional Mirroring)
- 认知探索 (Cognitive Probing)
- Meta 对话 (Meta-Conversation)
"""

import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from alice.exceptions import (
    InvalidConfigurationError,
    MissingConfigurationError,
    ConfigurationError,
)

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PyYAML 未安装，YAML 脚本引擎将不可用")

logger = logging.getLogger(__name__)


@dataclass
class ScriptIntent:
    """脚本意图定义"""
    name: str
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None
    templates: List[str] = field(default_factory=list)
    reassembly_rules: List[str] = field(default_factory=list)
    
    # 新增：仅关键词匹配标志，设为 True 时不进行代词替换
    keyword_only: bool = False

    # 统计信息
    usage_count: int = 0
    last_used: Optional[str] = None


class YAMLScriptEngine:
    """
    YAML 脚本引擎 v2
    
    功能:
    - 加载 YAML 格式脚本
    - 基于优先级的意图匹配
    - 条件触发机制
    - 响应模板管理
    - 使用统计追踪
    
    优先级调度:
    - P0 (90-100): 情感危机或极端情绪
    - P1 (70-89): 实体挖掘
    - P2 (40-69): 叙事助推
    - P3 (0-39): 万能回复
    """

    def __init__(self, script_file: Optional[str] = None):
        """
        初始化 YAML 脚本引擎

        Args:
            script_file: YAML 脚本文件路径
        """
        self.script_file = script_file
        self.intents: Dict[str, ScriptIntent] = {}
        self._load_scripts()

    def _load_scripts(self) -> None:
        """从 YAML 文件加载脚本"""
        if not YAML_AVAILABLE:
            raise DependencyError("PyYAML 未安装，无法使用 YAML 脚本引擎")

        if not self.script_file:
            raise MissingConfigurationError("未指定 YAML 脚本文件路径")

        script_path = Path(self.script_file)
        if not script_path.exists():
            raise MissingConfigurationError(f"脚本文件不存在：{script_path}")

        try:
            with open(script_path, "r", encoding="utf-8") as f:
                scripts_data = yaml.safe_load(f)

            if not scripts_data:
                raise InvalidConfigurationError(f"脚本文件为空：{script_path}")

            self._parse_scripts(scripts_data, script_path)
            logger.info(f"成功加载 {len(self.intents)} 个脚本意图")

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 [{script_path}]: {e}", exc_info=True)
            raise InvalidConfigurationError(f"YAML 脚本格式错误：{script_path}") from e
        except IOError as e:
            logger.error(f"无法读取脚本文件 [{script_path}]: {e}", exc_info=True)
            raise ConfigurationError(f"无法读取 YAML 脚本文件：{script_path}") from e

    def _parse_scripts(self, scripts_data: Any, script_path: Path) -> None:
        """
        解析脚本数据

        Args:
            scripts_data: 脚本数据列表
            script_path: 脚本文件路径（用于错误报告）

        Raises:
            InvalidConfigurationError: 当脚本格式无效时
        """
        if not isinstance(scripts_data, list):
            raise InvalidConfigurationError(
                f"脚本格式错误：期望列表格式，实际为 {type(scripts_data).__name__} [{script_path}]"
            )

        for idx, script_data in enumerate(scripts_data):
            if not isinstance(script_data, dict):
                raise InvalidConfigurationError(
                    f"脚本格式错误：索引 {idx} 处的条目应为字典 [{script_path}]"
                )

            # 验证必需字段
            if "intent" not in script_data:
                raise InvalidConfigurationError(
                    f"脚本缺少必需字段 'intent' (索引：{idx}) [{script_path}]"
                )

            if "templates" not in script_data:
                raise InvalidConfigurationError(
                    f"脚本缺少必需字段 'templates' (意图：{script_data.get('intent', 'unknown')}) [{script_path}]"
                )

            templates = script_data.get("templates", [])
            if not isinstance(templates, list) or len(templates) == 0:
                raise InvalidConfigurationError(
                    f"脚本 'templates' 必须是非空列表 (意图：{script_data.get('intent', 'unknown')}) [{script_path}]"
                )

            intent_name = script_data.get("intent", f"intent_{len(self.intents)}")

            intent = ScriptIntent(
                name=intent_name,
                priority=script_data.get("priority", 50),
                condition=script_data.get("condition"),
                templates=script_data.get("templates", []),
                reassembly_rules=script_data.get("reassembly_rules", []),
                keyword_only=script_data.get("keyword_only", False),
            )

            self.intents[intent_name] = intent

    def match(self, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[ScriptIntent]:
        """
        匹配脚本

        Args:
            text: 输入文本
            context: 上下文信息（包含 entities, sentiment 等）

        Returns:
            匹配的脚本意图
        """
        context = context or {}
        
        # 按优先级排序（从高到低）
        sorted_intents = sorted(
            self.intents.values(),
            key=lambda i: i.priority,
            reverse=True,
        )
        
        for intent in sorted_intents:
            if self._check_condition(intent, text, context):
                intent.usage_count += 1
                from datetime import datetime
                intent.last_used = datetime.now().isoformat()
                return intent
        
        return None

    def _check_condition(
        self,
        intent: ScriptIntent,
        text: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        检查条件是否满足
        
        Args:
            intent: 脚本意图
            text: 输入文本
            context: 上下文信息
            
        Returns:
            条件是否满足
        """
        condition = intent.condition
        
        if condition is None:
            return True  # 无条件，总是匹配
        
        # 检查实体条件
        if "entities" in condition:
            required_entities = condition["entities"]
            context_entities = context.get("entities", [])
            
            if not any(e[0] in required_entities for e in context_entities):
                return False
        
        # 检查情感条件
        if "sentiment" in condition:
            required_sentiment = condition["sentiment"]
            sentiment_score = context.get("sentiment", 0.0)
            
            if required_sentiment == "negative" and sentiment_score >= -0.2:
                return False
            elif required_sentiment == "positive" and sentiment_score <= 0.2:
                return False
        
        # 检查关键词条件
        if "keywords" in condition:
            keywords = condition["keywords"]
            if not any(kw in text for kw in keywords):
                return False
        
        # 检查 POS 标签条件（简化实现）
        if "pos_tags" in condition:
            # 需要实际的 POS  tagging，这里简化处理
            pass
        
        return True

    def generate_response(
        self,
        intent: ScriptIntent,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成响应

        Args:
            intent: 脚本意图
            context: 上下文信息

        Returns:
            生成的响应
        """
        if not intent.templates:
            return ""

        # 选择一个模板（避免重复）
        template = self._select_template(intent)

        # 填充实体占位符
        if context:
            template = self._fill_placeholders(template, context)

        return template

    def generate_response_with_reassembly(
        self,
        intent: ScriptIntent,
        context: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None,
        reassembly_engine: Optional[Any] = None,
    ) -> str:
        """
        生成响应（支持代词替换）

        Args:
            intent: 脚本意图
            context: 上下文信息
            user_input: 用户输入
            reassembly_engine: 句法重组引擎

        Returns:
            生成的响应
        """
        if not intent.templates:
            return ""

        # 选择一个模板（避免重复）
        template = self._select_template(intent)

        # 如果是 keyword_only 模板，仅填充实体占位符，不进行代词替换
        if intent.keyword_only:
            if context:
                template = self._fill_placeholders(template, context)
            return template

        # 非 keyword_only 模板，使用重组引擎进行代词替换
        if reassembly_engine and user_input:
            template = self._fill_placeholders(template, context or {})
            # 使用重组引擎应用代词映射
            response = reassembly_engine.reassemble(
                components=[user_input],
                reassembly_rule=template,
                apply_pronoun_mapping=True,
            )
            return response

        # 无重组引擎时，仅填充实体占位符
        if context:
            template = self._fill_placeholders(template, context)
        return template

    def _select_template(self, intent: ScriptIntent) -> str:
        """
        选择模板（避免重复）
        
        Args:
            intent: 脚本意图
            
        Returns:
            选中的模板
        """
        templates = intent.templates
        
        if len(templates) == 1:
            return templates[0]
        
        # 简单随机选择
        return random.choice(templates)

    def _fill_placeholders(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        填充占位符
        
        Args:
            template: 模板字符串
            context: 上下文信息
            
        Returns:
            填充后的字符串
        """
        # 填充实体占位符
        entities = context.get("entities", [])
        
        for entity_type, entity_text in entities:
            placeholder = f"{{{entity_type}}}"
            if placeholder in template:
                template = template.replace(placeholder, entity_text)
        
        # 清理未匹配的占位符
        template = re.sub(r"\{[^}]+\}", "", template)
        
        return template

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_intents": len(self.intents),
            "intents": [
                {
                    "name": i.name,
                    "priority": i.priority,
                    "usage_count": i.usage_count,
                    "last_used": i.last_used,
                }
                for i in self.intents.values()
            ],
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        for intent in self.intents.values():
            intent.usage_count = 0
            intent.last_used = None
