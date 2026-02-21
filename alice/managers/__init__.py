"""
管理器模块

包含各种管理器类：
- ContextManager: 上下文管理
- UserProfile: 用户画像数据类

注意：ConfigManager 已被移除，请使用 config.settings 替代
"""

from alice.managers.context_manager import ContextManager, UserProfile

__all__ = [
    "ContextManager",
    "UserProfile",
]
