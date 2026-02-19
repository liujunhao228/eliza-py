#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级语义分析器模块

基于规则和轻量级统计实现语义分析。
可选使用 LTP 增强模式进行更精确的分析。
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

from alice.processors.text_processor import TextPreprocessor

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    语义分析器

    功能:
    - 情感分析（基于词典）
    - 意图检测（基于关键词）
    - 实体提取（基于规则或 LTP）
    - 话题识别

    设计原则:
    - 规则优先：基于规则的处理优于统计
    - 轻量化：默认不依赖重型模型
    - 可扩展：支持 LTP 增强模式
    - 降级处理：LTP 不可用时自动降级
    """

    def __init__(
        self,
        use_ltp: bool = False,
        ltp_engine: Optional[Any] = None,
    ):
        """
        初始化语义分析器

        Args:
            use_ltp: 是否使用 LTP 增强
            ltp_engine: LTP 引擎实例（可选）
        """
        self.preprocessor = TextPreprocessor()
        self.use_ltp = use_ltp
        self.ltp_engine = ltp_engine

        # 情感词库
        self.positive_words = {
            "好", "棒", "喜欢", "开心", "高兴", "快乐", "幸福", "满意",
            "爱", "美好", "顺利", "成功", "优秀", "赞美", "感谢",
            "温暖", "安心", "轻松", "愉快", "欣慰", "骄傲", "自豪",
        }
        self.negative_words = {
            "坏", "差", "讨厌", "难过", "生气", "焦虑", "痛苦", "失望",
            "恨", "烦恼", "压力", "累", "困", "烦", "糟糕", "失败",
            "伤心", "悲伤", "沮丧", "愤怒", "恼火", "烦躁", "郁闷",
            "委屈", "害怕", "恐惧", "紧张", "担心", "不安", "慌乱",
            "疲惫", "疲倦", "压抑", "孤独", "寂寞", "无助",
        }

        # 意图关键词映射
        self.intent_keywords = {
            "narrative": ["去", "做", "看", "买", "发生", "出现", "开始", "结束"],
            "emotion": ["感觉", "觉得", "心情", "情绪", "感受"],
            "person": ["朋友", "家人", "同事", "同学", "老师", "老板"],
            "relationship": ["关系", "相处", "吵架", "矛盾", "误会"],
            "question": ["为什么", "怎么", "如何", "什么", "哪里", "何时"],
            "belief": ["认为", "相信", "以为", "猜想"],
            "desire": ["想", "想要", "希望", "渴望", "期待", "需要"],
        }

        # 实体提取规则
        self.pronouns = ["我", "你", "他", "她", "它", "我们", "你们", "他们", "她们"]
        self.time_words = ["今天", "昨天", "明天", "刚才", "最近", "上周", "下周", "现在", "当时"]

        # 人称代词到实体的映射
        self.pronoun_entity_map = {
            "我": "user",
            "你": "bot",
            "他": "third_person",
            "她": "third_person",
            "它": "third_person",
            "我们": "user_group",
            "你们": "bot_group",
            "他们": "third_person_group",
            "她们": "third_person_group",
        }

    def analyze(self, text: str) -> Dict:
        """
        分析文本语义

        Args:
            text: 待分析的文本

        Returns:
            分析结果字典
        """
        # 文本预处理
        standardized_text = self.preprocessor.standardize_text(text)
        words = self.preprocessor.segment_text(standardized_text)

        # LTP 增强分析
        if self.use_ltp and self.ltp_engine and self.ltp_engine.is_available:
            return self._analyze_with_ltp(text, standardized_text, words)

        # 轻量级分析
        analysis = {
            "tokens": words,
            "sentiment": self._analyze_sentiment(words),
            "intent": self._detect_intent(words),
            "entities": self._extract_entities(words, text),
            "original_text": text,
            "standardized_text": standardized_text,
        }

        return analysis

    def _analyze_with_ltp(self, text: str, standardized_text: str, words: List[str]) -> Dict:
        """
        使用 LTP 增强分析

        Args:
            text: 原始文本
            standardized_text: 标准化文本
            words: 分词结果

        Returns:
            分析结果字典
        """
        try:
            # 使用 LTP 引擎进行完整分析
            ltp_result = self.ltp_engine.analyze(text)

            # 融合 LTP 结果和轻量级分析
            ltp_entities = [(e.entity_type.value, e.text) for e in ltp_result.entities]
            rule_entities = self._extract_entities(words, text)

            # 合并实体（去重）
            all_entities = list(set(rule_entities + ltp_entities))

            return {
                "tokens": ltp_result.tokens or words,
                "sentiment": self._analyze_sentiment(words),
                "intent": self._detect_intent(words),
                "entities": all_entities,
                "syntax": ltp_result.syntax.to_dict() if ltp_result.syntax else None,
                "original_text": text,
                "standardized_text": standardized_text,
                "use_ltp": True,
            }

        except Exception as e:
            logger.warning(f"LTP 增强分析失败，降级到轻量级模式：{e}")
            return self.analyze(text)

    def _analyze_sentiment(self, tokens: List[str]) -> float:
        """
        简单情感分析
        
        Args:
            tokens: 分词结果
            
        Returns:
            情感分数 (-1.0 到 1.0)
        """
        pos_count = sum(
            1 for token in tokens 
            if any(pw in token for pw in self.positive_words)
        )
        neg_count = sum(
            1 for token in tokens 
            if any(nw in token for nw in self.negative_words)
        )
        
        if pos_count + neg_count == 0:
            return 0.0
        
        # 归一化到 [-1, 1]
        return (pos_count - neg_count) / (pos_count + neg_count)

    def _detect_intent(self, tokens: List[str]) -> str:
        """
        意图检测
        
        Args:
            tokens: 分词结果
            
        Returns:
            意图类型
        """
        intent_scores = defaultdict(int)
        
        for intent, keywords in self.intent_keywords.items():
            # 检查 tokens 中是否包含关键词或其子串
            score = sum(
                1 for token in tokens 
                if any(kw in token for kw in keywords)
            )
            intent_scores[intent] = score
        
        # 返回得分最高的意图
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)
        
        return "general"

    def _extract_entities(
        self,
        tokens: List[str],
        text: str,
    ) -> List[Tuple[str, str]]:
        """
        提取关键实体
        
        Args:
            tokens: 分词结果
            text: 原始文本
            
        Returns:
            实体列表 [(类型，文本), ...]
        """
        entities = []
        
        # 人称代词
        for pronoun in self.pronouns:
            if pronoun in tokens:
                entity_type = self.pronoun_entity_map.get(pronoun, "pronoun")
                entities.append((entity_type, pronoun))
        
        # 时间词
        for tw in self.time_words:
            if tw in tokens:
                entities.append(("time", tw))
        
        # 简单的人名识别（中文常见姓氏 + 名字模式）
        common_surnames = {
            "李", "王", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴",
            "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗",
        }
        for i, token in enumerate(tokens):
            if len(token) >= 2 and token[0] in common_surnames:
                entities.append(("person", token))
        
        return entities

    def get_sentiment_label(self, sentiment_score: float) -> str:
        """
        获取情感标签
        
        Args:
            sentiment_score: 情感分数
            
        Returns:
            情感标签
        """
        if sentiment_score > 0.2:
            return "positive"
        elif sentiment_score < -0.2:
            return "negative"
        else:
            return "neutral"

    def analyze_with_label(self, text: str) -> Dict:
        """
        分析文本并添加情感标签
        
        Args:
            text: 待分析的文本
            
        Returns:
            分析结果字典（包含情感标签）
        """
        analysis = self.analyze(text)
        analysis["sentiment_label"] = self.get_sentiment_label(analysis["sentiment"])
        return analysis
