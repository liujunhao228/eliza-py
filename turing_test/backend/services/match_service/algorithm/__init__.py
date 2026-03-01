"""
匹配算法模块

提供可插拔的匹配算法实现：
- ProbabilityAlgorithm: 概率决策算法
- FIFOAlgorithm: FIFO 匹配算法
"""

from .base import MatchAlgorithm, QueueSnapshot
from .probability import ProbabilityAlgorithm
from .fifo import FIFOAlgorithm

__all__ = [
    # 抽象基类
    "MatchAlgorithm",
    "QueueSnapshot",
    # 算法实现
    "ProbabilityAlgorithm",
    "FIFOAlgorithm",
]
