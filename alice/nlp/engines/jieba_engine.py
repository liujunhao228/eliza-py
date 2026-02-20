#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jieba 分词引擎 - 只负责分词
"""

import logging
from typing import List

from alice.nlp.base import Segmenter
from alice.exceptions import DependencyError

logger = logging.getLogger(__name__)

# 必须导入 jieba
try:
    import jieba
except ImportError:
    raise DependencyError(
        "jieba 库未安装",
        suggestion="pip install jieba"
    )


class JiebaEngine(Segmenter):
    """Jieba 分词引擎"""
    
    def __init__(self):
        """初始化"""
        self._seg = jieba
    
    @property
    def is_available(self) -> bool:
        return True
    
    def segment(self, text: str) -> List[str]:
        """分词"""
        return list(self._seg.cut(text))
