"""
匹配服务模块（简化版）

极简匹配逻辑：
- 20% 概率直接分配 AI（对照组）
- 80% 概率尝试匹配真人（FIFO）
- 结果暂存，前端主动拉取
"""

from .service import MatchService, match_service, get_match_service
from .algorithm import MatchAlgorithm

__all__ = [
    "MatchService",
    "match_service",
    "get_match_service",
    "MatchAlgorithm",
]
