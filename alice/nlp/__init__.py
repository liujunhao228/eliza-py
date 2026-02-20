"""
NLP 模块 - 统一自然语言处理接口

新架构：
- 分词：JiebaEngine
- 句法分析：LtpEngine（可选）
- 实体识别：NerEngine
- 工厂：NlpFactory

使用示例:
    from alice.nlp import NlpFactory

    factory = NlpFactory({'use_ltp': False})

    # 创建单个引擎
    segmenter = factory.create_segmenter()

    # 创建流水线
    pipeline = factory.create_pipeline(['jieba', 'ner'])
    result = pipeline.process("今天我很开心")
"""

from alice.nlp.base import (
    EntityType,
    Entity,
    SyntaxStructure,
    NlpResult,
    Segmenter,
    SyntaxAnalyzer,
    EntityRecognizer,
)
from alice.nlp.factory import NlpFactory, NlpPipeline
from alice.nlp.dictionaries import DictionaryManager
from alice.nlp.engines import JiebaEngine, LtpEngine, NerEngine

__all__ = [
    # 基础数据类
    "EntityType",
    "Entity",
    "SyntaxStructure",
    "NlpResult",
    # 接口
    "Segmenter",
    "SyntaxAnalyzer",
    "EntityRecognizer",
    # 工厂
    "NlpFactory",
    "NlpPipeline",
    # 引擎
    "JiebaEngine",
    "LtpEngine",
    "NerEngine",
    # 工具
    "DictionaryManager",
]
