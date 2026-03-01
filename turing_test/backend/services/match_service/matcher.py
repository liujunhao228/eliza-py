"""
匹配协调器

核心业务逻辑协调器，负责：
- 执行完整匹配流程
- 协调各组件（队列、Bot 池、结果管理器）
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict
from loguru import logger

from .config import MatchConfig
from .queue import MatchQueue
from .result_manager import ResultManager
from .algorithm import MatchAlgorithm, ProbabilityAlgorithm
from .pools import BotPool, HoneypotPool, BotConfig, HoneypotBotConfig
from .types import (
    UserId, WebsocketRef, MatchType, MatchRequest,
    MatchResultData, SafeMatchResult,
)


class MatchCoordinator:
    """
    匹配协调器

    核心职责：
    1. 执行完整匹配流程
    2. 协调队列、Bot 池、结果管理器
    3. 处理真人匹配和 Bot 匹配逻辑

    Attributes:
        config: 匹配配置
        algorithm: 匹配算法
        queue: 队列管理器
        bot_pool: 普通 Bot 池
        honeypot_pool: 钓鱼 Bot 池
        result_manager: 结果管理器
    """

    def __init__(
        self,
        config: MatchConfig,
        algorithm: Optional[MatchAlgorithm] = None,
        queue: Optional[MatchQueue] = None,
        bot_pool: Optional[BotPool] = None,
        honeypot_pool: Optional[HoneypotPool] = None,
        result_manager: Optional[ResultManager] = None,
    ):
        """
        初始化匹配协调器

        Args:
            config: 匹配配置
            algorithm: 匹配算法（默认使用 ProbabilityAlgorithm）
            queue: 队列管理器（默认创建新实例）
            bot_pool: 普通 Bot 池（默认创建新实例）
            honeypot_pool: 钓鱼 Bot 池（默认创建新实例）
            result_manager: 结果管理器（默认创建新实例）
        """
        self.config = config
        self.algorithm = algorithm or ProbabilityAlgorithm()
        self.queue = queue or MatchQueue()
        self.bot_pool = bot_pool or BotPool()
        self.honeypot_pool = honeypot_pool or HoneypotPool()
        self.result_manager = result_manager or ResultManager()

        # 用户匹配锁：防止同一用户并发匹配
        self._user_locks: Dict[UserId, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # 保护 _user_locks 字典

        # 统计信息
        self._stats = {
            'total_matches': 0,
            'human_matches': 0,
            'bot_matches': 0,
            'honeypot_matches': 0,
            'timeout_fallbacks': 0,
        }

    async def match_user(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int = 100
    ) -> SafeMatchResult:
        """
        执行完整匹配流程

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分

        Returns:
            安全匹配结果

        Raises:
            ValueError: 用户已在队列中或匹配正在进行中
            RuntimeError: 匹配失败
        """
        # 获取用户锁（防止同一用户并发匹配）
        user_lock = await self._get_user_lock(user_id)

        async with user_lock:
            # 检查是否已有结果（有结果说明之前匹配成功，直接返回）
            existing_result = await self.result_manager.get_safe(user_id)
            if existing_result:
                logger.info(f"用户 {user_id} 已有匹配结果，直接返回")
                return existing_result

            # 检查是否正在队列中等待（注意：这个检查可能在锁外有竞态，但概率极低）
            if await self.queue.contains(user_id):
                raise ValueError(f"用户 {user_id} 已在匹配队列中")

            # 执行匹配
            success = await self._execute_match(user_id, websocket_ref, user_score)
            if not success:
                raise RuntimeError("匹配失败")

            # 等待结果（增加重试逻辑，处理超时清理的竞态）
            result = await self._wait_for_result_with_retry(user_id)
            if result is None:
                raise RuntimeError("匹配超时")

            return result

    async def _wait_for_result_with_retry(
        self,
        user_id: UserId,
        timeout: Optional[float] = None,
        retry_count: int = 3,
        retry_delay: float = 0.5
    ) -> Optional[SafeMatchResult]:
        """
        等待匹配结果（带重试，处理超时清理的竞态条件）

        Args:
            user_id: 用户 ID
            timeout: 总超时时间（秒）
            retry_count: 重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            安全匹配结果，超时则返回 None
        """
        if timeout is None:
            timeout = float(self.config.timeout_seconds)

        start_time = datetime.now(timezone.utc).timestamp()

        # 主等待循环
        while (datetime.now(timezone.utc).timestamp() - start_time) < timeout:
            result = await self.result_manager.get_safe(user_id)
            if result:
                return result
            await asyncio.sleep(0.1)

        # 超时后重试（处理清理任务的竞态）
        for attempt in range(retry_count):
            result = await self.result_manager.get_safe(user_id)
            if result:
                logger.info(f"用户 {user_id} 在超时后重试 {attempt + 1}/{retry_count} 获取到匹配结果")
                return result
            await asyncio.sleep(retry_delay)

        # 最终检查
        result = await self.result_manager.get_safe(user_id)
        if result:
            logger.info(f"用户 {user_id} 在最终检查获取到匹配结果")
            return result

        logger.warning(f"用户 {user_id} 匹配超时，未获取到结果")
        return None

    async def _get_user_lock(self, user_id: UserId) -> asyncio.Lock:
        """
        获取用户的异步锁（延迟创建，防止并发访问）

        Args:
            user_id: 用户 ID

        Returns:
            用户专属的异步锁
        """
        async with self._locks_lock:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = asyncio.Lock()
            return self._user_locks[user_id]

    async def _execute_match(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> bool:
        """
        执行匹配逻辑

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分

        Returns:
            是否成功
        """
        # 1. 决定匹配类型
        match_type = self.algorithm.decide_match_type(self.config)
        logger.info(f"用户 {user_id} 匹配类型：{match_type.value}")

        self._stats['total_matches'] += 1

        # 2. 根据类型执行不同逻辑
        if match_type == MatchType.BOT:
            await self._match_bot(user_id, websocket_ref, user_score)
            self._stats['bot_matches'] += 1
            return True

        elif match_type == MatchType.HONEYPOT:
            await self._match_honeypot(user_id, websocket_ref, user_score)
            self._stats['honeypot_matches'] += 1
            return True

        else:  # match_type == MatchType.HUMAN
            return await self._match_human_or_timeout(
                user_id, websocket_ref, user_score
            )

    async def _match_bot(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> None:
        """
        匹配普通 Bot

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分
        """
        bot_config = self.bot_pool.draw()
        match_duration = self.algorithm.calculate_match_duration(self.config)

        result = MatchResultData(
            session_id=0,  # 由上层创建会话后更新
            opponent_type="ai",
            true_identity=f"Bot_{bot_config.id}",
            bot_level=bot_config.id,
            is_honeypot=False,
            match_duration_ms=match_duration,
        )

        # 存储结果（包含 Bot 配置供上层使用）
        await self.result_manager.store(user_id, result)
        logger.info(f"用户 {user_id} 匹配 Bot: {bot_config.id}")

    async def _match_honeypot(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> None:
        """
        匹配钓鱼 Bot

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分
        """
        honeypot_config = self.honeypot_pool.draw()
        match_duration = self.algorithm.calculate_match_duration(self.config)

        result = MatchResultData(
            session_id=0,  # 由上层创建会话后更新
            opponent_type="honeypot",
            true_identity=f"Honeypot_{honeypot_config.id}",
            bot_level=None,
            is_honeypot=True,
            match_duration_ms=match_duration,
        )

        await self.result_manager.store(user_id, result)
        logger.info(f"用户 {user_id} 匹配钓鱼 Bot: {honeypot_config.id}")

    async def _match_human_or_timeout(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> bool:
        """
        尝试匹配真人，如果队列中有人则配对，否则加入等待

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分

        Returns:
            是否成功（加入等待队列也算成功）
        """
        # 获取队列快照
        snapshot = await self.queue.get_snapshot()

        # 尝试在队列中找人
        opponent_id = self.algorithm.select_opponent(snapshot)

        if opponent_id:
            # 队列里有人，立即配对
            await self._create_human_pair(user_id, opponent_id)
            self._stats['human_matches'] += 1
            return True
        else:
            # 队列里没人，加入等待
            request = MatchRequest(
                user_id=user_id,
                timestamp=datetime.now(timezone.utc).timestamp(),
                match_type=MatchType.HUMAN,
                websocket_ref=websocket_ref,
                user_score=user_score,
            )
            await self.queue.add(request)
            return True

    async def _create_human_pair(
        self,
        user_id: UserId,
        opponent_id: UserId
    ) -> None:
        """
        创建真人配对

        Args:
            user_id: 用户 ID
            opponent_id: 对手用户 ID
        """
        # 从队列中移除对手
        await self.queue.remove(opponent_id)

        match_duration = self.algorithm.calculate_match_duration(self.config)

        # 为双方创建相同的匹配结果
        result = MatchResultData(
            session_id=0,  # 由上层创建会话后更新
            opponent_type="opponent",
            true_identity="Human",
            bot_level=None,
            is_honeypot=False,
            opponent_user_id=opponent_id,
            match_duration_ms=match_duration,
        )

        # 为双方存储结果
        await self.result_manager.store_batch({
            user_id: result,
            opponent_id: result,
        })

        logger.info(f"✅ 真人匹配：用户 {user_id} <-> 用户 {opponent_id}")

    async def _wait_for_result(
        self,
        user_id: UserId,
        timeout: Optional[float] = None
    ) -> Optional[SafeMatchResult]:
        """
        等待匹配结果

        Args:
            user_id: 用户 ID
            timeout: 超时时间（秒），默认使用配置值

        Returns:
            安全匹配结果，超时则返回 None
        """
        if timeout is None:
            timeout = float(self.config.timeout_seconds)

        start_time = datetime.now(timezone.utc).timestamp()

        while (datetime.now(timezone.utc).timestamp() - start_time) < timeout:
            result = await self.result_manager.get_safe(user_id)
            if result:
                return result
            await asyncio.sleep(0.1)

        # 超时后额外检查一次（避免竞态条件）
        result = await self.result_manager.get_safe(user_id)
        if result:
            logger.info(f"用户 {user_id} 在超时后获取到匹配结果")
            return result

        return None

    async def remove_from_queue(self, user_id: UserId) -> bool:
        """
        从队列中移除用户

        Args:
            user_id: 用户 ID

        Returns:
            是否成功移除
        """
        return await self.queue.remove(user_id)

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            **self._stats,
            'queue_size': len(self._queue._queue) if hasattr(self._queue, '_queue') else 0,
        }

    def get_bot_pools(self) -> Tuple[BotPool, HoneypotPool]:
        """获取 Bot 池"""
        return self.bot_pool, self.honeypot_pool
