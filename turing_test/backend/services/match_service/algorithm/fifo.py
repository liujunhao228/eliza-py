"""
FIFO 匹配算法

先进先出策略：选择最早加入队列的用户进行匹配。
"""

from typing import Optional
import time

from .base import MatchAlgorithm, QueueSnapshot
from ..types import MatchType, UserId
from ..config import MatchConfig


class FIFOAlgorithm(MatchAlgorithm):
    """
    FIFO 匹配算法

    核心策略：
    1. 按时间戳排序等待队列
    2. 选择最早加入的真人匹配用户

    适用场景：
    - 真人匹配
    - 公平性要求高的场景
    """

    def decide_match_type(self, config: MatchConfig) -> MatchType:
        """
        FIFO 算法不负责概率决策，抛出异常

        Raises:
            NotImplementedError: 此算法不支持概率决策
        """
        raise NotImplementedError(
            "FIFOAlgorithm 仅用于对手选择，不支持概率决策"
        )

    def select_opponent(self, snapshot: QueueSnapshot) -> Optional[UserId]:
        """
        选择最早等待的真人匹配用户

        Args:
            snapshot: 队列快照

        Returns:
            对手用户 ID，如果没有合适的对手则返回 None
        """
        if not snapshot.requests:
            return None

        # 过滤出真人匹配请求
        human_requests = [
            (uid, req) for uid, req in snapshot.requests.items()
            if req.match_type == MatchType.HUMAN
        ]

        if not human_requests:
            return None

        # 按时间戳排序，返回最早的
        human_requests.sort(key=lambda x: x[1].timestamp)
        return human_requests[0][0]

    @staticmethod
    def get_wait_time(snapshot: QueueSnapshot, user_id: UserId) -> Optional[float]:
        """
        计算用户等待时间

        Args:
            snapshot: 队列快照
            user_id: 用户 ID

        Returns:
            等待时间（秒），如果用户不在队列中则返回 None
        """
        import time
        request = snapshot.requests.get(user_id)
        if not request:
            return None
        return snapshot.timestamp - request.timestamp

    @staticmethod
    def get_queue_position(snapshot: QueueSnapshot, user_id: UserId) -> Optional[int]:
        """
        获取用户在队列中的位置

        Args:
            snapshot: 队列快照
            user_id: 用户 ID

        Returns:
            队列位置（从 1 开始），如果用户不在队列中则返回 None
        """
        request = snapshot.requests.get(user_id)
        if not request:
            return None

        # 计算比当前用户更早的真人匹配请求数量
        position = 1
        for uid, req in snapshot.requests.items():
            if req.match_type == MatchType.HUMAN and req.timestamp < request.timestamp:
                position += 1

        return position
