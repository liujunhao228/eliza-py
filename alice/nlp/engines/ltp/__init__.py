#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎模块
============

增强版 LTP 引擎，支持完整的 NLP 分析功能。

模块结构:
- config: 配置类 (LtpConfig) - 含标注集常量
- models: 数据模型 (Token, POSTag, DependencyRelation, LtpFullResult 等)
- handlers: 任务处理器 (CWSTaskHandler, POSTaskHandler 等)
- validators: 验证器 (PosTagValidator, DependencyValidator 等)
- exceptions: 异常类 (LtpError, ModelLoadError, AnalysisError)
- engine: 主引擎类 (LtpEngine)

使用示例:
    >>> from alice.nlp.engines.ltp import LtpEngine, LtpConfig
    >>> config = LtpConfig(enable_srl=True)
    >>> engine = LtpEngine(config)
    >>> result = engine.analyze_full("小明在北京大学读书")
    >>> print(result.to_json())
"""

from .config import LtpConfig, NER_ENTITY_MAPPING, POS_TAG_SET, SEMANTIC_ROLE_SET
from .models import (
    TaskType,
    Token,
    POSTag,
    DependencyRelation,
    SemanticRole,
    SemanticDependency,
    SemanticDependencyGraph,
    LtpFullResult,
)
from .handlers import (
    BaseTaskHandler,
    CWSTaskHandler,
    POSTaskHandler,
    NERTaskHandler,
    DEPTaskHandler,
    SRLTaskHandler,
    SDPTaskHandler,
)
from .validators import (
    PosTagValidator,
    DependencyValidator,
    SemanticRoleValidator,
    SemanticDepValidator,
)
from .exceptions import (
    LtpError,
    ModelLoadError,
    AnalysisError,
)
from .engine import LtpEngine, LTP_AVAILABLE, LTP_VERSION

__all__ = [
    # 配置
    'LtpConfig',
    'NER_ENTITY_MAPPING',
    'POS_TAG_SET',
    'SEMANTIC_ROLE_SET',
    # 模型
    'TaskType',
    'Token',
    'POSTag',
    'DependencyRelation',
    'SemanticRole',
    'SemanticDependency',
    'SemanticDependencyGraph',
    'LtpFullResult',
    # 处理器
    'BaseTaskHandler',
    'CWSTaskHandler',
    'POSTaskHandler',
    'NERTaskHandler',
    'DEPTaskHandler',
    'SRLTaskHandler',
    'SDPTaskHandler',
    # 验证器
    'PosTagValidator',
    'DependencyValidator',
    'SemanticRoleValidator',
    'SemanticDepValidator',
    # 异常
    'LtpError',
    'ModelLoadError',
    'AnalysisError',
    # 引擎
    'LtpEngine',
    'LTP_AVAILABLE',
    'LTP_VERSION',
]
