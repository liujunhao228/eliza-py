#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理器模块

负责插件的生命周期管理、注册、卸载和执行调度。
"""

import logging
from typing import Any, Dict, List, Optional, Type
from collections import OrderedDict

from alice.plugins.base_plugin import BasePlugin, PluginResult

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器
    
    功能:
    - 插件注册和注销
    - 插件生命周期管理
    - 插件执行调度（按优先级）
    - 插件配置管理
    - 插件状态监控
    """

    def __init__(self):
        """初始化插件管理器"""
        # 使用 OrderedDict 保持插入顺序
        self._plugins: OrderedDict[str, BasePlugin] = OrderedDict()
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def register_plugin(
        self,
        name: str,
        plugin_class: Type[BasePlugin],
        config: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None,
    ) -> bool:
        """
        注册插件
        
        Args:
            name: 插件名称
            plugin_class: 插件类
            config: 插件配置
            priority: 插件优先级（可选，覆盖插件默认值）
            
        Returns:
            是否注册成功
        """
        try:
            # 创建插件实例
            plugin = plugin_class(config=config)
            
            # 设置优先级
            if priority is not None:
                plugin.priority = priority
            
            # 保存配置
            self._plugin_configs[name] = config or {}
            
            # 注册插件
            self._plugins[name] = plugin
            
            logger.info(f"插件已注册：{name} (优先级：{plugin.priority})")
            return True
            
        except Exception as e:
            logger.error(f"注册插件失败 {name}: {e}")
            return False

    def unregister_plugin(self, name: str) -> bool:
        """
        注销插件
        
        Args:
            name: 插件名称
            
        Returns:
            是否注销成功
        """
        if name not in self._plugins:
            logger.warning(f"插件不存在：{name}")
            return False
        
        try:
            plugin = self._plugins[name]
            plugin.cleanup()
            del self._plugins[name]
            del self._plugin_configs[name]
            
            logger.info(f"插件已注销：{name}")
            return True
            
        except Exception as e:
            logger.error(f"注销插件失败 {name}: {e}")
            return False

    def initialize_all(self) -> bool:
        """
        初始化所有已注册的插件
        
        Returns:
            是否所有插件都初始化成功
        """
        success = True
        
        for name, plugin in self._plugins.items():
            try:
                if not plugin.initialize():
                    logger.warning(f"插件初始化失败：{name}")
                    plugin.enabled = False
                    success = False
                else:
                    logger.info(f"插件初始化成功：{name}")
            except Exception as e:
                logger.error(f"插件初始化异常 {name}: {e}")
                plugin.enabled = False
                success = False
        
        self._initialized = True
        return success

    def cleanup_all(self) -> None:
        """清理所有插件资源"""
        for name, plugin in self._plugins.items():
            try:
                plugin.cleanup()
                logger.info(f"插件已清理：{name}")
            except Exception as e:
                logger.error(f"插件清理失败 {name}: {e}")
        
        self._initialized = False

    def process_input(
        self,
        text: str,
        context: Dict[str, Any],
        priority_threshold: int = 0,
    ) -> List[PluginResult]:
        """
        按优先级处理用户输入
        
        Args:
            text: 用户输入文本
            context: 对话上下文
            priority_threshold: 优先级阈值，只处理高于此值的插件
            
        Returns:
            所有插件的处理结果列表
        """
        if not self._initialized:
            logger.warning("插件管理器未初始化")
            return []
        
        results = []
        
        # 按优先级排序（从高到低）
        sorted_plugins = sorted(
            self._plugins.values(),
            key=lambda p: p.priority,
            reverse=True,
        )
        
        for plugin in sorted_plugins:
            if not plugin.enabled:
                continue
            
            if plugin.priority < priority_threshold:
                continue
            
            try:
                result = plugin.process_input(text, context)
                results.append(result)
            except Exception as e:
                logger.error(f"插件处理输入失败 {plugin.name}: {e}")
                results.append(PluginResult(
                    success=False,
                    metadata={"error": str(e), "plugin": plugin.name},
                ))
        
        return results

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """
        获取指定插件
        
        Args:
            name: 插件名称
            
        Returns:
            插件实例，不存在返回 None
        """
        return self._plugins.get(name)

    def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        if name not in self._plugins:
            return False
        self._plugins[name].enabled = True
        logger.info(f"插件已启用：{name}")
        return True

    def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        if name not in self._plugins:
            return False
        self._plugins[name].enabled = False
        logger.info(f"插件已禁用：{name}")
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        列出所有插件信息
        
        Returns:
            插件信息列表
        """
        return [
            {
                "name": name,
                "enabled": plugin.enabled,
                "priority": plugin.priority,
                "initialized": self._initialized,
            }
            for name, plugin in self._plugins.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取插件管理器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_plugins": len(self._plugins),
            "enabled_plugins": sum(1 for p in self._plugins.values() if p.enabled),
            "initialized": self._initialized,
            "plugins": self.list_plugins(),
        }
