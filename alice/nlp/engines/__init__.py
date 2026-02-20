#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NLP 引擎模块

注意：
- NerEngine 已移除，实体识别功能已集成到 LTP 引擎中
- 使用 LtpEngine.analyze() 或 LtpEngine.analyze_full() 进行实体识别
"""

from alice.nlp.engines.jieba_engine import JiebaEngine
from alice.nlp.engines.ltp_engine import LtpEngine

__all__ = [
    "JiebaEngine",
    "LtpEngine",
]
