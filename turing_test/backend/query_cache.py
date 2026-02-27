#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查询缓存模块

为 SQLAlchemy 异步查询提供缓存支持，减少重复数据库查询。

特性:
- 基于查询哈希的自动缓存
- TTL 过期机制
- 支持手动缓存失效
- 统计命中率

使用示例:
    cache = QueryCache(max_size=1000, default_ttl=300)

    # 装饰器方式
    @cache_query(cache, ttl=300)
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    # 手动缓存
    key = cache.generate_key("get_user", user_id=123)
    cached = await cache.get(key)
    if cached:
        return cached

    result = await db.execute(...)
    await cache.set(key, result)
    return result
"""

import hashlib
import json
import time
import logging
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from functools import wraps
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from alice.cache.lru_cache import LRUCache

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total * 100 if total > 0 else 0.0


class QueryCache:
    """
    查询缓存

    用于缓存数据库查询结果，减少重复查询。
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化查询缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认 TTL（秒）
        """
        self.cache = LRUCache[Dict[str, Any]](max_size=max_size, default_ttl=default_ttl)
        self.default_ttl = default_ttl
        self.stats = CacheStats()

    def generate_key(self, query_name: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            query_name: 查询名称
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            MD5 哈希的缓存键
        """
        key_data = {
            'query': query_name,
            'args': args,
            'kwargs': sorted(kwargs.items()),
        }
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        data = self.cache.get(key)
        if data is not None:
            self.stats.hits += 1
            logger.debug(f"查询缓存命中：{key[:20]}...")
            return data.get('value')

        self.stats.misses += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        data = {
            'value': value,
            'cached_at': time.time(),
            'ttl': ttl if ttl is not None else self.default_ttl,
        }
        self.cache.set(key, data, ttl=ttl)
        logger.debug(f"查询缓存已设置：{key[:20]}...")

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        return self.cache.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        根据模式删除缓存

        Args:
            pattern: 缓存键前缀模式

        Returns:
            删除的数量
        """
        deleted_count = 0
        for key in list(self.cache.get_all_keys()):
            if key.startswith(pattern):
                if self.cache.delete(key):
                    deleted_count += 1

        if deleted_count > 0:
            self.stats.evictions += deleted_count
            logger.info(f"已删除 {deleted_count} 个匹配 '{pattern}' 的缓存")

        return deleted_count

    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
        logger.info("查询缓存已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'size': len(self.cache),
            'max_size': self.cache.max_size,
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'evictions': self.stats.evictions,
            'hit_rate': f"{self.stats.hit_rate:.2f}%",
            'cache_stats': self.cache.get_stats(),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self.stats = CacheStats()


def cache_query(
    cache: QueryCache,
    ttl: Optional[int] = None,
    key_prefix: str = "",
):
    """
    查询缓存装饰器

    Usage:
        cache = QueryCache()

        @cache_query(cache, ttl=300, key_prefix="user")
        async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 提取参数
            # 假设第一个参数是 db/session，其余为查询参数
            if args:
                # 跳过 self 和 db 参数
                start_idx = 1
                if len(args) > 1 and isinstance(args[1], AsyncSession):
                    start_idx = 2

                query_args = args[start_idx:]
            else:
                query_args = ()

            # 生成缓存键
            cache_key = cache.generate_key(
                f"{key_prefix}_{func.__name__}",
                *query_args,
                **{k: v for k, v in kwargs.items() if k != 'db'},
            )

            # 尝试从缓存获取
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # 执行查询
            result = await func(*args, **kwargs)

            # 缓存结果（如果非 None）
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


# =============================================================================
# 预定义查询缓存
# =============================================================================

# 全局查询缓存实例
# - 用户数据缓存：1000 条目，5 分钟 TTL
# - 配置数据缓存：500 条目，30 分钟 TTL
# - 统计数据缓存：200 条目，1 分钟 TTL

user_query_cache = QueryCache(max_size=1000, default_ttl=300)
config_query_cache = QueryCache(max_size=500, default_ttl=1800)
stats_query_cache = QueryCache(max_size=200, default_ttl=60)


async def get_all_cache_stats() -> Dict[str, Any]:
    """获取所有缓存统计"""
    return {
        'user_query': user_query_cache.get_stats(),
        'config_query': config_query_cache.get_stats(),
        'stats_query': stats_query_cache.get_stats(),
    }


async def clear_all_caches() -> None:
    """清空所有缓存"""
    user_query_cache.clear()
    config_query_cache.clear()
    stats_query_cache.clear()
    logger.info("所有查询缓存已清空")
