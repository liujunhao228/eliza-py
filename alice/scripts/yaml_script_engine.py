#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本引擎 v2 模块（兼容层）

⚠️ 已废弃：请使用 alice.scripting.YAMLScriptEngine

此模块仅为向后兼容保留，新功能请使用 alice.scripting 包。
"""

import warnings
import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# 发出废弃警告
warnings.warn(
    "alice.scripts.yaml_script_engine 已废弃，请使用 alice.scripting.YAMLScriptEngine",
    DeprecationWarning,
    stacklevel=2,
)

# 导入新引擎
from alice.scripting.yaml.engine import YAMLScriptEngine as NewYAMLScriptEngine
from alice.scripting.yaml.engine import ScriptIntent as NewScriptIntent
from alice.scripting.context import ScriptContext

logger = logging.getLogger(__name__)


@dataclass
class ScriptIntent:
    """
    脚本意图定义（兼容旧接口）
    
    委托给新引擎的 ScriptIntent
    """
    name: str
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None
    templates: List[str] = field(default_factory=list)
    reassembly_rules: List[str] = field(default_factory=list)
    keyword_only: bool = False
    usage_count: int = 0
    last_used: Optional[str] = None

    def to_new_intent(self) -> NewScriptIntent:
        """转换为新引擎的 ScriptIntent"""
        return NewScriptIntent(
            name=self.name,
            priority=self.priority,
            condition=self.condition,
            templates=self.templates,
            reassembly_rules=self.reassembly_rules,
            keyword_only=self.keyword_only,
            usage_count=self.usage_count,
            last_used=self.last_used,
        )


class YAMLScriptEngine:
    """
    YAML 脚本引擎 v2（兼容层）
    
    内部委托给 alice.scripting.yaml.engine.YAMLScriptEngine
    
    ⚠️ 已废弃：请直接使用 alice.scripting.YAMLScriptEngine
    """

    def __init__(self, script_file: Optional[str] = None):
        """
        初始化 YAML 脚本引擎

        Args:
            script_file: YAML 脚本文件路径（字符串路径）
        """
        self.script_file = script_file
        
        # 创建新引擎实例（参数适配：str → Path）
        script_path = Path(script_file) if script_file else None
        self._engine = NewYAMLScriptEngine(default_script_file=script_path)
        
        # 暴露 intents 属性（兼容旧接口）
        # 注意：这里需要将新引擎的 _intents 转换为旧格式
        self.intents: Dict[str, ScriptIntent] = {}
        self._sync_intents()

    def _sync_intents(self) -> None:
        """同步新引擎的意图到旧格式"""
        self.intents.clear()
        for name, new_intent in self._engine._intents.items():
            self.intents[name] = ScriptIntent(
                name=new_intent.name,
                priority=new_intent.priority,
                condition=new_intent.condition,
                templates=new_intent.templates,
                reassembly_rules=new_intent.reassembly_rules,
                keyword_only=new_intent.keyword_only,
                usage_count=new_intent.usage_count,
                last_used=new_intent.last_used,
            )

    def match(self, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[ScriptIntent]:
        """
        匹配脚本（兼容旧接口）

        Args:
            text: 输入文本
            context: 上下文信息

        Returns:
            匹配的脚本意图
        """
        # 将旧格式上下文转换为 ScriptContext
        if context is None:
            context = {}
        
        script_context = ScriptContext(
            text=text,
            tokens=context.get("tokens", []),
            entities=context.get("entities", []),
            pos_tags=context.get("pos_tags", context.get("tokens_with_pos", [])),
            dependencies=context.get("dependencies", []),
            syntax=context.get("syntax", {}),
            triples=context.get("triples", []),
            semantic_roles=context.get("semantic_roles", []),
            semantic_deps=context.get("semantic_deps", []),
            turn_count=context.get("turn_count", 0),
            time_context=context.get("time_context", {}),
            user_profile=context.get("user_profile", {}),
        )
        
        # 使用新引擎匹配
        match_result = self._engine.match(script_context)
        
        if match_result:
            # 返回旧格式的 ScriptIntent
            intent = self._engine._intents.get(match_result.script_id)
            if intent:
                return ScriptIntent(
                    name=intent.name,
                    priority=intent.priority,
                    condition=intent.condition,
                    templates=intent.templates,
                    reassembly_rules=intent.reassembly_rules,
                    keyword_only=intent.keyword_only,
                    usage_count=intent.usage_count,
                    last_used=intent.last_used,
                )
        
        return None

    def generate_response(
        self,
        intent: ScriptIntent,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成响应（兼容旧接口）

        Args:
            intent: 脚本意图
            context: 上下文信息

        Returns:
            生成的响应
        """
        if context is None:
            context = {}
        
        script_context = ScriptContext(
            text=context.get("text", ""),
            tokens=context.get("tokens", []),
            entities=context.get("entities", []),
            pos_tags=context.get("pos_tags", []),
            dependencies=context.get("dependencies", []),
            syntax=context.get("syntax", {}),
            triples=context.get("triples", []),
            semantic_roles=context.get("semantic_roles", []),
            semantic_deps=context.get("semantic_deps", []),
            turn_count=context.get("turn_count", 0),
            time_context=context.get("time_context", {}),
            user_profile=context.get("user_profile", {}),
        )
        
        # 使用新引擎生成响应
        response = self._engine.generate_response(intent.name, script_context)
        
        if response:
            return response.text
        return ""

    def generate_response_with_reassembly(
        self,
        intent: ScriptIntent,
        context: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None,
        reassembly_engine: Optional[Any] = None,
    ) -> str:
        """
        生成响应（支持代词替换，兼容旧接口）

        Args:
            intent: 脚本意图
            context: 上下文信息
            user_input: 用户输入
            reassembly_engine: 重组引擎

        Returns:
            生成的响应
        """
        # 如果是 keyword_only 模板，直接返回
        if intent.keyword_only:
            return self.generate_response(intent, context)
        
        # 如果有重组引擎，临时设置并使用
        if reassembly_engine:
            old_engine = self._engine.reassembly_engine
            self._engine.reassembly_engine = reassembly_engine
            try:
                if context is None:
                    context = {}
                
                script_context = ScriptContext(
                    text=context.get("text", user_input or ""),
                    tokens=context.get("tokens", []),
                    entities=context.get("entities", []),
                    pos_tags=context.get("pos_tags", []),
                    dependencies=context.get("dependencies", []),
                    syntax=context.get("syntax", {}),
                    triples=context.get("triples", []),
                    semantic_roles=context.get("semantic_roles", []),
                    semantic_deps=context.get("semantic_deps", []),
                    turn_count=context.get("turn_count", 0),
                    time_context=context.get("time_context", {}),
                    user_profile=context.get("user_profile", {}),
                )
                
                response = self._engine.generate_response(
                    intent.name, 
                    script_context, 
                    user_input=user_input
                )
                
                if response:
                    return response.text
            finally:
                self._engine.reassembly_engine = old_engine
        
        return self.generate_response(intent, context)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（兼容旧接口）"""
        new_stats = self._engine.get_stats()
        return {
            "total_intents": new_stats.get("total_intents", 0),
            "intents": [
                {
                    "name": i["name"],
                    "priority": i["priority"],
                    "usage_count": i.get("usage_count", 0),
                    "last_used": i.get("last_used"),
                }
                for i in new_stats.get("intents", [])
            ],
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        for intent in self.intents.values():
            intent.usage_count = 0
            intent.last_used = None
        # 同步到新引擎
        for new_intent in self._engine._intents.values():
            new_intent.usage_count = 0
            new_intent.last_used = None


# 模块级别的便捷函数
def create_engine(script_file: Optional[str] = None) -> YAMLScriptEngine:
    """
    创建 YAML 脚本引擎（便捷函数）
    
    ⚠️ 已废弃：请直接使用 YAMLScriptEngine()
    """
    return YAMLScriptEngine(script_file)
