"""
脚本引擎 v2 模块

支持 YAML 格式的脚本配置，提供更灵活的脚本定义。
"""

from alice.scripts.yaml_script_engine import YAMLScriptEngine, ScriptIntent

__all__ = [
    "YAMLScriptEngine",
    "ScriptIntent",
]
