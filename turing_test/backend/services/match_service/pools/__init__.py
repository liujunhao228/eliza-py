"""
Bot 池模块

提供 Bot 池实现：
- BotPool: 普通 Bot 池 (Lv.1/2/3)
- HoneypotPool: 钓鱼 Bot 池 (攻击型/可疑型)
"""

from .base import BotPoolBase, BotConfig, HoneypotBotConfig
from .bot_pool import BotPool, BotPoolConfig
from .honeypot_pool import HoneypotPool, HoneypotPoolConfig

__all__ = [
    # 抽象基类
    "BotPoolBase",
    "BotConfig",
    "HoneypotBotConfig",
    # 池实现
    "BotPool",
    "BotPoolConfig",
    "HoneypotPool",
    "HoneypotPoolConfig",
]
