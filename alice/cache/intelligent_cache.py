#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能缓存模块

提供 LRU 缓存策略，减少重复计算。
"""

import logging
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IntelligentCache:
    """
    智能缓存
    
    功能:
    - LRU 缓存策略
    - TTL 过期机制
    - 缓存统计
    - 自动清理
    
    使用场景:
    - 语义分析结果缓存
    - 响应结果缓存
    - 实体提取结果缓存
    """

    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认 TTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl  # 默认 1 小时过期
        
        # 使用 OrderedDict 实现 LRU
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在或已过期返回 None
        """
        if key not in self._cache:
            self._misses += 1
            return None
        
        item = self._cache[key]
        
        # 检查是否过期
        if self._is_expired(item):
            self._remove(key)
            self._misses += 1
            return None
        
        # 移动到末尾（最近使用）
        self._cache.move_to_end(key)
        self._hits += 1
        
        return item["value"]

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        设置缓存项
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值
        """
        # 如果已存在，先删除
        if key in self._cache:
            self._remove(key)
        
        # 如果缓存已满，删除最旧的
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        # 添加新项
        self._cache[key] = {
            "value": value,
            "created_at": datetime.now(),
            "ttl": ttl if ttl is not None else self.default_ttl,
        }

    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """
        检查缓存项是否过期
        
        Args:
            item: 缓存项
            
        Returns:
            是否过期
        """
        ttl = item.get("ttl", self.default_ttl)
        if ttl <= 0:
            return False  # 永不过期
        
        age = (datetime.now() - item["created_at"]).total_seconds()
        return age > ttl

    def _remove(self, key: str) -> None:
        """
        删除缓存项
        
        Args:
            key: 缓存键
        """
        if key in self._cache:
            del self._cache[key]

    def _evict_oldest(self) -> None:
        """删除最旧的缓存项"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._remove(oldest_key)
            self._evictions += 1
            logger.debug(f"缓存已满，删除最旧项：{oldest_key}")

    def contains(self, key: str) -> bool:
        """
        检查缓存键是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        return self.get(key) is not None

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("缓存已清空")

    def cleanup_expired(self) -> int:
        """
        清理过期缓存项
        
        Returns:
            清理的数量
        """
        expired_keys = [
            key for key, item in self._cache.items()
            if self._is_expired(item)
        ]
        
        for key in expired_keys:
            self._remove(key)
        
        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存项")
        
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = self._hits + self._misses
        hit_rate = (
            self._hits / total_requests * 100
            if total_requests > 0
            else 0.0
        )
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": f"{hit_rate:.2f}%",
        }

    def get_analysis_cache(self, text: str) -> Optional[Dict]:
        """
        获取分析结果缓存
        
        Args:
            text: 原始文本
            
        Returns:
            缓存的分析结果
        """
        key = self._generate_analysis_key(text)
        return self.get(key)

    def cache_analysis(
        self,
        text: str,
        analysis: Dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        缓存分析结果
        
        Args:
            text: 原始文本
            analysis: 分析结果
            ttl: 过期时间（秒）
        """
        key = self._generate_analysis_key(text)
        self.set(key, analysis, ttl=ttl)

    def _generate_analysis_key(self, text: str) -> str:
        """
        生成分析结果缓存键
        
        Args:
            text: 原始文本
            
        Returns:
            缓存键
        """
        import hashlib
        return f"analysis:{hashlib.md5(text.encode('utf-8')).hexdigest()}"

    def __len__(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def __repr__(self) -> str:
        return f"IntelligentCache(size={len(self._cache)}/{self.max_size})"
