"""
插件系统模块

提供插件化架构支持，允许动态扩展 Alice 的功能。
"""

from alice.plugins.base_plugin import BasePlugin, PluginResult
from alice.plugins.plugin_manager import PluginManager
from alice.plugins.curiosity_plugin import CuriosityPlugin

__all__ = [
    "BasePlugin",
    "PluginResult",
    "PluginManager",
    "CuriosityPlugin",
]
