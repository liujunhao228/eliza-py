#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应生成器模块 - 重构版

基于 YAML 脚本引擎和重组规则生成响应。
移除硬编码的响应池，所有响应由规则文件驱动。

情感分析增强：
- 支持基于情感标签的响应选择
- 提供情感驱动的共情回应
- 支持细粒度情感（喜、怒、哀、惧等）的特定响应
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    响应生成器 - 重构版

    功能:
    - 基于 YAML 脚本引擎的响应生成
    - 基于重组规则的响应生成
    - 回退响应处理
    - 响应多样性控制
    - 情感驱动的共情回应

    设计原则:
    - 规则文件驱动：所有响应模板来自 YAML 文件
    - 无硬编码：移除所有硬编码的响应池
    - 优先级调度：基于脚本优先级选择响应
    """

    def __init__(
        self,
        script_engine: Optional[Any] = None,
        reassembly_engine: Optional[Any] = None,
        fallback_file: Optional[str] = None,
    ):
        """
        初始化响应生成器

        Args:
            script_engine: YAML 脚本引擎实例
            reassembly_engine: 句法重组引擎实例
            fallback_file: 回退响应文件路径（可选）
        """
        self.script_engine = script_engine
        self.reassembly_engine = reassembly_engine

        # 回退响应（仅保留最基础的，其他全部来自 YAML）
        self.fallback_responses = self._load_fallback_responses(fallback_file)

    def _load_fallback_responses(self, fallback_file: Optional[str]) -> List[str]:
        """
        加载回退响应

        Args:
            fallback_file: 回退响应文件路径

        Returns:
            回退响应列表
        """
        if not fallback_file:
            return []

        # 尝试从文件加载
        try:
            import yaml
            with open(fallback_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning(f"无法加载回退响应文件：{e}")

        return []

    def generate(
        self,
        user_input: str,
        semantic_info: Dict[str, Any],
        intent: str,
        intent_match: Optional[Any] = None,
    ) -> str:
        """
        生成响应

        Args:
            user_input: 用户输入
            semantic_info: 语义分析结果
            intent: 意图类型
            intent_match: 意图匹配结果（包含 priority, keyword_only 等）

        Returns:
            生成的响应
        """
        # 1. 优先使用脚本引擎生成响应（如果有）
        if self.script_engine and intent_match:
            response = self._generate_from_script(
                intent_match=intent_match,
                user_input=user_input,
                semantic_info=semantic_info,
            )
            if response:
                logger.debug(
                    "响应策略：script_based",
                    extra={"intent": intent, "strategy": "script_based"},
                )
                return response

        # 2. 对于 keyword_only 意图（问候、告别、感谢），直接返回脚本响应
        # 不使用重组规则
        if intent_match and getattr(intent_match, 'keyword_only', False):
            if self.script_engine:
                response = self._get_script_template(intent_match)
                if response:
                    return response

        # 3. 尝试使用重组规则（仅适用于非 keyword_only 意图）
        if self.reassembly_engine and semantic_info.get("tokens"):
            response = self._try_reassembly(user_input, semantic_info, intent)
            if response:
                logger.debug(
                    "响应策略：reassembly",
                    extra={"intent": intent, "strategy": "reassembly"},
                )
                return response

        # 4. 使用回退响应
        logger.debug(
            "响应策略：fallback",
            extra={"intent": intent, "strategy": "fallback"},
        )
        return self._get_fallback_response()

    def _generate_from_script(
        self,
        intent_match: Any,
        user_input: str,
        semantic_info: Dict[str, Any],
    ) -> Optional[str]:
        """
        从脚本引擎生成响应

        Args:
            intent_match: 意图匹配结果
            user_input: 用户输入
            semantic_info: 语义分析结果

        Returns:
            生成的响应
        """
        if not self.script_engine:
            return None

        # 构建上下文
        context = {
            "entities": semantic_info.get("entities", []),
            "sentiment": semantic_info.get("sentiment", 0.0),
            "sentiment_detail": semantic_info.get("sentiment_detail", {}),
            "sentiment_label": semantic_info.get("sentiment_label", "neutral"),
            "recent_turns": semantic_info.get("recent_turns", []),
        }

        # 获取脚本意图
        script_intent = self.script_engine.intents.get(intent_match.intent)
        if not script_intent:
            return None

        # 如果是 keyword_only，直接返回模板（不进行代词替换）
        if script_intent.keyword_only:
            return self._get_script_template(script_intent)

        # 非 keyword_only，使用重组引擎
        if self.reassembly_engine:
            response = self.script_engine.generate_response_with_reassembly(
                intent=script_intent,
                context=context,
                user_input=user_input,
                reassembly_engine=self.reassembly_engine,
            )
            return response

        # 无重组引擎时，仅填充实体占位符
        return self.script_engine.generate_response(script_intent, context)

    def _get_script_template(self, script_intent: Any) -> Optional[str]:
        """
        获取脚本模板（随机选择）

        Args:
            script_intent: 脚本意图对象

        Returns:
            选中的模板
        """
        import random

        if not script_intent.templates:
            return None

        return random.choice(script_intent.templates)

    def _try_reassembly(
        self,
        user_input: str,
        semantic_info: Dict[str, Any],
        intent: str,
    ) -> Optional[str]:
        """
        尝试使用重组规则生成响应

        Args:
            user_input: 用户输入
            semantic_info: 语义分析结果
            intent: 意图类型

        Returns:
            重组后的响应
        """
        if not self.reassembly_engine:
            return None

        # 根据意图类型选择不同的重组规则
        rules = self._get_reassembly_rules_for_intent(intent)
        if not rules:
            return None

        import random
        rule = random.choice(rules)

        response = self.reassembly_engine.reassemble(
            components=[user_input],
            reassembly_rule=rule,
            apply_pronoun_mapping=True,
        )

        return response.strip() if response else None

    def _get_reassembly_rules_for_intent(self, intent: str) -> List[str]:
        """
        根据意图获取重组规则

        Args:
            intent: 意图类型

        Returns:
            重组规则列表
        """
        # 重组规则应当来自 YAML 配置文件
        # 如果重组引擎没有提供规则，返回空列表
        return []

    def _get_fallback_response(self) -> str:
        """
        获取回退响应

        Returns:
            回退响应
        """
        import random
        return random.choice(self.fallback_responses)

    def set_script_engine(self, script_engine: Any) -> None:
        """
        设置脚本引擎

        Args:
            script_engine: YAML 脚本引擎实例
        """
        self.script_engine = script_engine
        logger.info(f"响应生成器已绑定脚本引擎，支持 {len(script_engine.intents)} 个意图")

    def set_reassembly_engine(self, reassembly_engine: Any) -> None:
        """
        设置重组引擎

        Args:
            reassembly_engine: 句法重组引擎实例
        """
        self.reassembly_engine = reassembly_engine
        logger.info("响应生成器已绑定重组引擎")
