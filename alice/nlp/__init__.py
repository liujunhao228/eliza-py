"""
NLP 模块 - 统一自然语言处理接口

提供轻量级和 LTP 增强两种模式：
- 轻量级：基于规则和词典，快速响应
- LTP 增强：基于依存句法分析，精确理解

情感分析支持：
- 规则词典（轻量级）
- BERT 深度学习模型
- SnowNLP
- 混合模式

使用示例:
    # 轻量级模式
    from alice.nlp import NlpEngine
    nlp = NlpEngine(use_ltp=False)
    result = nlp.analyze("你好")

    # LTP 增强模式（懒加载）
    nlp = NlpEngine(use_ltp=True, lazy_load=True)
    result = nlp.analyze("我和朋友去了北京")

    # 情感分析
    from alice.nlp.sentiment import create_sentiment_engine
    sentiment_engine = create_sentiment_engine(mode='rule')
    result = sentiment_engine.analyze("我很开心")
"""

from alice.nlp.base import NlpEngine, NlpResult, SyntaxStructure, Entity
from alice.nlp.ltp_engine import LtpEngine
from alice.nlp.ner_engine import NerEngine
from alice.nlp.syntax_reassembly import SyntaxReassembly

# 情感分析模块
from alice.nlp.sentiment import (
    SentimentEngine,
    SentimentResult,
    SentimentLabel,
    RuleSentimentEngine,
    BertSentimentEngine,
    SnowNlpSentimentEngine,
    HybridSentimentEngine,
    create_sentiment_engine,
)

__all__ = [
    # 基础 NLP
    "NlpEngine",
    "NlpResult",
    "SyntaxStructure",
    "Entity",
    "LtpEngine",
    "NerEngine",
    "SyntaxReassembly",
    # 情感分析
    "SentimentEngine",
    "SentimentResult",
    "SentimentLabel",
    "RuleSentimentEngine",
    "BertSentimentEngine",
    "SnowNlpSentimentEngine",
    "HybridSentimentEngine",
    "create_sentiment_engine",
]
