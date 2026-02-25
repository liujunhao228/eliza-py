"""
Bot 实例信息模块

负责 Bot 实例的状态管理和统计。
"""

import time
from typing import Dict, Optional

from alice.bots.lightweight_alice_bot import LightweightAliceBot


class BotInstanceInfo:
    """Bot 实例信息"""

    def __init__(self, bot: LightweightAliceBot, template_id: str = "default"):
        self.bot = bot
        self.bot_id = id(bot)
        self.template_id = template_id  # Bot 使用的模板 ID
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.request_count = 0
        self.is_busy = False
        self.assigned_at: Optional[float] = None

    def mark_busy(self):
        """标记为忙碌状态"""
        self.is_busy = True
        self.assigned_at = time.time()

    def mark_idle(self):
        """标记为空闲状态"""
        self.is_busy = False
        self.last_used_at = time.time()
        self.request_count += 1

    def get_idle_duration(self) -> float:
        """获取空闲时长（秒）"""
        return time.time() - self.last_used_at

    def get_stats(self) -> Dict:
        """获取实例统计信息"""
        return {
            "bot_id": self.bot_id,
            "template_id": self.template_id,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "request_count": self.request_count,
            "is_busy": self.is_busy,
            "idle_duration": self.get_idle_duration(),
        }
