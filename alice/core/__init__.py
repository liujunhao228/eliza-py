"""
核心引擎模块

包含对话系统的核心组件：
- DialogueEngine: 对话主引擎
- IntentMatcher: 意图匹配器
- ResponseGenerator: 响应生成器
- ScriptContext: 脚本上下文（从 scripting 导入）
- ScriptMatcher: 脚本匹配器（从 scripting 导入）
- ContextManager: 上下文管理器
"""

from alice.core.dialogue_engine import DialogueEngine
from alice.core.intent_matcher import IntentMatcher
from alice.core.response_generator import ResponseGenerator
from alice.core.context_manager import ContextManager, UserProfile, ConversationTurn

# 从 scripting 包导入（统一脚本引擎架构）
from alice.scripting import ScriptContext, ScriptMatcher

__all__ = [
    # 对话引擎
    "DialogueEngine",
    "IntentMatcher",
    "ResponseGenerator",
    # 上下文管理
    "ContextManager",
    "UserProfile",
    "ConversationTurn",
    # 脚本引擎（从 scripting 导入）
    "ScriptContext",
    "ScriptMatcher",
]
