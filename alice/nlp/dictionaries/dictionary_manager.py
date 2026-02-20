#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词典管理器 - 从 YAML 加载词典
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml

logger = logging.getLogger(__name__)


class DictionaryManager:
    """词典管理器"""
    
    def __init__(self, dictionary_dir: Optional[Path] = None):
        """
        初始化
        
        Args:
            dictionary_dir: 词典目录，None 则使用默认路径
        """
        if dictionary_dir is None:
            from alice.config import SCRIPTS_DIR
            dictionary_dir = SCRIPTS_DIR / "dictionaries"
        
        self.dictionary_dir = dictionary_dir
        self._dictionaries: Dict[str, Dict[str, Any]] = {}
    
    def load(self, name: str) -> Dict[str, Any]:
        """
        加载词典
        
        Args:
            name: 词典名称（不含.yaml 后缀）
        
        Returns:
            词典内容
        """
        if name in self._dictionaries:
            return self._dictionaries[name]
        
        file_path = self.dictionary_dir / f"{name}.yaml"
        
        if not file_path.exists():
            logger.warning(f"词典文件不存在：{file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            self._dictionaries[name] = data
            return data
        except Exception as e:
            logger.error(f"加载词典失败：{name}, 错误：{e}")
            return {}
    
    def get(self, name: str, key: str, default: Any = None) -> Any:
        """获取词典中的值"""
        data = self.load(name)
        return data.get(key, default)
    
    def get_list(self, name: str, key: str) -> List[str]:
        """获取词典中的列表"""
        data = self.load(name)
        result = data.get(key, [])
        return result if isinstance(result, list) else []
    
    def get_dict(self, name: str, key: str) -> Dict[str, Any]:
        """获取词典中的字典"""
        data = self.load(name)
        result = data.get(key, {})
        return result if isinstance(result, dict) else {}
