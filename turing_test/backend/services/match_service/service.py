"""
匹配服务（重构版）

基于新架构的匹配服务，职责清晰、易于测试。

架构层次:
1. Config: 配置管理
2. Algorithm: 匹配算法
3. Pools: Bot 池
4. Queue: 队列管理
5. ResultManager: 结果管理
6. Matcher: 匹配协调器
7. Service: 对外接口（本文件）
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Any, Dict, Tuple
from contextlib import asynccontextmanager

from loguru import logger

from .config import MatchConfig
from .queue import MatchQueue
from .result_manager import ResultManager
from .matcher import MatchCoordinator
from .algorithm import ProbabilityAlgorithm
from .pools import BotPool, HoneypotPool, BotPoolConfig, HoneypotPoolConfig
from .types import (
    UserId, WebsocketRef, MatchType, MatchRequest,
    MatchResultData, SafeMatchResult, MatchStatistics,
)


class MatchService:
    """
    匹配服务（重构版）

    对外提供的统一接口，内部委托给协调器处理。

    核心职责:
    1. 提供匹配接口（join_queue, remove_from_queue, get_result）
    2. 管理后台任务（超时清理）
    3. 创建会话（与数据库交互）

    注意：
    - 具体匹配逻辑委托给 MatchCoordinator
    - 会话创建由 SessionCreator 处理
    """

    def __init__(
        self,
        config: Optional[MatchConfig] = None,
        coordinator: Optional[MatchCoordinator] = None,
    ):
        """
        初始化匹配服务

        Args:
            config: 匹配配置（None 时使用默认配置）
            coordinator: 匹配协调器（None 时自动创建）
        """
        self.config = config or MatchConfig()
        self.coordinator = coordinator or self._create_default_coordinator()

        # 后台任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # 会话创建器（由外部注入或延迟初始化）
        self._session_creator: Optional[Any] = None

    def _create_default_coordinator(self) -> MatchCoordinator:
        """创建默认协调器"""
        return MatchCoordinator(
            config=self.config,
            algorithm=ProbabilityAlgorithm(),
            queue=MatchQueue(),
            bot_pool=BotPool(),
            honeypot_pool=HoneypotPool(),
            result_manager=ResultManager(),
        )

    def set_session_creator(self, creator: Any) -> None:
        """
        设置会话创建器（依赖注入）

        Args:
            creator: 会话创建器实例
        """
        self._session_creator = creator
        logger.info("MatchService: 会话创建器已注入")

    def start(self) -> None:
        """启动后台任务"""
        if self._running:
            logger.warning("MatchService 已经运行")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("MatchService 已启动")

    async def stop(self) -> None:
        """停止服务"""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        logger.info("MatchService 已停止")

    async def _cleanup_loop(self) -> None:
        """定期清理超时匹配请求"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                logger.info("MatchService 清理任务已取消")
                break
            except Exception as e:
                logger.error(f"MatchService 清理任务出错：{e}", exc_info=True)

    async def _cleanup_expired(self) -> None:
        """清理超时的匹配请求"""
        coordinator = self.coordinator
        queue = coordinator.queue

        async def on_expired(user_id: UserId, request: MatchRequest) -> None:
            """超时回调：分配 Bot（如果用户还没有结果）"""
            # 检查用户是否已有匹配结果（避免重复分配）
            existing_result = await coordinator.result_manager.get_safe(user_id)
            if existing_result:
                logger.info(f"用户 {user_id} 已有匹配结果，跳过超时回调")
                return
            
            await coordinator._match_bot(user_id, request.websocket_ref or 0, request.user_score)
            coordinator._stats['timeout_fallbacks'] += 1

        await queue.cleanup_expired(
            timeout_seconds=self.config.timeout_seconds,
            on_expired=on_expired,
        )

    async def join_queue(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int = 100
    ) -> SafeMatchResult:
        """
        加入匹配队列

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分

        Returns:
            安全匹配结果

        Raises:
            ValueError: 用户已在队列中
            RuntimeError: 匹配失败
        """
        # 执行匹配
        result = await self.coordinator.match_user(user_id, websocket_ref, user_score)

        # 异步创建会话（不阻塞响应）
        if self._session_creator:
            asyncio.create_task(self._session_creator.create_session(result, user_id))

        return result

    async def remove_from_queue(self, user_id: UserId) -> bool:
        """从队列中移除用户"""
        return await self.coordinator.remove_from_queue(user_id)

    async def get_result(self, user_id: UserId) -> Optional[SafeMatchResult]:
        """获取暂存的匹配结果（安全版本）"""
        return await self.coordinator.result_manager.get_safe(user_id)

    async def get_result_internal(self, user_id: UserId) -> Optional[MatchResultData]:
        """获取暂存的匹配结果（内部使用，包含完整信息）"""
        return await self.coordinator.result_manager.get(user_id)

    async def clear_result(self, user_id: UserId) -> None:
        """清除暂存的匹配结果"""
        await self.coordinator.result_manager.clear(user_id)

    def get_queue_size(self) -> int:
        """获取队列大小（同步版本）"""
        # 注意：这是近似值，因为队列是异步的
        return len(self.coordinator.queue._queue)

    def is_user_waiting(self, user_id: UserId) -> bool:
        """检查用户是否在等待队列中（同步版本）"""
        return user_id in self.coordinator.queue._queue

    def get_statistics(self) -> MatchStatistics:
        """获取匹配服务统计信息"""
        stats = self.coordinator.get_stats()
        bot_pool, honeypot_pool = self.coordinator.get_bot_pools()

        return MatchStatistics(
            waiting_count=stats.get('queue_size', 0),
            human_waiting=0,  # TODO: 需要异步获取
            timeout_seconds=self.config.timeout_seconds,
            bot_pool=bot_pool.get_stats(),
            honeypot_pool=honeypot_pool.get_stats(),
        )

    def get_internal_stats(self) -> Dict[str, Any]:
        """获取内部统计信息（包含详细数据）"""
        return self.coordinator.get_stats()

    def get_bot_pools(self) -> Tuple[BotPool, HoneypotPool]:
        """获取 Bot 池"""
        return self.coordinator.get_bot_pools()

    @asynccontextmanager
    async def transaction(self, user_id: UserId):
        """
        事务上下文管理器，确保操作的原子性

        Usage:
            async with match_service.transaction(user_id) as tx:
                tx.result = some_result
        """
        class Transaction:
            def __init__(self):
                self.result: Optional[MatchResultData] = None
                self.committed = False

        tx = Transaction()
        try:
            yield tx
            if tx.result and not tx.committed:
                await self.coordinator.result_manager.store(user_id, tx.result)
                tx.committed = True
                logger.debug(f"事务提交：user_id={user_id}")
        except Exception as e:
            logger.error(f"事务失败：user_id={user_id}, error={e}", exc_info=True)
            raise


