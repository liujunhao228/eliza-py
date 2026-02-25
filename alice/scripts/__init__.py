"""
脚本引擎模块 - 向后兼容别名

注意：此模块已废弃，请使用 alice.scripting 包。
"""

# 向后兼容：从新 scripting 包导入
from alice.scripting.yaml_engine import YAMLScriptEngine, ScriptIntent

__all__ = [
    "YAMLScriptEngine",
    "ScriptIntent",
]
