"""
匹配队列管理器

负责管理等待队列，支持：
- 加入/移除用户
- 队列快照（供算法使用）
- 超时清理
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Awaitable
from loguru import logger

from .types import UserId, MatchRequest, QueueSnapshot, MatchType


class MatchQueue:
    """
    匹配队列管理器

    线程安全:
    - 使用 asyncio.Lock 保护共享状态

    Attributes:
        _queue: 等待队列
        _lock: 异步锁
    """

    def __init__(self):
        """初始化队列管理器"""
        self._queue: Dict[UserId, MatchRequest] = {}
        self._lock = asyncio.Lock()

    async def add(self, request: MatchRequest) -> bool:
        """
        加入队列

        Args:
            request: 匹配请求

        Returns:
            是否成功加入（如果用户已在队列中则返回 False）
        """
        async with self._lock:
            if request.user_id in self._queue:
                logger.warning(f"用户 {request.user_id} 已在队列中")
                return False
            self._queue[request.user_id] = request
            logger.info(f"用户 {request.user_id} 加入等待队列")
            return True

    async def remove(self, user_id: UserId) -> bool:
        """
        从队列中移除用户

        Args:
            user_id: 用户 ID

        Returns:
            是否成功移除（如果用户不在队列中则返回 False）
        """
        async with self._lock:
            if user_id not in self._queue:
                return False
            del self._queue[user_id]
            logger.info(f"用户 {user_id} 离开等待队列")
            return True

    async def contains(self, user_id: UserId) -> bool:
        """
        检查用户是否在队列中

        Args:
            user_id: 用户 ID

        Returns:
            是否在队列中
        """
        async with self._lock:
            return user_id in self._queue

    async def get_request(self, user_id: UserId) -> Optional[MatchRequest]:
        """
        获取用户的匹配请求

        Args:
            user_id: 用户 ID

        Returns:
            匹配请求，如果用户不在队列中则返回 None
        """
        async with self._lock:
            return self._queue.get(user_id)

    async def get_snapshot(self) -> QueueSnapshot:
        """
        获取队列快照（供算法使用）

        创建队列的只读快照，避免算法修改原始数据。

        Returns:
            队列快照
        """
        async with self._lock:
            # 创建浅拷贝快照
            return QueueSnapshot(
                requests=dict(self._queue),
                timestamp=time.time()
            )

    async def size(self) -> int:
        """
        获取队列大小

        Returns:
            队列中的用户数量
        """
        async with self._lock:
            return len(self._queue)

    async def human_count(self) -> int:
        """
        获取等待真人匹配的用户数量

        Returns:
            等待真人匹配的用户数量
        """
        async with self._lock:
            return sum(
                1 for req in self._queue.values()
                if req.match_type == MatchType.HUMAN
            )

    async def cleanup_expired(
        self,
        timeout_seconds: float,
        on_expired: Callable[[UserId, MatchRequest], Awaitable[None]]
    ) -> List[UserId]:
        """
        清理超时的匹配请求

        Args:
            timeout_seconds: 超时时间（秒）
            on_expired: 超时回调函数 (异步)

        Returns:
            被清理的用户 ID 列表
        """
        now = time.time()
        expired_users: List[UserId] = []

        # 先找出超时用户（在锁内）
        async with self._lock:
            for user_id, request in list(self._queue.items()):
                if (now - request.timestamp) > timeout_seconds:
                    expired_users.append(user_id)

        # 处理超时用户（在锁外，避免长时间持有锁）
        for user_id in expired_users:
            async with self._lock:
                # 再次检查，避免已被其他操作移除
                if user_id in self._queue:
                    request = self._queue[user_id]
                    del self._queue[user_id]
                    # 调用回调
                    await on_expired(user_id, request)
                    logger.info(f"匹配超时：user_id={user_id}")

        return expired_users

    async def clear(self) -> None:
        """清空队列"""
        async with self._lock:
            self._queue.clear()
        logger.info("匹配队列已清空")
