"""
脚本引擎包

提供统一的脚本引擎接口，支持多种脚本语言：
- Lua: 高性能脚本，支持复杂逻辑
- YAML: 声明式配置，易于编写和维护

本包完全独立，不依赖 alice 其他模块。

核心组件:
- BaseScriptEngine: 脚本引擎基类
- ScriptContext: 统一上下文对象
- ScriptMatcher: 统一脚本匹配器
- ScriptConfig: 脚本配置
- ScriptConfigLoader: 配置加载器
- EndAction: 结束对话动作
"""

from alice.scripting.base import (
    BaseScriptEngine,
    ScriptConfig,
    ScriptMatchResult,
    ScriptResponse,
)
from alice.scripting.context import ScriptContext
from alice.scripting.matcher import ScriptMatcher
from alice.scripting.config import ScriptConfigLoader, load_scripts
from alice.scripting.lua.engine import LuaScriptEngine
from alice.scripting.yaml.engine import YAMLScriptEngine, ScriptIntent
from alice.scripting.end_action import EndAction

__all__ = [
    # 基类和数据结构
    "BaseScriptEngine",
    "ScriptConfig",
    "ScriptMatchResult",
    "ScriptResponse",
    # 上下文
    "ScriptContext",
    # 匹配器
    "ScriptMatcher",
    # 配置
    "ScriptConfigLoader",
    "load_scripts",
    # 引擎
    "LuaScriptEngine",
    "YAMLScriptEngine",
    "ScriptIntent",
    # 结束动作
    "EndAction",
]
