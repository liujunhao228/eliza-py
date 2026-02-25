#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好奇心插件模块 - 重构版

实现 Alice 的核心功能：好奇的朋友角色。
基于 YAML 脚本引擎驱动，移除硬编码逻辑。
"""

import logging
import random
from typing import Any, Dict, List, Optional

from alice.plugins.base_plugin import BasePlugin, PluginResult
from alice.scripting import YAMLScriptEngine, ScriptIntent
from alice.nlp.syntax_reassembly import SyntaxReassembly

logger = logging.getLogger(__name__)


class CuriosityPlugin(BasePlugin):
    """
    好奇心插件 - 重构版

    实现 Alice 的核心对话策略：
    - 叙事助推：维持对话流
    - 实体深度挖掘：对人、事、物表现好奇
    - 认知探索：引导思考观点
    - Meta 对话：处理关于 Alice 的提问

    设计原则:
    - YAML 脚本驱动：所有对话逻辑来自 YAML 配置文件
    - 无硬编码：移除所有硬编码的对话规则
    - 优先级调度：基于脚本优先级选择响应
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化好奇心插件

        Args:
            config: 配置字典，可包含：
                - script_file: 脚本文件路径
                - rules_file: 反射规则文件路径
                - priority: 插件优先级
        """
        default_config = {
            "script_file": None,
            "rules_file": None,
            "priority": 50,
        }
        config = config or default_config

        super().__init__(config)
        self.priority = self.config.get("priority", 50)

        # 脚本引擎和重组引擎（由对话引擎统一管理）
        self.script_engine: Optional[YAMLScriptEngine] = None
        self.reassembly_engine: Optional[SyntaxReassembly] = None

        # 使用统计
        self.script_history: Dict[str, int] = {}
        self.last_used_responses: Dict[str, str] = {}

    def initialize(self) -> bool:
        """
        初始化插件

        注意：脚本引擎和重组引擎由对话引擎统一初始化并注入
        插件只负责使用这些引擎

        Returns:
            是否初始化成功
        """
        try:
            # 如果配置中指定了文件路径，创建独立的引擎实例
            script_file = self.config.get("script_file")
            rules_file = self.config.get("rules_file")

            if script_file and not self.script_engine:
                self.script_engine = YAMLScriptEngine(script_file=script_file)

            if rules_file and not self.reassembly_engine:
                self.reassembly_engine = SyntaxReassembly(rules_file=rules_file)

            logger.info("好奇心插件初始化成功")
            return True

        except Exception as e:
            logger.error(f"好奇心插件初始化失败：{e}")
            return False

    def set_script_engine(self, script_engine: YAMLScriptEngine) -> None:
        """
        设置脚本引擎（由对话引擎注入）

        Args:
            script_engine: YAML 脚本引擎实例
        """
        self.script_engine = script_engine
        logger.debug(f"好奇心插件已绑定脚本引擎，支持 {len(script_engine.intents)} 个意图")

    def set_reassembly_engine(self, reassembly_engine: SyntaxReassembly) -> None:
        """
        设置重组引擎（由对话引擎注入）

        Args:
            reassembly_engine: 句法重组引擎实例
        """
        self.reassembly_engine = reassembly_engine
        logger.debug("好奇心插件已绑定重组引擎")

    def process_input(self, text: str, context: Dict[str, Any]) -> PluginResult:
        """
        处理用户输入并生成响应

        Args:
            text: 用户输入文本
            context: 对话上下文（包含 semantic_info, intent_match 等）

        Returns:
            插件处理结果
        """
        # 优先使用注入的脚本引擎
        script_engine = self.script_engine
        if not script_engine:
            return PluginResult(
                success=False,
                response=None,
                metadata={"reason": "script_engine_not_available"},
            )

        try:
            # 从上下文中获取语义信息
            semantic_info = context.get("semantic_info", {})
            intent_match = context.get("intent_match", None)

            # 如果已有意图匹配结果，直接使用
            if intent_match and hasattr(intent_match, 'intent'):
                intent_name = intent_match.intent
                script_intent = script_engine.intents.get(intent_name)
                if script_intent:
                    # 生成响应
                    response = self._generate_response(
                        intent=script_intent,
                        text=text,
                        context=semantic_info,
                    )

                    if response:
                        # 更新历史记录
                        self.script_history[intent_name] = self.script_history.get(intent_name, 0) + 1
                        self.last_used_responses[intent_name] = response

                        return PluginResult(
                            success=True,
                            response=response,
                            metadata={
                                "intent": intent_name,
                                "priority": script_intent.priority,
                                "keyword_only": script_intent.keyword_only,
                                "script_id": intent_name,
                            },
                        )

            # 无意图匹配结果，重新匹配
            intent = script_engine.match(text, semantic_info)
            if not intent:
                return PluginResult(
                    success=False,
                    response=None,
                    metadata={"reason": "no_intent_matched"},
                )

            # 生成响应
            response = self._generate_response(
                intent=intent,
                text=text,
                context=semantic_info,
            )

            if response:
                # 更新历史记录
                self.script_history[intent.name] = self.script_history.get(intent.name, 0) + 1
                self.last_used_responses[intent.name] = response

                return PluginResult(
                    success=True,
                    response=response,
                    metadata={
                        "intent": intent.name,
                        "priority": intent.priority,
                        "keyword_only": intent.keyword_only,
                        "script_id": intent.name,
                    },
                )
            else:
                return PluginResult(
                    success=False,
                    response=None,
                    metadata={"reason": "response_generation_failed"},
                )

        except Exception as e:
            logger.error(f"好奇心插件处理失败：{e}", exc_info=True)
            return PluginResult(
                success=False,
                response=None,
                metadata={"error": str(e)},
            )

    def _generate_response(
        self,
        intent: ScriptIntent,
        text: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        生成响应

        Args:
            intent: 脚本意图
            text: 用户输入
            context: 上下文信息

        Returns:
            生成的响应
        """
        if not intent.templates:
            return None

        # 如果是 keyword_only 模板，填充占位符后返回（不进行代词替换）
        if intent.keyword_only:
            return self._fill_placeholders(intent, context)

        # 非 keyword_only 模板，使用重组引擎进行代词替换
        if self.reassembly_engine:
            response = self._generate_with_reassembly(intent, text, context)
            if response:
                return response

        # 无重组引擎或重组失败，直接返回模板
        return self._fill_placeholders(intent, context)

    def _generate_with_reassembly(
        self,
        intent: ScriptIntent,
        text: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        使用重组引擎生成响应（进行代词替换）

        Args:
            intent: 脚本意图
            text: 用户输入
            context: 上下文信息

        Returns:
            重组后的响应
        """
        if not self.reassembly_engine:
            return None

        # 选择模板
        template = self._select_template(intent)
        if not template:
            return None

        # 填充实体占位符
        template = self._fill_placeholders_from_template(template, context)

        # 使用重组引擎应用代词映射
        response = self.reassembly_engine.reassemble(
            components=[text],
            reassembly_rule=template,
            apply_pronoun_mapping=True,
        )

        return response.strip() if response else None

    def _select_template(self, intent: ScriptIntent) -> Optional[str]:
        """
        选择模板（避免重复）

        Args:
            intent: 脚本意图

        Returns:
            选中的模板
        """
        if not intent.templates:
            return None

        templates = intent.templates
        if len(templates) == 1:
            return templates[0]

        # 避免重复使用同一个模板
        last_response = self.last_used_responses.get(intent.name, "")
        available = [t for t in templates if t != last_response]

        if available:
            return random.choice(available)
        return random.choice(templates)

    def _fill_placeholders_from_template(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        填充模板中的实体占位符和上下文变量

        Args:
            template: 模板字符串
            context: 上下文信息

        Returns:
            填充后的模板
        """
        import re

        entities = context.get("entities", [])

        # 构建实体映射
        entity_map = {}
        for entity_type, entity_text in entities:
            entity_map[entity_type.lower()] = entity_text

        # 替换占位符
        def replace_placeholder(match):
            placeholder = match.group(1).lower()
            
            # 优先检查实体
            if placeholder in entity_map:
                return entity_map[placeholder]
            
            # 检查上下文变量
            if placeholder in context:
                value = context[placeholder]
                if isinstance(value, (list, dict)):
                    return str(value)
                return str(value) if value is not None else ""
            
            # 未匹配，返回原占位符（后续会被清理）
            return match.group(0)

        result = re.sub(r'\{([^}]+)\}', replace_placeholder, template)

        # 清理未匹配的占位符（替换为空）
        result = re.sub(r'\{[^}]+\}', '', result)

        return result

    def _fill_placeholders(
        self,
        intent: ScriptIntent,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        填充模板中的实体占位符

        Args:
            intent: 脚本意图
            context: 上下文信息

        Returns:
            填充后的响应
        """
        template = self._select_template(intent)
        if not template:
            return None

        return self._fill_placeholders_from_template(template, context)

    def get_stats(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        return {
            "name": self.name,
            "script_history": self.script_history,
            "last_used_responses": self.last_used_responses,
        }

    def reset(self) -> None:
        """重置插件状态"""
        self.script_history.clear()
        self.last_used_responses.clear()

    def cleanup(self) -> None:
        """清理插件资源"""
        self.reset()
