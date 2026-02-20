"""
管理器模块

包含各种管理器类：
- ConfigManager: 统一配置管理
- ContextManager: 上下文管理
- UserProfile: 用户画像数据类
"""

from alice.managers.config_manager import ConfigManager
from alice.managers.context_manager import ContextManager, UserProfile

__all__ = [
    "ConfigManager",
    "ContextManager",
    "UserProfile",
]