# =============================================================================
# 工厂函数（依赖注入）
# =============================================================================

# 全局实例（用于非路由层访问，如 game.py、WebSocket 等）
_match_service_instance: Optional[MatchService] = None


def create_match_service(
    config: Optional[MatchConfig] = None,
    coordinator: Optional[MatchCoordinator] = None
) -> MatchService:
    """
    创建匹配服务实例

    Args:
        config: 匹配配置
        coordinator: 匹配协调器

    Returns:
        MatchService 实例
    """
    return MatchService(config=config, coordinator=coordinator)


def get_match_service() -> MatchService:
    """
    获取全局匹配服务实例

    注意：此函数仅用于非路由层（如 game.py、WebSocket 等）。
    路由层请使用依赖注入：MatchServiceDep

    Returns:
        MatchService 实例

    Raises:
        RuntimeError: 如果服务未在 main.py 中初始化
    """
    global _match_service_instance
    if _match_service_instance is None:
        # 尝试从当前运行的 app 获取
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行的事件循环，说明在应用中，应该从 app.state 获取
            # 但这需要调用者传入 request，所以抛出更明确的错误
            raise RuntimeError(
                "匹配服务未初始化。请在 main.py 的 lifespan 中初始化，"
                "或在调用此函数前确保应用已启动。"
            )
        except RuntimeError:
            raise
    return _match_service_instance


def set_match_service(service: MatchService) -> None:
    """
    设置全局匹配服务实例（在 main.py 的 lifespan 中调用）

    Args:
        service: 匹配服务实例
    """
    global _match_service_instance
    _match_service_instance = service


def reset_match_service() -> None:
    """重置全局匹配服务实例（用于测试）"""
    global _match_service_instance
    _match_service_instance = None
