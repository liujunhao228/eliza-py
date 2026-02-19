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

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML 未安装，YAML 脚本引擎将不可用")

logger = logging.getLogger(__name__)


@dataclass
class ScriptIntent:
    """脚本意图定义"""
    name: str
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None
    templates: List[str] = field(default_factory=list)
    reassembly_rules: List[str] = field(default_factory=list)
    
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
            logger.warning("PyYAML 未安装，无法加载脚本")
            return
        
        if not self.script_file:
            logger.warning("未指定脚本文件路径")
            return
        
        script_path = Path(self.script_file)
        if not script_path.exists():
            logger.warning(f"脚本文件不存在：{script_path}")
            # 尝试创建默认脚本
            self._create_default_scripts()
            return
        
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                scripts_data = yaml.safe_load(f)
                
            if not scripts_data:
                logger.warning("脚本文件为空")
                return
            
            self._parse_scripts(scripts_data)
            logger.info(f"成功加载 {len(self.intents)} 个脚本意图")
            
        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误：{e}")
            self._create_default_scripts()
        except IOError as e:
            logger.error(f"无法读取脚本文件：{e}")
            self._create_default_scripts()

    def _parse_scripts(self, scripts_data: List[Dict[str, Any]]) -> None:
        """
        解析脚本数据
        
        Args:
            scripts_data: 脚本数据列表
        """
        for script_data in scripts_data:
            intent_name = script_data.get("intent", f"intent_{len(self.intents)}")
            
            intent = ScriptIntent(
                name=intent_name,
                priority=script_data.get("priority", 50),
                condition=script_data.get("condition"),
                templates=script_data.get("templates", []),
                reassembly_rules=script_data.get("reassembly_rules", []),
            )
            
            self.intents[intent_name] = intent

    def _create_default_scripts(self) -> None:
        """创建默认脚本（用于回退）"""
        default_scripts = [
            {
                "intent": "narrative_continuation",
                "priority": 50,
                "condition": {"pos_tags": ["VERB"]},
                "templates": [
                    "后来呢？",
                    "那之后发生了什么让你意想不到的事吗？",
                    "然后呢？",
                ],
            },
            {
                "intent": "person_interest",
                "priority": 70,
                "condition": {"entities": ["PERSON"]},
                "templates": [
                    "你提到的这个{PERSON}，ta 平时是个怎样的人呀？",
                    "听起来你对{PERSON}挺关注的，能多跟我说说 ta 吗？",
                    "诶，{PERSON}在你的故事里扮演了什么样的角色呢？",
                ],
            },
            {
                "intent": "emotion_mirror",
                "priority": 90,
                "condition": {"sentiment": "negative"},
                "templates": [
                    "听起来那阵子你挺不容易的，那种感觉现在还在吗？",
                    "我能理解你的感受，能多说说吗？",
                ],
            },
            {
                "intent": "cognitive_probe",
                "priority": 60,
                "condition": {"keywords": ["觉得", "认为", "我想"]},
                "templates": [
                    "你为什么会产生这样的想法呢？",
                    "如果换一个角度看这件事，你觉得会发生什么？",
                ],
            },
            {
                "intent": "meta_conversation",
                "priority": 80,
                "condition": {"keywords": ["你是谁", "你觉得呢"]},
                "templates": [
                    "我只是一个对你的故事充满好奇的朋友呀。",
                    "我的看法并不重要，重要的是这件事对你的意义，不是吗？",
                ],
            },
            {
                "intent": "fallback",
                "priority": 10,
                "condition": None,
                "templates": [
                    "原来是这样啊。",
                    "唔，我在听。",
                    "能再多说一些吗？",
                ],
            },
        ]
        
        for script_data in default_scripts:
            intent = ScriptIntent(
                name=script_data["intent"],
                priority=script_data.get("priority", 50),
                condition=script_data.get("condition"),
                templates=script_data.get("templates", []),
            )
            self.intents[script_data["intent"]] = intent

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
