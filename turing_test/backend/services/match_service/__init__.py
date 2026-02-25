"""
匹配服务模块

提供匹配队列管理、匹配算法和统计功能。
"""

from .service import MatchService, match_service, get_match_service
from .queue import MatchQueue, MatchPriority
from .algorithm import MatchAlgorithm
from .statistics import MatchStatistics

__all__ = [
    "MatchService",
    "match_service",
    "get_match_service",
    "MatchQueue",
    "MatchPriority",
    "MatchAlgorithm",
    "MatchStatistics",
]
