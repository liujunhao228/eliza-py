#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本引擎基类

定义所有脚本引擎的统一接口和数据结构。
本模块不依赖任何 alice 其他模块，确保 scripting 包的独立性。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class ScriptConfig:
    """
    脚本配置
    
    用于定义脚本的加载和运行参数。
    
    Attributes:
        script_id: 脚本唯一标识
        name: 脚本名称
        script_type: 脚本类型 ("lua" | "yaml")
        priority: 优先级 (0-100)，越高越优先
        enabled: 是否启用
        description: 脚本描述
        variables: 全局变量（传递给脚本的默认变量）
        max_execution_time: 最大执行时间 (秒)
        sandbox_mode: 是否启用沙箱模式
        script_path: 脚本文件路径
        metadata: 其他元数据
    """
    script_id: str
    name: str
    script_type: str  # "lua" | "yaml"
    priority: int = 50
    enabled: bool = True
    description: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    max_execution_time: float = 1.0
    sandbox_mode: bool = True
    script_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'script_id': self.script_id,
            'name': self.name,
            'script_type': self.script_type,
            'priority': self.priority,
            'enabled': self.enabled,
            'description': self.description,
            'variables': self.variables,
            'max_execution_time': self.max_execution_time,
            'sandbox_mode': self.sandbox_mode,
            'script_path': str(self.script_path) if self.script_path else None,
            'metadata': self.metadata,
        }


@dataclass
class ScriptMatchResult:
    """
    脚本匹配结果
    
    Attributes:
        script_id: 脚本 ID
        script_type: 脚本类型 ("lua" | "yaml")
        intent_name: 意图名称
        priority: 优先级
        confidence: 置信度 (0.0 - 1.0)
        metadata: 附加元数据
    """
    script_id: str
    script_type: str  # "lua" | "yaml"
    intent_name: str
    priority: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def score(self) -> float:
        """
        计算综合得分（用于排序）
        
        Returns:
            综合得分 = priority * 0.7 + confidence * 100 * 0.3
        """
        return self.priority * 0.7 + self.confidence * 100 * 0.3


@dataclass
class ScriptResponse:
    """
    脚本响应结果

    Attributes:
        text: 响应文本
        script_id: 脚本 ID
        intent_name: 意图名称
        metadata: 附加元数据
        end_action: 结束对话动作 ("none" | "direct" | "farewell")
        end_reason: 结束原因 ("max_turns", "suspicion", "timeout", "user_farewell", etc.)
    """
    text: str = ""
    script_id: str = ""
    intent_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    end_action: str = "none"  # "none" | "direct" | "farewell"
    end_reason: str = ""


class BaseScriptEngine(ABC):
    """
    脚本引擎基类
    
    所有脚本引擎必须继承此接口，确保统一的调用方式。
    
    使用示例:
        engine = LuaScriptEngine()
        config = ScriptConfig(...)
        engine.load_script(config)
        match = engine.match(context)
        if match:
            response = engine.generate_response(match.script_id, context)
    """
    
    def __init__(self, engine_type: str = "base"):
        """
        初始化脚本引擎
        
        Args:
            engine_type: 引擎类型标识
        """
        self.engine_type = engine_type
        self.scripts: Dict[str, ScriptConfig] = {}
        self._stats = {
            'load_count': 0,
            'match_count': 0,
            'error_count': 0,
        }
    
    @abstractmethod
    def load_script(self, config: ScriptConfig) -> bool:
        """
        加载脚本
        
        Args:
            config: 脚本配置
            
        Returns:
            是否加载成功
        """
        pass
    
    @abstractmethod
    def unload_script(self, script_id: str) -> bool:
        """
        卸载脚本
        
        Args:
            script_id: 脚本 ID
            
        Returns:
            是否卸载成功
        """
        pass
    
    @abstractmethod
    def match(self, context: 'ScriptContext') -> Optional[ScriptMatchResult]:
        """
        匹配脚本
        
        Args:
            context: 脚本上下文
            
        Returns:
            匹配结果，无匹配时返回 None
        """
        pass
    
    @abstractmethod
    def generate_response(
        self,
        script_id: str,
        context: 'ScriptContext',
    ) -> Optional[ScriptResponse]:
        """
        生成响应
        
        Args:
            script_id: 脚本 ID
            context: 脚本上下文
            
        Returns:
            响应结果，失败时返回 None
        """
        pass
    
    @abstractmethod
    def reload_script(self, script_id: str) -> bool:
        """
        热重载脚本
        
        Args:
            script_id: 脚本 ID
            
        Returns:
            是否重载成功
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        pass
    
    def load_scripts_from_directory(self, directory: Path) -> int:
        """
        从目录批量加载脚本
        
        Args:
            directory: 脚本目录
            
        Returns:
            成功加载的脚本数量
        """
        if not directory.exists():
            return 0
        
        count = 0
        extension = self._get_extension()
        for script_file in directory.glob(f"*.{extension}"):
            config = self._create_config_from_file(script_file)
            if config and self.load_script(config):
                count += 1
        
        return count
    
    @abstractmethod
    def _get_extension(self) -> str:
        """获取脚本文件扩展名"""
        pass
    
    @abstractmethod
    def _create_config_from_file(self, file_path: Path) -> Optional[ScriptConfig]:
        """
        从文件创建脚本配置
        
        Args:
            file_path: 文件路径
            
        Returns:
            脚本配置，失败时返回 None
        """
        pass
    
    def _increment_stat(self, stat_name: str) -> None:
        """增加统计计数"""
        if stat_name in self._stats:
            self._stats[stat_name] += 1
    
    def get_script_ids(self) -> List[str]:
        """获取所有已加载的脚本 ID"""
        return list(self.scripts.keys())
    
    def get_script_config(self, script_id: str) -> Optional[ScriptConfig]:
        """获取脚本配置"""
        return self.scripts.get(script_id)
    
    def enable_script(self, script_id: str) -> bool:
        """启用脚本"""
        if script_id in self.scripts:
            self.scripts[script_id].enabled = True
            return True
        return False
    
    def disable_script(self, script_id: str) -> bool:
        """禁用脚本"""
        if script_id in self.scripts:
            self.scripts[script_id].enabled = False
            return True
        return False
    
    def clear_stats(self) -> None:
        """清空统计"""
        self._stats = {
            'load_count': 0,
            'match_count': 0,
            'error_count': 0,
        }
