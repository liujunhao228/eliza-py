"""
匹配算法抽象基类

定义匹配算法的标准接口，支持可插拔实现。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict

from ..types import MatchType, UserId, MatchRequest


@dataclass
class QueueSnapshot:
    """
    队列快照（供算法使用）

    Attributes:
        requests: 当前队列中的请求
        timestamp: 快照时间戳
    """
    requests: Dict[UserId, MatchRequest]
    timestamp: float


class MatchAlgorithm(ABC):
    """
    匹配算法抽象基类

    定义匹配算法的标准接口，支持：
    - 概率决策：决定匹配类型（真人/Bot/钓鱼）
    - 对手选择：从等待队列中选择对手

    实现子类：
    - ProbabilityAlgorithm: 概率决策算法
    - FIFOAlgorithm: 先进先出匹配算法
    """

    @abstractmethod
    def decide_match_type(self, config: "MatchConfig") -> MatchType:
        """
        决定匹配类型

        Args:
            config: 匹配配置

        Returns:
            匹配类型
        """
        pass

    @abstractmethod
    def select_opponent(self, snapshot: QueueSnapshot) -> Optional[UserId]:
        """
        从等待队列中选择对手

        Args:
            snapshot: 队列快照

        Returns:
            对手用户 ID，如果没有合适的对手则返回 None
        """
        pass
