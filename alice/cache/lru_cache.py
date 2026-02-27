#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能 LRU 缓存实现

基于 OrderedDict 实现线程安全的 LRU 缓存，支持：
- TTL 过期
- 最大容量限制
- 访问频率统计
- 批量操作
"""

import threading
import time
import hashlib
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
import json

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[int] = None  # 秒，None 表示永不过期

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None or self.ttl <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl

    def touch(self):
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache(Generic[T]):
    """
    线程安全的 LRU 缓存

    特性:
    - O(1) 时间复杂度的 get/set 操作
    - 自动 TTL 过期
    - 容量限制和自动淘汰
    - 访问频率统计
    - 批量操作支持

    使用示例:
        cache = LRUCache(max_size=1000, default_ttl=3600)
        cache.set("key", "value")
        value = cache.get("key")
    """

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = 3600):
        """
        初始化 LRU 缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认 TTL（秒），None 表示永不过期
        """
        self.max_size = max_size
        self.default_ttl = default_ttl

        # 使用 OrderedDict 实现 O(1) 的 LRU 淘汰
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        获取缓存值

        Args:
            key: 缓存键
            default: 默认值（未找到时返回）

        Returns:
            缓存值，不存在或已过期返回 default
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                self._remove(key)
                self._expirations += 1
                self._misses += 1
                return default

            # 移动到末尾（最近使用）并更新访问统计
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1

            return entry.value

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值
        """
        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                self._remove(key)

            # 如果缓存已满，淘汰最旧的
            if len(self._cache) >= self.max_size:
                self._evict_oldest()

            # 添加新条目
            self._cache[key] = CacheEntry(
                value=value,
                ttl=ttl if ttl is not None else self.default_ttl,
            )

    def delete(self, key: str) -> bool:
        """
        删除缓存项

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            return self._remove(key)

    def contains(self, key: str) -> bool:
        """
        检查缓存键是否存在且未过期

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired():
                self._remove(key)
                self._expirations += 1
                return False

            return True

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        清理所有过期条目

        Returns:
            清理的数量
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                self._remove(key)
                self._expirations += 1

            return len(expired_keys)

    def size(self) -> int:
        """获取当前缓存大小"""
        with self._lock:
            return len(self._cache)

    def is_full(self) -> bool:
        """检查缓存是否已满"""
        with self._lock:
            return len(self._cache) >= self.max_size

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (
                self._hits / total_requests * 100
                if total_requests > 0
                else 0.0
            )

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "usage_percent": len(self._cache) / self.max_size * 100,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
                "hit_rate": f"{hit_rate:.2f}%",
            }

    def get_all_keys(self) -> List[str]:
        """获取所有缓存键"""
        with self._lock:
            return list(self._cache.keys())

    def get_all_values(self) -> List[T]:
        """获取所有缓存值（未过期的）"""
        with self._lock:
            return [
                entry.value for entry in self._cache.values()
                if not entry.is_expired()
            ]

    def get_items(self) -> List[Tuple[str, T]]:
        """获取所有缓存项"""
        with self._lock:
            return [
                (key, entry.value)
                for key, entry in self._cache.items()
                if not entry.is_expired()
            ]

    def _remove(self, key: str) -> bool:
        """删除缓存项（内部方法，需要持有锁）"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def _evict_oldest(self) -> None:
        """淘汰最旧的条目（内部方法，需要持有锁）"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._remove(oldest_key)
            self._evictions += 1

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expirations = 0

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        with self._lock:
            return {
                "entries": {
                    key: {
                        "value": entry.value,
                        "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                        "last_accessed": datetime.fromtimestamp(entry.last_accessed).isoformat(),
                        "access_count": entry.access_count,
                        "ttl": entry.ttl,
                    }
                    for key, entry in self._cache.items()
                    if not entry.is_expired()
                },
                "stats": self.get_stats(),
            }

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __repr__(self) -> str:
        return f"LRUCache(size={len(self._cache)}/{self.max_size})"


class MultiLevelCache(Generic[T]):
    """
    多级缓存

    结合 L1（内存）和 L2（可选的 Redis/磁盘）缓存，
    提供更高效的缓存策略。

    使用示例:
        cache = MultiLevelCache(l1_max_size=1000, l1_ttl=300)
        cache.set("key", "value")
        value = cache.get("key")
    """

    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl: Optional[int] = 300,
        enable_l2: bool = False,
    ):
        """
        初始化多级缓存

        Args:
            l1_max_size: L1 缓存最大大小
            l1_ttl: L1 缓存 TTL（秒）
            enable_l2: 是否启用 L2 缓存（预留接口）
        """
        self.l1_cache = LRUCache[T](max_size=l1_max_size, default_ttl=l1_ttl)
        self.enable_l2 = enable_l2
        self._l2_cache: Optional[Dict[str, T]] = None  # 预留 L2 缓存

        # 统计
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        获取缓存值（优先 L1，未命中时查 L2）

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值
        """
        # 先查 L1
        value = self.l1_cache.get(key)
        if value is not None:
            self._l1_hits += 1
            return value

        # L1 未命中，查 L2（如果启用）
        if self.enable_l2 and self._l2_cache and key in self._l2_cache:
            value = self._l2_cache[key]
            self._l2_hits += 1
            # 回写到 L1
            self.l1_cache.set(key, value)
            return value

        self._misses += 1
        return default

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间
        """
        # 写入 L1
        self.l1_cache.set(key, value, ttl=ttl)

        # 如果启用 L2，也写入
        if self.enable_l2:
            if self._l2_cache is None:
                self._l2_cache = {}
            self._l2_cache[key] = value

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        deleted = self.l1_cache.delete(key)
        if self.enable_l2 and self._l2_cache and key in self._l2_cache:
            del self._l2_cache[key]
        return deleted

    def clear(self) -> None:
        """清空缓存"""
        self.l1_cache.clear()
        if self.enable_l2 and self._l2_cache:
            self._l2_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._l1_hits + self._l2_hits + self._misses
        return {
            "l1_hits": self._l1_hits,
            "l2_hits": self._l2_hits,
            "misses": self._misses,
            "l1_hit_rate": f"{self._l1_hits / total * 100:.2f}%" if total > 0 else "0.00%",
            "overall_hit_rate": f"{(self._l1_hits + self._l2_hits) / total * 100:.2f}%" if total > 0 else "0.00%",
            "l1_cache_stats": self.l1_cache.get_stats(),
        }


def generate_cache_key(*args, **kwargs) -> str:
    """
    生成缓存键

    Args:
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        MD5 哈希的缓存键
    """
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()),
    }
    key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def cache_result(cache: LRUCache, ttl: Optional[int] = None):
    """
    缓存函数结果装饰器

    Usage:
        cache = LRUCache(max_size=1000)

        @cache_result(cache, ttl=3600)
        def expensive_function(text: str) -> str:
            # 耗时操作
            return result
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = generate_cache_key(*args, **kwargs)

            # 尝试从缓存获取
            cached = cache.get(key)
            if cached is not None:
                return cached

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
