#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 缓存支持模块

提供可选的 Redis 缓存集成，用于分布式缓存和更大数据量的场景。

特性:
- 异步 Redis 操作
- 自动序列化/反序列化
- 连接池管理
- 优雅降级（Redis 不可用时自动降级到内存缓存）

安装依赖:
    pip install redis asyncredis

使用示例:
    # 配置 Redis
    redis_cache = RedisCache(
        host="localhost",
        port=6379,
        db=0,
        password=None,
    )

    # 设置缓存
    await redis_cache.set("key", "value", ttl=300)

    # 获取缓存
    value = await redis_cache.get("key")
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 尝试导入 redis 库
try:
    import redis.asyncio as aioredis
    from redis.asyncio import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis 库未安装，RedisCache 将使用降级模式")

# 导入内存缓存作为降级方案
from alice.cache.lru_cache import LRUCache


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 50
    decode_responses: bool = False
    ssl: bool = False
    ssl_cert_reqs: Optional[str] = None


class RedisCache:
    """
    Redis 缓存

    支持：
    - 字符串、数字、列表、字典等类型的自动序列化
    - TTL 过期
    - 连接池管理
    - 优雅降级（Redis 不可用时使用内存缓存）
    """

    def __init__(
        self,
        config: Optional[RedisConfig] = None,
        fallback_to_memory: bool = True,
        memory_cache_size: int = 10000,
    ):
        """
        初始化 Redis 缓存

        Args:
            config: Redis 配置
            fallback_to_memory: Redis 不可用时是否降级到内存缓存
            memory_cache_size: 降级内存缓存的大小
        """
        self.config = config or RedisConfig()
        self.fallback_to_memory = fallback_to_memory
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None
        self._memory_cache: Optional[LRUCache[Dict[str, Any]]] = None
        self._connected = False
        self._stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'fallback_hits': 0,
        }

        if fallback_to_memory:
            self._memory_cache = LRUCache[Dict[str, Any]](
                max_size=memory_cache_size,
                default_ttl=3600,
            )

    async def connect(self) -> bool:
        """
        连接到 Redis

        Returns:
            是否连接成功
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis 库未安装，使用内存缓存降级")
            return False

        try:
            # 创建连接池
            self._pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                username=self.config.username,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                max_connections=self.config.max_connections,
                decode_responses=self.config.decode_responses,
                ssl=self.config.ssl,
            )

            # 创建 Redis 客户端
            self._redis = aioredis.Redis(connection_pool=self._pool)

            # 测试连接
            await self._redis.ping()
            self._connected = True

            logger.info(
                f"Redis 已连接：{self.config.host}:{self.config.port}"
            )
            return True

        except Exception as e:
            logger.warning(f"Redis 连接失败：{e}，使用降级模式")
            self._connected = False
            return False

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis 连接已关闭")

        if self._pool:
            await self._pool.disconnect()

        self._connected = False

    def _serialize(self, value: Any) -> str:
        """序列化值"""
        return json.dumps(value, ensure_ascii=False, default=str)

    def _deserialize(self, value: Optional[str]) -> Optional[Any]:
        """反序列化值"""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        # 优先尝试 Redis
        if self._connected and self._redis:
            try:
                value = await self._redis.get(key)
                if value is not None:
                    self._stats['hits'] += 1
                    return self._deserialize(value)

                self._stats['misses'] += 1

            except Exception as e:
                logger.error(f"Redis GET 错误：{e}")
                self._stats['errors'] += 1

        # 降级到内存缓存
        if self.fallback_to_memory and self._memory_cache:
            value = self._memory_cache.get(key)
            if value is not None:
                self._stats['fallback_hits'] += 1
                return value.get('value')

        self._stats['misses'] += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        serialized = self._serialize(value)

        # 尝试 Redis
        if self._connected and self._redis:
            try:
                if ttl:
                    await self._redis.setex(key, ttl, serialized)
                else:
                    await self._redis.set(key, serialized)
                return True

            except Exception as e:
                logger.error(f"Redis SET 错误：{e}")
                self._stats['errors'] += 1

        # 降级到内存缓存
        if self.fallback_to_memory and self._memory_cache:
            self._memory_cache.set(
                key,
                {'value': value, 'cached_at': time.time()},
                ttl=ttl,
            )
            return True

        return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        deleted = False

        # Redis 删除
        if self._connected and self._redis:
            try:
                result = await self._redis.delete(key)
                deleted = result > 0
            except Exception as e:
                logger.error(f"Redis DELETE 错误：{e}")

        # 内存缓存删除
        if self._memory_cache:
            self._memory_cache.delete(key)

        return deleted

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self._connected and self._redis:
            try:
                return await self._redis.exists(key) > 0
            except Exception:
                pass

        if self._memory_cache:
            return self._memory_cache.contains(key)

        return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        result = {}

        if self._connected and self._redis:
            try:
                values = await self._redis.mget(keys)
                for key, value in zip(keys, values):
                    if value is not None:
                        result[key] = self._deserialize(value)
                        self._stats['hits'] += 1
                    else:
                        self._stats['misses'] += 1
                return result
            except Exception as e:
                logger.error(f"Redis MGET 错误：{e}")

        # 降级到内存
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value

        return result

    async def set_many(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """批量设置"""
        if self._connected and self._redis:
            try:
                pipeline = self._redis.pipeline()
                for key, value in data.items():
                    serialized = self._serialize(value)
                    if ttl:
                        pipeline.setex(key, ttl, serialized)
                    else:
                        pipeline.set(key, serialized)
                await pipeline.execute()
                return True
            except Exception as e:
                logger.error(f"Redis MSET 错误：{e}")

        # 降级到内存
        if self._memory_cache:
            for key, value in data.items():
                self._memory_cache.set(
                    key,
                    {'value': value, 'cached_at': time.time()},
                    ttl=ttl,
                )
            return True

        return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的键

        Args:
            pattern: 键模式（支持通配符 *）

        Returns:
            删除的数量
        """
        deleted_count = 0

        if self._connected and self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted = await self._redis.delete(*keys)
                        deleted_count += deleted
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error(f"Redis SCAN 错误：{e}")

        return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total * 100 if total > 0 else 0.0

        return {
            'connected': self._connected,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'errors': self._stats['errors'],
            'fallback_hits': self._stats.get('fallback_hits', 0),
            'hit_rate': f"{hit_rate:.2f}%",
            'memory_cache_stats': (
                self._memory_cache.get_stats() if self._memory_cache else None
            ),
        }

    @property
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self._connected or self.fallback_to_memory


# =============================================================================
# 全局 Redis 缓存实例
# =============================================================================

# 默认 Redis 缓存（自动降级到内存缓存）
default_redis_cache = RedisCache(
    config=RedisConfig(
        host="localhost",
        port=6379,
        db=0,
    ),
    fallback_to_memory=True,
    memory_cache_size=10000,
)


async def get_redis_cache() -> RedisCache:
    """获取 Redis 缓存实例（用于依赖注入）"""
    if not default_redis_cache.is_available:
        await default_redis_cache.connect()
    return default_redis_cache


async def shutdown_redis_cache() -> None:
    """关闭 Redis 缓存"""
    await default_redis_cache.close()
