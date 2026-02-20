#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件基类模块

定义所有插件必须遵循的标准接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PluginResult:
    """插件处理结果"""
    success: bool
    response: Optional[str] = None
    entities: Optional[List[tuple]] = None
    intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BasePlugin(ABC):
    """
    插件基类
    
    所有插件必须继承此类并实现抽象方法。
    
    插件生命周期:
    1. __init__: 插件实例化
    2. initialize: 初始化资源
    3. process_input: 处理用户输入
    4. generate_response: 生成响应
    5. cleanup: 清理资源
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化插件
        
        Args:
            config: 插件配置字典
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.enabled = True
        self.priority = 50  # 默认优先级，0-100，越高越优先

    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化插件资源
        
        Returns:
            是否初始化成功
        """
        pass

    @abstractmethod
    def process_input(self, text: str, context: Dict[str, Any]) -> PluginResult:
        """
        处理用户输入
        
        Args:
            text: 用户输入文本
            context: 对话上下文
            
        Returns:
            插件处理结果
        """
        pass

    def generate_response(self, result: PluginResult) -> Optional[str]:
        """
        根据处理结果生成响应
        
        Args:
            result: 插件处理结果
            
        Returns:
            生成的响应文本
        """
        return result.response

    def cleanup(self) -> None:
        """清理插件资源"""
        pass

    def reload_config(self, config: Dict[str, Any]) -> None:
        """
        重新加载配置
        
        Args:
            config: 新的配置字典
        """
        self.config = config

    def is_available(self) -> bool:
        """
        检查插件是否可用
        
        Returns:
            插件是否可用
        """
        return self.enabled

    def get_info(self) -> Dict[str, Any]:
        """
        获取插件信息
        
        Returns:
            插件信息字典
        """
        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "config": self.config,
        }
