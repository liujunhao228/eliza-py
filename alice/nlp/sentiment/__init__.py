#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情感分析引擎模块 - 统一接口

支持多种情感分析模型：
- 规则词典（轻量级，快速）
- BERT 深度学习模型（精确）
- SnowNLP（可选依赖）
- 混合模式（多引擎融合）

使用示例:
    # 轻量级模式
    from alice.nlp.sentiment import create_sentiment_engine
    engine = create_sentiment_engine(mode='rule')
    result = engine.analyze("我很开心")
    
    # BERT 模式（懒加载）
    engine = create_sentiment_engine(mode='bert', lazy_load=True)
    result = engine.analyze("我感到很沮丧")
    
    # SnowNLP 模式
    engine = create_sentiment_engine(mode='snownlp')
    result = engine.analyze("这真是太棒了")
    
    # 自动选择
    engine = create_sentiment_engine(mode='auto')
    
    # 混合模式
    engine = create_sentiment_engine(mode='hybrid', engines=['rule', 'snownlp'])
"""

from alice.nlp.sentiment.base import (
    SentimentEngine,
    SentimentResult,
    SentimentLabel,
)
from alice.nlp.sentiment.rule_engine import RuleSentimentEngine
from alice.nlp.sentiment.bert_engine import BertSentimentEngine
from alice.nlp.sentiment.snownlp_engine import SnowNlpSentimentEngine
from alice.nlp.sentiment.engine_factory import (
    create_sentiment_engine,
    HybridSentimentEngine,
)

__all__ = [
    # 基类
    "SentimentEngine",
    "SentimentResult",
    "SentimentLabel",
    # 具体引擎
    "RuleSentimentEngine",
    "BertSentimentEngine",
    "SnowNlpSentimentEngine",
    "HybridSentimentEngine",
    # 工厂函数
    "create_sentiment_engine",
]
