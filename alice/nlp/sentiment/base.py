#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情感分析基础模块 - 定义统一接口和数据类
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentLabel(Enum):
    """情感标签枚举"""
    POSITIVE = "positive"      # 正面
    NEGATIVE = "negative"      # 负面
    NEUTRAL = "neutral"        # 中性
    MIXED = "mixed"           # 混合


@dataclass
class SentimentResult:
    """情感分析结果数据类"""
    text: str
    score: float = 0.0              # 情感分数 (-1.0 到 1.0)
    label: SentimentLabel = SentimentLabel.NEUTRAL  # 情感标签
    confidence: float = 0.5         # 置信度 (0.0 到 1.0)
    emotions: Dict[str, float] = field(default_factory=dict)  # 细粒度情感
    keywords: List[str] = field(default_factory=list)  # 情感关键词
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'text': self.text,
            'score': self.score,
            'label': self.label.value,
            'confidence': self.confidence,
            'emotions': self.emotions,
            'keywords': self.keywords,
            'metadata': self.metadata,
        }

    @staticmethod
    def score_to_label(score: float) -> SentimentLabel:
        """
        将情感分数转换为标签

        Args:
            score: 情感分数 (-1.0 到 1.0)

        Returns:
            情感标签
        """
        if score > 0.2:
            return SentimentLabel.POSITIVE
        elif score < -0.2:
            return SentimentLabel.NEGATIVE
        elif abs(score) <= 0.05:
            return SentimentLabel.NEUTRAL
        else:
            # 接近阈值但未达到，视为混合
            return SentimentLabel.MIXED


class SentimentEngine(ABC):
    """
    情感分析引擎基类

    定义统一的情感分析接口
    """

    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        """
        分析文本情感

        Args:
            text: 待分析文本

        Returns:
            情感分析结果
        """
        pass

    @abstractmethod
    def get_label(self, score: float) -> SentimentLabel:
        """
        获取情感标签

        Args:
            score: 情感分数

        Returns:
            情感标签
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        批量分析文本

        Args:
            texts: 待分析文本列表

        Returns:
            情感分析结果列表
        """
        return [self.analyze(text) for text in texts]

    def is_positive(self, result: SentimentResult) -> bool:
        """判断是否为正面情感"""
        return result.label == SentimentLabel.POSITIVE

    def is_negative(self, result: SentimentResult) -> bool:
        """判断是否为负面情感"""
        return result.label == SentimentLabel.NEGATIVE

    def is_neutral(self, result: SentimentResult) -> bool:
        """判断是否为中性情感"""
        return result.label == SentimentLabel.NEUTRAL

    def get_intensity(self, result: SentimentResult) -> str:
        """
        获取情感强度

        Args:
            result: 情感分析结果

        Returns:
            强度描述
        """
        abs_score = abs(result.score)
        if abs_score > 0.7:
            return "strong"
        elif abs_score > 0.4:
            return "moderate"
        else:
            return "weak"
