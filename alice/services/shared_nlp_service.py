"""
共享NLP服务，单例模式
统一管理所有NLP资源，避免重复加载
"""

import threading
from typing import Dict, Any, Optional
from functools import lru_cache
import jieba
from alice.nlp.engines.jieba_engine import JiebaEngine
from alice.nlp.engines.ltp_engine import LTP4Engine  # 如果启用LTP


class SharedNLPService:
    """
    共享NLP服务，单例模式
    统一管理所有NLP资源，避免重复加载
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._jieba_engine = JiebaEngine()
        self._ltp_engine = None  # 可选加载
        self._cache = {}
        self._cache_lock = threading.RLock()
    
    def initialize_ltp(self, enable_ltp: bool = False):
        """可选初始化LTP引擎"""
        if enable_ltp:
            self._ltp_engine = LTP4Engine()
    
    def tokenize(self, text: str) -> list:
        """分词"""
        return self._jieba_engine.tokenize(text)
    
    def analyze_syntax(self, text: str) -> Dict[str, Any]:
        """句法分析 - 如果启用了LTP"""
        if self._ltp_engine:
            return self._ltp_engine.analyze_syntax(text)
        else:
            # 使用jieba作为替代
            return {"tokens": self.tokenize(text)}
    
    def extract_entities(self, text: str) -> list:
        """实体抽取 - 如果启用了LTP"""
        if self._ltp_engine:
            return self._ltp_engine.extract_entities(text)
        else:
            # 使用jieba + 简单规则作为替代
            return []
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """获取缓存结果"""
        with self._cache_lock:
            return self._cache.get(key)
    
    def set_cached_result(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存结果"""
        with self._cache_lock:
            self._cache[key] = value