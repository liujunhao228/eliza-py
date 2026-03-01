"""
匹配结果管理器

负责管理匹配结果，支持：
- 存储匹配结果
- 获取安全结果（过滤敏感字段）
- 清除结果
"""

import asyncio
from typing import Dict, Optional
from loguru import logger

from .types import UserId, MatchResultData, SafeMatchResult


class ResultManager:
    """
    匹配结果管理器

    负责存储和管理匹配结果，提供安全的结果访问接口。

    线程安全:
    - 使用 asyncio.Lock 保护共享状态

    Attributes:
        _results: 匹配结果字典
        _lock: 异步锁
    """

    def __init__(self):
        """初始化结果管理器"""
        self._results: Dict[UserId, MatchResultData] = {}
        self._lock = asyncio.Lock()

    async def store(
        self,
        user_id: UserId,
        result: MatchResultData
    ) -> None:
        """
        存储匹配结果

        Args:
            user_id: 用户 ID
            result: 匹配结果数据
        """
        async with self._lock:
            old_result = self._results.get(user_id)
            if old_result:
                logger.debug(f"覆盖用户 {user_id} 的旧匹配结果")
            self._results[user_id] = result
            logger.debug(f"存储用户 {user_id} 的匹配结果：session_id={result.session_id}")

    async def store_batch(
        self,
        results: Dict[UserId, MatchResultData]
    ) -> None:
        """
        批量存储匹配结果

        Args:
            results: 用户 ID 到结果的映射
        """
        async with self._lock:
            self._results.update(results)
            logger.debug(f"批量存储 {len(results)} 个匹配结果")

    async def get(self, user_id: UserId) -> Optional[MatchResultData]:
        """
        获取匹配结果（内部使用，包含完整信息）

        Args:
            user_id: 用户 ID

        Returns:
            匹配结果数据，如果不存在则返回 None
        """
        async with self._lock:
            result = self._results.get(user_id)
            if result:
                logger.debug(f"获取用户 {user_id} 的内部匹配结果")
            return result

    async def get_safe(self, user_id: UserId) -> Optional[SafeMatchResult]:
        """
        获取安全匹配结果（返回给前端）

        过滤敏感字段，仅返回：
        - session_id
        - opponent_type (固定为 "opponent")
        - match_duration_ms

        Args:
            user_id: 用户 ID

        Returns:
            安全匹配结果，如果不存在则返回 None
        """
        async with self._lock:
            result = self._results.get(user_id)
            if not result:
                return None

            logger.debug(f"获取用户 {user_id} 的安全匹配结果")
            return self._to_safe_result(result)

    async def get_batch_safe(
        self,
        user_ids: list[UserId]
    ) -> Dict[UserId, Optional[SafeMatchResult]]:
        """
        批量获取安全匹配结果

        Args:
            user_ids: 用户 ID 列表

        Returns:
            用户 ID 到安全结果的映射
        """
        async with self._lock:
            return {
                user_id: self._to_safe_result(result) if result else None
                for user_id, result in [
                    (uid, self._results.get(uid)) for uid in user_ids
                ]
            }

    async def clear(self, user_id: UserId) -> None:
        """
        清除用户的匹配结果

        Args:
            user_id: 用户 ID
        """
        async with self._lock:
            if user_id in self._results:
                del self._results[user_id]
                logger.debug(f"清除用户 {user_id} 的匹配结果")

    async def clear_batch(self, user_ids: list[UserId]) -> None:
        """
        批量清除匹配结果

        Args:
            user_ids: 用户 ID 列表
        """
        async with self._lock:
            for user_id in user_ids:
                if user_id in self._results:
                    del self._results[user_id]
            logger.debug(f"批量清除 {len(user_ids)} 个匹配结果")

    async def clear_all(self) -> None:
        """清空所有匹配结果"""
        async with self._lock:
            self._results.clear()
        logger.info("所有匹配结果已清空")

    async def exists(self, user_id: UserId) -> bool:
        """
        检查用户是否有匹配结果

        Args:
            user_id: 用户 ID

        Returns:
            是否存在匹配结果
        """
        async with self._lock:
            return user_id in self._results

    async def count(self) -> int:
        """
        获取结果数量

        Returns:
            结果数量
        """
        async with self._lock:
            return len(self._results)

    @staticmethod
    def _to_safe_result(result: MatchResultData) -> SafeMatchResult:
        """
        将内部结果转换为安全结果（过滤敏感字段）

        Args:
            result: 内部匹配结果

        Returns:
            安全匹配结果
        """
        return SafeMatchResult(
            session_id=result.session_id,
            opponent_type="opponent",  # 统一返回 opponent，隐藏真实身份
            match_duration_ms=result.match_duration_ms,
        )
