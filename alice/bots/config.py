#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 配置数据类

定义单个 Bot 实例的配置结构
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BotConfig:
    """
    Bot 实例配置

    Attributes:
        name: Bot 名称（唯一标识）
        display_name: 显示名称
        description: Bot 描述
        script_file: 脚本文件路径
        rules_file: 规则文件路径
        enable_ltp: 是否启用 LTP
        enable_ner: 是否启用 NER
        enable_plugins: 是否启用插件
        cache_size: 缓存大小
        enable_logging: 是否启用日志
        enable_hot_reload: 是否启用热重载
        hot_reload_mode: 热重载模式 ("auto" 或 "manual")
        custom_settings: 自定义配置
    """
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    
    # 脚本配置
    script_file: Optional[str] = None
    rules_file: Optional[str] = None
    
    # NLP 配置
    enable_ltp: bool = True
    enable_ner: bool = True
    
    # 功能开关
    enable_plugins: bool = True
    enable_logging: bool = True
    enable_hot_reload: bool = True
    hot_reload_mode: str = "auto"
    
    # 性能配置
    cache_size: int = 100
    
    # 自定义配置
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """后处理：设置默认值"""
        if self.display_name is None:
            self.display_name = self.name.capitalize()
    
    def resolve_path(self, path: Optional[str]) -> Optional[Path]:
        """
        解析相对路径为绝对路径
        
        Args:
            path: 文件路径（可以是相对路径或绝对路径）
            
        Returns:
            解析后的 Path 对象，如果 path 为 None 则返回 None
        """
        if path is None:
            return None
        
        p = Path(path)
        if p.is_absolute():
            return p
        
        # 相对于项目根目录
        project_root = Path(__file__).parent.parent.parent
        return project_root / p
