#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图匹配器模块 - 重构版

基于 YAML 脚本引擎的意图匹配，移除硬编码规则。
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IntentMatch:
    """意图匹配结果"""
    intent: str
    confidence: float
    priority: int = 50
    keyword_only: bool = False
    metadata: Optional[Dict[str, Any]] = None


class IntentMatcher:
    """
    意图匹配器 - 重构版

    特性:
    - 基于 YAML 脚本引擎驱动
    - 移除硬编码规则
    - 支持优先级调度
    - 支持条件触发
    """

    def __init__(self, script_engine: Optional[Any] = None):
        """
        初始化意图匹配器

        Args:
            script_engine: YAML 脚本引擎实例
        """
        self.script_engine = script_engine

    def match(self, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[IntentMatch]:
        """
        匹配意图

        Args:
            text: 输入文本
            context: 上下文信息（entities 等）

        Returns:
            意图匹配结果
        """
        # 使用 YAML 脚本引擎匹配
        if self.script_engine:
            script_intent = self.script_engine.match(text, context)
            if script_intent:
                return IntentMatch(
                    intent=script_intent.name,
                    confidence=self._calculate_confidence(script_intent, text),
                    priority=script_intent.priority,
                    keyword_only=script_intent.keyword_only,
                    metadata={
                        "script_id": script_intent.name,
                        "templates_count": len(script_intent.templates),
                    }
                )

        # 无脚本引擎或无匹配时，返回通用意图
        return IntentMatch(
            intent="general",
            confidence=0.5,
            priority=10,
        )

    def _calculate_confidence(self, script_intent: Any, text: str) -> float:
        """
        计算匹配置信度

        Args:
            script_intent: 脚本意图对象
            text: 输入文本

        Returns:
            置信度 (0.0 - 1.0)
        """
        # 基础置信度基于优先级
        base_confidence = min(script_intent.priority / 100.0, 1.0)

        # 关键词匹配奖励
        condition = script_intent.condition or {}
        keywords = condition.get("keywords", [])
        if keywords:
            matched_keywords = sum(1 for kw in keywords if kw in text)
            if matched_keywords > 0:
                keyword_bonus = min(matched_keywords * 0.1, 0.3)
                base_confidence += keyword_bonus

        # 实体匹配奖励
        entities = condition.get("entities", [])
        if entities:
            # 实体匹配由脚本引擎已经验证过
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def get_supported_intents(self) -> List[str]:
        """
        获取支持的意图列表

        Returns:
            意图列表
        """
        if self.script_engine:
            return list(self.script_engine.intents.keys())
        return ["general"]

    def set_script_engine(self, script_engine: Any) -> None:
        """
        设置脚本引擎

        Args:
            script_engine: YAML 脚本引擎实例
        """
        self.script_engine = script_engine
        logger.info(f"意图匹配器已绑定脚本引擎，支持 {len(script_engine.intents)} 个意图")
