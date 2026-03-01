"""
概率决策算法

根据配置的概率分布，随机决定匹配类型。
"""

import random
from typing import Tuple, Optional

from .base import MatchAlgorithm, QueueSnapshot
from ..types import MatchType, UserId
from ..config import MatchConfig


class ProbabilityAlgorithm(MatchAlgorithm):
    """
    概率决策算法

    使用累积概率分布决定匹配类型：
    1. 计算钓鱼 Bot 阈值 = honeypot_in_bot_rate * bot_probability
    2. 计算真人阈值 = 钓鱼阈值 + human_probability
    3. 随机掷骰子决定类型

    示例（默认配置）：
    - 0.00 - 0.105 (10.5%): 钓鱼 Bot
    - 0.105 - 0.405 (30%): 真人匹配
    - 0.405 - 1.00 (59.5%): 普通 Bot
    """

    def decide_match_type(self, config: MatchConfig) -> MatchType:
        """
        根据概率分布决定匹配类型

        Args:
            config: 匹配配置

        Returns:
            匹配类型
        """
        honeypot_threshold, human_threshold = config.get_bot_thresholds()
        roll = random.random()

        if roll < honeypot_threshold:
            return MatchType.HONEYPOT
        elif roll < human_threshold:
            return MatchType.HUMAN
        else:
            return MatchType.BOT

    def select_opponent(self, snapshot: QueueSnapshot) -> Optional[UserId]:
        """
        选择等待队列中的对手（委托给 FIFO 算法）

        Args:
            snapshot: 队列快照

        Returns:
            对手用户 ID
        """
        # 使用 FIFO 策略选择最早等待的真人用户
        return self._find_earliest_human(snapshot)

    def _find_earliest_human(self, snapshot: QueueSnapshot) -> Optional[UserId]:
        """
        查找最早等待的真人匹配用户

        Args:
            snapshot: 队列快照

        Returns:
            最早等待的用户 ID
        """
        if not snapshot.requests:
            return None

        earliest_user: Optional[UserId] = None
        earliest_time = float('inf')

        for uid, request in snapshot.requests.items():
            if request.match_type == MatchType.HUMAN:
                if request.timestamp < earliest_time:
                    earliest_user = uid
                    earliest_time = request.timestamp

        return earliest_user
