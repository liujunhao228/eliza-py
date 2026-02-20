"""
NLP 模块 - 统一自然语言处理接口

新架构：
- 分词：JiebaEngine
- 句法分析 + 实体识别：LtpEngine（可选）
- 工厂：NlpFactory

增强功能（参考 ltp-example.py）：
- LtpConfig: LTP 配置类（支持 device、batch_size、SRL、SDP 等）
- LtpFullResult: 完整分析结果（包含 tokens、pos_tags、dependencies、semantic_roles 等）
- Token、POSTag、DependencyRelation、SemanticRole 等数据模型

注意：
- NerEngine 已移除，实体识别功能已集成到 LTP 引擎中
- 使用 LtpEngine.analyze() 或 LtpEngine.analyze_full() 进行实体识别

使用示例:
    from alice.nlp import NlpFactory

    factory = NlpFactory({'use_ltp': False})

    # 创建单个引擎
    segmenter = factory.create_segmenter()

    # 创建流水线
    pipeline = factory.create_pipeline(['jieba', 'ner'])
    result = pipeline.process("今天我很开心")

    # 使用完整 LTP 功能
    from alice.nlp import LtpConfig, LtpFullResult
    config = LtpConfig(enable_srl=True, enable_sdp=False)
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
from alice.nlp.engines import JiebaEngine, LtpEngine
from alice.nlp.engines.ltp_engine import (
    LtpConfig,
    LtpFullResult,
    Token,
    POSTag,
    DependencyRelation,
    SemanticRole,
    SemanticDependency,
    SemanticDependencyGraph,
    TaskType,
)

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
    # LTP 增强类
    "LtpConfig",
    "LtpFullResult",
    "Token",
    "POSTag",
    "DependencyRelation",
    "SemanticRole",
    "SemanticDependency",
    "SemanticDependencyGraph",
    "TaskType",
    # 工具
    "DictionaryManager",
]
