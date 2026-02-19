#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SnowNLP 情感分析器 - 基于 SnowNLP 库

SnowNLP 是一个轻量级的中文 NLP 库，内置情感分析功能：
- 快速响应
- 无需额外训练
- 适合一般情感分析场景
"""

import logging
from typing import Dict, Optional

from alice.nlp.sentiment.base import SentimentEngine, SentimentResult, SentimentLabel
from alice.utils.degradation_monitor import degradation_monitor

logger = logging.getLogger(__name__)

# 尝试导入 SnowNLP
try:
    from snownlp import SnowNLP
    SNOWNLP_AVAILABLE = True
except ImportError:
    SNOWNLP_AVAILABLE = False
    logger.info("未安装 SnowNLP，SnowNLP 情感分析器不可用")


class SnowNlpSentimentEngine(SentimentEngine):
    """
    SnowNLP 情感分析引擎

    特性:
    - 基于 SnowNLP 库
    - 轻量级，快速响应
    - 无需额外训练
    """

    def __init__(self):
        """初始化 SnowNLP 情感分析引擎"""
        self._available = SNOWNLP_AVAILABLE

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self._available

    def analyze(self, text: str) -> SentimentResult:
        """
        分析文本情感

        Args:
            text: 待分析文本

        Returns:
            情感分析结果
        """
        if not SNOWNLP_AVAILABLE:
            degradation_monitor.register_degradation(
                component='snownlp_sentiment',
                reason='SnowNLP 库未安装',
                severity=2,
                recovery_plan='安装 SnowNLP 库：pip install snownlp'
            )
            return self._fallback_analyze(text)

        try:
            # 使用 SnowNLP 进行情感分析
            s = SnowNLP(text)
            
            # SnowNLP 返回的是正面情感概率 (0.0 - 1.0)
            # 转换为统一的情感分数 (-1.0 到 1.0)
            positive_prob = s.sentiments
            
            # 转换公式：score = 2 * prob - 1
            score = 2 * positive_prob - 1
            
            # 确定情感标签
            label = SentimentResult.score_to_label(score)
            
            # 计算置信度
            confidence = max(positive_prob, 1 - positive_prob)
            
            # 获取关键词
            keywords = s.keywords(3) if hasattr(s, 'keywords') else []
            
            return SentimentResult(
                text=text,
                score=score,
                label=label,
                confidence=confidence,
                keywords=keywords,
                metadata={
                    'positive_prob': positive_prob,
                    'summary': s.summary() if hasattr(s, 'summary') else [],
                }
            )

        except Exception as e:
            logger.warning(f"SnowNLP 情感分析失败，降级处理：{e}")
            degradation_monitor.register_degradation(
                component='snownlp_sentiment_inference',
                reason=f'SnowNLP 分析异常：{type(e).__name__}',
                severity=2,
                recovery_plan='检查输入文本格式或重启服务'
            )
            return self._fallback_analyze(text)

    def _fallback_analyze(self, text: str) -> SentimentResult:
        """
        降级分析方案

        Args:
            text: 待分析文本

        Returns:
            情感分析结果（中性）
        """
        return SentimentResult(
            text=text,
            score=0.0,
            label=SentimentLabel.NEUTRAL,
            confidence=0.5,
            metadata={'fallback': True, 'reason': 'SnowNLP 模型不可用'},
        )

    def get_label(self, score: float) -> SentimentLabel:
        """
        获取情感标签

        Args:
            score: 情感分数

        Returns:
            情感标签
        """
        return SentimentResult.score_to_label(score)

    def get_sentiment_summary(self, text: str) -> Optional[str]:
        """
        获取情感摘要

        Args:
            text: 待分析文本

        Returns:
            摘要文本
        """
        if not SNOWNLP_AVAILABLE:
            return None

        try:
            s = SnowNLP(text)
            if hasattr(s, 'summary'):
                return ' '.join(s.summary())
        except Exception as e:
            logger.error(f"获取 SnowNLP 摘要失败：{e}")

        return None

    def get_tags(self, text: str) -> Optional[list]:
        """
        获取文本标签

        Args:
            text: 待分析文本

        Returns:
            标签列表
        """
        if not SNOWNLP_AVAILABLE:
            return None

        try:
            s = SnowNLP(text)
            if hasattr(s, 'tags'):
                return s.tags()
        except Exception as e:
            logger.error(f"获取 SnowNLP 标签失败：{e}")

        return None
