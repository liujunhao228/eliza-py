#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图匹配器模块

负责基于规则和统计的意图匹配。
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IntentMatch:
    """意图匹配结果"""
    intent: str
    confidence: float
    matched_pattern: Optional[str] = None
    slots: Optional[Dict[str, str]] = None


class IntentMatcher:
    """
    意图匹配器
    
    功能:
    - 基于规则的意图匹配
    - 基于关键词的意图匹配
    - 置信度计算
    - 槽位提取
    """

    def __init__(self):
        """初始化意图匹配器"""
        # 意图模式库
        self.intent_patterns = {
            "greeting": [
                r"^你好",
                r"^嗨",
                r"^hello",
                r"^早上好",
                r"^中午好",
                r"^晚上好",
            ],
            "farewell": [
                r"再见$",
                r"拜拜$",
                r"bye$",
                r"下次 (再)?聊",
            ],
            "question": [
                r"为什么",
                r"怎么 (样)?",
                r"如何",
                r"什么",
                r"哪里",
                r"何时",
                r"谁",
            ],
            "self_introduction": [
                r"你是 (谁 | 什么)",
                r"你叫什么",
                r"介绍一下 (你 | 自己)",
            ],
            "thanks": [
                r"谢谢",
                r"感谢",
                r"thanks",
            ],
            "affirmation": [
                r"^是的",
                r"^对",
                r"^嗯",
                r"^好",
            ],
            "negation": [
                r"^不",
                r"^没",
                r"^不是",
            ],
        }
        
        # 意图关键词
        self.intent_keywords = {
            "emotion_expression": ["开心", "难过", "生气", "焦虑", "兴奋"],
            "narrative": ["去", "做", "看", "买", "发生"],
            "opinion": ["觉得", "认为", "看法", "观点"],
        }

    def match(self, text: str) -> Optional[IntentMatch]:
        """
        匹配意图
        
        Args:
            text: 输入文本
            
        Returns:
            意图匹配结果
        """
        # 1. 尝试模式匹配
        pattern_match = self._match_patterns(text)
        if pattern_match:
            return pattern_match
        
        # 2. 尝试关键词匹配
        keyword_match = self._match_keywords(text)
        if keyword_match:
            return keyword_match
        
        # 3. 无匹配
        return IntentMatch(
            intent="general",
            confidence=0.5,
        )

    def _match_patterns(self, text: str) -> Optional[IntentMatch]:
        """
        基于正则模式匹配意图
        
        Args:
            text: 输入文本
            
        Returns:
            意图匹配结果
        """
        best_match = None
        best_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # 计算置信度（基于匹配长度和位置）
                    confidence = self._calculate_pattern_confidence(
                        match,
                        len(text),
                    )
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = IntentMatch(
                            intent=intent,
                            confidence=confidence,
                            matched_pattern=pattern,
                        )
        
        return best_match

    def _match_keywords(self, text: str) -> Optional[IntentMatch]:
        """
        基于关键词匹配意图
        
        Args:
            text: 输入文本
            
        Returns:
            意图匹配结果
        """
        best_match = None
        best_score = 0
        
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            
            if score > best_score:
                best_score = score
                best_match = IntentMatch(
                    intent=intent,
                    confidence=min(score / len(keywords), 1.0),
                )
        
        if best_score > 0:
            return best_match
        
        return None

    def _calculate_pattern_confidence(
        self,
        match: re.Match,
        text_length: int,
    ) -> float:
        """
        计算模式匹配置信度
        
        Args:
            match: 正则匹配结果
            text_length: 文本长度
            
        Returns:
            置信度 (0.0 - 1.0)
        """
        match_length = match.end() - match.start()
        
        # 基础置信度
        base_confidence = 0.7
        
        # 匹配位置奖励（句首匹配奖励更高）
        if match.start() == 0:
            base_confidence += 0.1
        
        # 匹配长度奖励
        length_bonus = min(match_length / text_length, 0.2)
        
        return min(base_confidence + length_bonus, 1.0)

    def extract_slots(
        self,
        text: str,
        intent: str,
    ) -> Dict[str, str]:
        """
        提取槽位
        
        Args:
            text: 输入文本
            intent: 意图类型
            
        Returns:
            槽位字典
        """
        slots = {}
        
        # 根据意图类型提取不同的槽位
        if intent == "question":
            # 提取疑问词
            question_words = ["为什么", "怎么", "如何", "什么", "哪里", "何时", "谁"]
            for qw in question_words:
                if qw in text:
                    slots["question_word"] = qw
                    break
        
        elif intent == "self_introduction":
            # 提取询问对象
            if "你" in text:
                slots["target"] = "bot"
        
        return slots

    def get_supported_intents(self) -> List[str]:
        """
        获取支持的意图列表
        
        Returns:
            意图列表
        """
        return list(self.intent_patterns.keys()) + list(self.intent_keywords.keys())
