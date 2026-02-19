#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情感分析引擎工厂 - 统一入口

提供统一的情感分析接口，支持多种后端引擎：
- rule: 规则词典（轻量级，快速）
- bert: BERT 深度学习模型（精确）
- snownlp: SnowNLP（折中方案）
- auto: 自动选择最佳可用引擎
- hybrid: 混合模式（多引擎融合）

使用示例:
    from alice.nlp.sentiment import create_sentiment_engine
    
    # 轻量级模式
    engine = create_sentiment_engine(mode='rule')
    
    # BERT 模式（懒加载）
    engine = create_sentiment_engine(mode='bert', lazy_load=True)
    
    # 自动选择
    engine = create_sentiment_engine(mode='auto')
    
    # 混合模式
    engine = create_sentiment_engine(mode='hybrid', engines=['rule', 'snownlp'])
    
    # 使用
    result = engine.analyze("我很开心")
    print(f"情感分数：{result.score}, 标签：{result.label}")
"""

import logging
from typing import List, Optional, Dict, Any

from alice.nlp.sentiment.base import SentimentEngine, SentimentResult, SentimentLabel
from alice.nlp.sentiment.rule_engine import RuleSentimentEngine
from alice.nlp.sentiment.bert_engine import BertSentimentEngine
from alice.nlp.sentiment.snownlp_engine import SnowNlpSentimentEngine
from alice.utils.degradation_monitor import degradation_monitor

logger = logging.getLogger(__name__)


def create_sentiment_engine(
    mode: str = 'auto',
    **kwargs,
) -> SentimentEngine:
    """
    创建情感分析引擎

    Args:
        mode: 引擎模式
              - 'rule': 规则词典
              - 'bert': BERT 模型
              - 'snownlp': SnowNLP
              - 'auto': 自动选择
              - 'hybrid': 混合模式
        **kwargs: 传递给具体引擎的参数

    Returns:
        情感分析引擎实例
    """
    if mode == 'rule':
        return RuleSentimentEngine(
            custom_positive=kwargs.get('custom_positive'),
            custom_negative=kwargs.get('custom_negative'),
        )

    elif mode == 'bert':
        return BertSentimentEngine(
            model_name=kwargs.get('model_name', 'sentiment'),
            model_path=kwargs.get('model_path'),
            lazy_load=kwargs.get('lazy_load', True),
            device=kwargs.get('device'),
        )

    elif mode == 'snownlp':
        return SnowNlpSentimentEngine()

    elif mode == 'auto':
        return _create_auto_engine(**kwargs)

    elif mode == 'hybrid':
        return HybridSentimentEngine(
            engines=kwargs.get('engines', ['rule', 'snownlp']),
            weights=kwargs.get('weights'),
        )

    else:
        logger.warning(f"未知的情感分析模式：{mode}，使用规则引擎")
        return RuleSentimentEngine()


def _create_auto_engine(**kwargs) -> SentimentEngine:
    """
    自动选择最佳可用引擎

    优先级：BERT > SnowNLP > Rule

    Returns:
        情感分析引擎实例
    """
    # 尝试 BERT
    if kwargs.get('prefer_bert', False):
        try:
            bert_engine = BertSentimentEngine(lazy_load=False)
            if bert_engine.is_available:
                logger.info("自动选择 BERT 情感分析引擎")
                return bert_engine
        except Exception as e:
            logger.warning(f"BERT 引擎不可用：{e}")

    # 尝试 SnowNLP
    try:
        snownlp_engine = SnowNlpSentimentEngine()
        if snownlp_engine.is_available:
            logger.info("自动选择 SnowNLP 情感分析引擎")
            return snownlp_engine
    except Exception as e:
        logger.warning(f"SnowNLP 引擎不可用：{e}")

    # 降级到规则引擎
    logger.info("自动选择规则词典情感分析引擎（降级方案）")
    return RuleSentimentEngine()


class HybridSentimentEngine(SentimentEngine):
    """
    混合情感分析引擎

    融合多个引擎的分析结果，提高准确性：
    - 加权平均
    - 投票机制
    - 置信度融合
    """

    def __init__(
        self,
        engines: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        初始化混合情感分析引擎

        Args:
            engines: 引擎列表 ['rule', 'bert', 'snownlp']
            weights: 引擎权重配置
        """
        self.engines: Dict[str, SentimentEngine] = {}
        self.weights = weights or {
            'rule': 0.3,
            'bert': 0.5,
            'snownlp': 0.2,
        }

        # 初始化指定的引擎
        engine_map = {
            'rule': RuleSentimentEngine,
            'bert': BertSentimentEngine,
            'snownlp': SnowNlpSentimentEngine,
        }

        if engines is None:
            engines = ['rule', 'snownlp']

        for engine_name in engines:
            if engine_name in engine_map:
                try:
                    self.engines[engine_name] = engine_map[engine_name]()
                    logger.info(f"混合引擎已加载：{engine_name}")
                except Exception as e:
                    logger.warning(f"引擎 {engine_name} 加载失败：{e}")

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return len(self.engines) > 0

    def analyze(self, text: str) -> SentimentResult:
        """
        分析文本情感（融合多引擎结果）

        Args:
            text: 待分析文本

        Returns:
            融合后的情感分析结果
        """
        if not self.engines:
            return SentimentResult(
                text=text,
                score=0.0,
                label=SentimentLabel.NEUTRAL,
                confidence=0.5,
            )

        results = []
        valid_weights = []

        # 收集各引擎的分析结果
        for name, engine in self.engines.items():
            if engine.is_available:
                try:
                    result = engine.analyze(text)
                    results.append((name, result))
                    valid_weights.append(self.weights.get(name, 0.2))
                except Exception as e:
                    logger.warning(f"引擎 {name} 分析失败：{e}")

        if not results:
            return SentimentResult(
                text=text,
                score=0.0,
                label=SentimentLabel.NEUTRAL,
                confidence=0.5,
            )

        # 归一化权重
        total_weight = sum(valid_weights)
        if total_weight > 0:
            valid_weights = [w / total_weight for w in valid_weights]

        # 加权平均计算最终分数
        final_score = sum(
            result.score * weight
            for (_, result), weight in zip(results, valid_weights)
        )

        # 计算加权置信度
        final_confidence = sum(
            result.confidence * weight
            for (_, result), weight in zip(results, valid_weights)
        )

        # 确定情感标签
        final_label = SentimentResult.score_to_label(final_score)

        # 融合关键词
        all_keywords = []
        for _, result in results:
            all_keywords.extend(result.keywords)
        unique_keywords = list(set(all_keywords))

        # 融合细粒度情感
        merged_emotions: Dict[str, float] = {}
        for (_, result), weight in zip(results, valid_weights):
            for emotion, intensity in result.emotions.items():
                merged_emotions[emotion] = merged_emotions.get(emotion, 0) + intensity * weight

        return SentimentResult(
            text=text,
            score=final_score,
            label=final_label,
            confidence=final_confidence,
            keywords=unique_keywords,
            emotions=merged_emotions,
            metadata={
                'hybrid': True,
                'engines_used': [name for name, _ in results],
                'weights': dict(zip([name for name, _ in results], valid_weights)),
                'individual_results': [
                    {'engine': name, 'score': result.score, 'confidence': result.confidence}
                    for name, result in results
                ],
            }
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

    def get_engine_stats(self) -> Dict[str, Any]:
        """
        获取引擎统计信息

        Returns:
            引擎状态字典
        """
        return {
            name: {
                'available': engine.is_available,
                'type': type(engine).__name__,
            }
            for name, engine in self.engines.items()
        }
