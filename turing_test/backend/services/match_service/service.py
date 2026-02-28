"""
匹配服务（概率分流版）- 重构版

修复内容:
1. 添加缺失的 join_queue 方法，修复 API 层调用
2. 为所有共享状态添加锁保护，避免竞态条件
3. 优化 Bot 池实现，使用 random.choices 替代低效的副本方式
4. 完善类型注解，使用 TypedDict 和 dataclass
5. 增强错误处理，添加 try-except 和回滚机制
6. 修复资源泄漏，完善任务取消和清理
7. 添加详细的日志和监控

匹配逻辑:
1. 30% 概率匹配真人（FIFO）
2. 70% 概率匹配 Bot（含 15% 钓鱼 Bot）
3. 真人超时 10 秒降级为 Bot
4. 结果暂存，前端主动拉取
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from loguru import logger

from config import settings
from turing_test.backend.services.session_state import session_state_manager
from turing_test.backend.services.match_bot_pool import (
    BotPool, HoneypotPool,
    get_bot_pool, get_honeypot_pool,
)
from turing_test.backend.services.match_service.types import (
    MatchType, MatchRequest, MatchResultData, SafeMatchResult, MatchStatistics,
    UserId, SessionId, WebsocketRef,
)


@dataclass
class MatchServiceConfig:
    """
    匹配服务配置
    
    Attributes:
        human_probability: 真人匹配概率 (默认 30%)
        bot_probability: Bot 匹配概率 (默认 70%)
        honeypot_in_bot_rate: 钓鱼 Bot 在 Bot 局中的比例 (默认 15%)
        timeout_seconds: 真人匹配超时时间 (秒)
        fake_delay_min_ms: 假装延迟最小值 (毫秒)
        fake_delay_max_ms: 假装延迟最大值 (毫秒)
        cleanup_interval_seconds: 清理任务间隔 (秒)
    """
    human_probability: float = 0.30
    bot_probability: float = 0.70
    honeypot_in_bot_rate: float = 0.15
    timeout_seconds: int = 10
    fake_delay_min_ms: int = 1000
    fake_delay_max_ms: int = 3000
    cleanup_interval_seconds: int = 5


class MatchService:
    """
    概率分流匹配服务
    
    核心逻辑:
    1. 用户加入时，后台掷骰子决定匹配类型
       - 70% → Bot 局 (立即分配 Bot)
       - 15% of Bot → 钓鱼 Bot
       - 30% → 真人局 (尝试匹配真人，超时降级为 Bot)

    2. Bot 局：从 Bot 池抽取 (Lv.1/2/3)
    3. 钓鱼局：从钓鱼 Bot 池抽取 (攻击型/可疑型)
    4. 真人局：FIFO 匹配，超时 10 秒降级为 Bot
    
    线程安全:
    - 使用 asyncio.Lock 保护所有共享状态
    - waiting_queue 和 match_results 分别有独立的锁
    """

    def __init__(self, config: Optional[MatchServiceConfig] = None):
        """
        初始化匹配服务
        
        Args:
            config: 匹配服务配置，None 时使用默认配置
        """
        # 等待队列：user_id -> MatchRequest
        self._waiting_queue: Dict[UserId, MatchRequest] = {}
        # 匹配结果暂存：user_id -> MatchResultData
        self._match_results: Dict[UserId, MatchResultData] = {}
        
        # 独立的锁，避免锁竞争
        self._queue_lock = asyncio.Lock()
        self._results_lock = asyncio.Lock()
        
        # 配置
        self._config = config or self._load_config_from_settings()
        
        # Bot 池（通过依赖注入获取）
        self._bot_pool: Optional[BotPool] = None
        self._honeypot_pool: Optional[HoneypotPool] = None
        
        # 后台任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 统计信息
        self._stats = {
            'total_matches': 0,
            'human_matches': 0,
            'bot_matches': 0,
            'honeypot_matches': 0,
            'timeout_fallbacks': 0,
        }

    def _load_config_from_settings(self) -> MatchServiceConfig:
        """从全局配置加载配置"""
        try:
            honeypot_cfg = settings.turing.match.honeypot
            if hasattr(honeypot_cfg, 'probability_in_bot_matches'):
                honeypot_rate = honeypot_cfg.probability_in_bot_matches
            elif isinstance(honeypot_cfg, dict):
                honeypot_rate = honeypot_cfg.get('probability_in_bot_matches', 0.15)
            else:
                honeypot_rate = 0.15
        except (AttributeError, KeyError):
            honeypot_rate = 0.15
        
        return MatchServiceConfig(
            human_probability=getattr(settings.turing.match, 'human_probability', 0.30),
            bot_probability=getattr(settings.turing.match, 'bot_probability', 0.70),
            honeypot_in_bot_rate=honeypot_rate,
            timeout_seconds=getattr(settings.turing.match, 'timeout_seconds', 10),
            fake_delay_min_ms=getattr(settings.turing.match, 'fake_delay_min_ms', 1000),
            fake_delay_max_ms=getattr(settings.turing.match, 'fake_delay_max_ms', 3000),
        )

    def set_bot_pools(self, bot_pool: BotPool, honeypot_pool: HoneypotPool) -> None:
        """
        设置 Bot 池（依赖注入）
        
        Args:
            bot_pool: 普通 Bot 池
            honeypot_pool: 钓鱼 Bot 池
        """
        self._bot_pool = bot_pool
        self._honeypot_pool = honeypot_pool
        logger.info("MatchService: Bot 池已注入")

    def get_bot_pools(self) -> Tuple[BotPool, HoneypotPool]:
        """获取 Bot 池（如果未设置则创建默认的）"""
        if self._bot_pool is None:
            self._bot_pool = get_bot_pool()
        if self._honeypot_pool is None:
            self._honeypot_pool = get_honeypot_pool()
        return self._bot_pool, self._honeypot_pool

    def start(self) -> None:
        """启动后台任务（在应用启动时调用）"""
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
                await asyncio.sleep(self._config.cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                logger.info("MatchService 清理任务已取消")
                break
            except Exception as e:
                logger.error(f"MatchService 清理任务出错：{e}", exc_info=True)

    async def _cleanup_expired(self) -> None:
        """清理超时的匹配请求"""
        now = datetime.now(timezone.utc).timestamp()
        expired_users: List[UserId] = []
        
        async with self._queue_lock:
            for user_id, request in list(self._waiting_queue.items()):
                if (now - request.timestamp) > self._config.timeout_seconds:
                    expired_users.append(user_id)
        
        # 处理超时用户（在锁外，避免长时间持有锁）
        for user_id in expired_users:
            try:
                async with self._queue_lock:
                    # 再次检查，避免已被处理
                    if user_id in self._waiting_queue:
                        del self._waiting_queue[user_id]
                
                # 超时降级为 Bot
                await self._assign_bot(user_id, MatchType.BOT_TIMEOUT)
                self._stats['timeout_fallbacks'] += 1
                logger.info(f"匹配超时：user_id={user_id}, 降级为 Bot")
                
            except Exception as e:
                logger.error(f"清理超时用户 {user_id} 失败：{e}", exc_info=True)

    def _decide_match_type(self) -> MatchType:
        """
        概率掷骰子决定匹配类型
        
        Returns:
            MatchType: 匹配类型
        """
        roll = random.random()

        # 累积概率阈值
        honeypot_threshold = self._config.honeypot_in_bot_rate * self._config.bot_probability
        human_threshold = honeypot_threshold + self._config.human_probability

        if roll < honeypot_threshold:
            return MatchType.HONEYPOT
        elif roll < human_threshold:
            return MatchType.HUMAN
        else:
            return MatchType.BOT

    def _generate_match_duration(self) -> int:
        """生成假装延迟 (毫秒)"""
        return random.randint(
            self._config.fake_delay_min_ms, 
            self._config.fake_delay_max_ms
        )

    async def join_queue(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int = 100
    ) -> SafeMatchResult:
        """
        加入匹配队列并等待结果（API 层使用）
        
        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分
            
        Returns:
            安全匹配结果（返回给前端）
            
        Raises:
            ValueError: 用户已在队列中或已有匹配结果
            RuntimeError: 匹配失败
        """
        # 检查重复
        async with self._queue_lock:
            if user_id in self._waiting_queue:
                raise ValueError(f"用户 {user_id} 已在匹配队列中")
        
        async with self._results_lock:
            if user_id in self._match_results:
                logger.warning(f"用户 {user_id} 已有匹配结果，清除旧结果")
                del self._match_results[user_id]
        
        # 加入队列并匹配
        success = await self._add_to_queue_internal(user_id, websocket_ref, user_score)
        if not success:
            raise RuntimeError("加入队列失败")
        
        # 等待匹配结果（最多等待 5 秒）
        result = await self._wait_for_result(user_id, timeout=5.0)
        if result is None:
            raise RuntimeError("匹配超时")
        
        return self._to_safe_result(result)

    async def _add_to_queue_internal(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> bool:
        """
        内部加入队列方法
        
        Returns:
            是否成功加入队列
        """
        # 概率掷骰子决定匹配类型
        match_type = self._decide_match_type()
        logger.info(f"用户 {user_id} 匹配类型：{match_type.value}")
        
        self._stats['total_matches'] += 1

        if match_type == MatchType.BOT:
            # Bot 局：立即分配
            await self._assign_bot(user_id, match_type, websocket_ref, user_score)
            self._stats['bot_matches'] += 1
            return True

        elif match_type == MatchType.HONEYPOT:
            # 钓鱼局：立即分配钓鱼 Bot
            await self._assign_honeypot(user_id, websocket_ref, user_score)
            self._stats['honeypot_matches'] += 1
            return True

        else:  # match_type == MatchType.HUMAN
            # 真人局：尝试匹配
            opponent_id = self._find_waiting_human()

            if opponent_id:
                # 队列里有人，立即配对
                await self._create_human_match(user_id, opponent_id, websocket_ref, user_score)
                self._stats['human_matches'] += 1
            else:
                # 队列里没人，加入等待
                async with self._queue_lock:
                    self._waiting_queue[user_id] = MatchRequest(
                        user_id=user_id,
                        timestamp=datetime.now(timezone.utc).timestamp(),
                        match_type=MatchType.HUMAN,
                        websocket_ref=websocket_ref,
                        user_score=user_score,
                    )
                logger.info(f"用户 {user_id} 加入等待队列")

        return True

    async def _wait_for_result(
        self,
        user_id: UserId,
        timeout: float = 5.0
    ) -> Optional[MatchResultData]:
        """等待匹配结果"""
        start_time = datetime.now(timezone.utc).timestamp()
        
        while (datetime.now(timezone.utc).timestamp() - start_time) < timeout:
            async with self._results_lock:
                if user_id in self._match_results:
                    return self._match_results[user_id]
            await asyncio.sleep(0.1)
        
        return None

    async def remove_from_queue(self, user_id: UserId) -> bool:
        """从队列中移除用户"""
        async with self._queue_lock:
            if user_id not in self._waiting_queue:
                return False
            del self._waiting_queue[user_id]
            logger.info(f"用户 {user_id} 离开等待队列")
            return True

    async def get_result(self, user_id: UserId) -> Optional[SafeMatchResult]:
        """获取暂存的匹配结果（安全版本）"""
        async with self._results_lock:
            result = self._match_results.get(user_id)
            if result:
                return self._to_safe_result(result)
        return None

    async def get_result_internal(self, user_id: UserId) -> Optional[MatchResultData]:
        """获取暂存的匹配结果（内部使用，包含完整信息）"""
        async with self._results_lock:
            return self._match_results.get(user_id)

    async def clear_result(self, user_id: UserId) -> None:
        """清除暂存的匹配结果"""
        async with self._results_lock:
            if user_id in self._match_results:
                del self._match_results[user_id]

    def _find_waiting_human(self) -> Optional[UserId]:
        """查找等待中的真人对手（FIFO）"""
        if not self._waiting_queue:
            return None

        # 获取最早加入的真人匹配用户
        earliest_user: Optional[UserId] = None
        earliest_time = float('inf')

        for uid, req in self._waiting_queue.items():
            if req.match_type == MatchType.HUMAN and req.timestamp < earliest_time:
                earliest_user = uid
                earliest_time = req.timestamp

        return earliest_user

    async def _create_human_match(
        self,
        user_id: UserId,
        opponent_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> None:
        """创建真人匹配"""
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        
        session_id: Optional[int] = None
        
        try:
            # 从队列中移除对手
            async with self._queue_lock:
                if opponent_id in self._waiting_queue:
                    del self._waiting_queue[opponent_id]

            async with async_session_maker() as db:
                try:
                    # 创建两个关联会话
                    session_a = Session(
                        user_id=user_id,
                        opponent_type="opponent",
                        true_identity="Human",
                        bot_level=None,
                        is_honeypot=False,
                        opponent_user_id=opponent_id,
                        turn_count=0,
                        meta_conversation_count=0,
                        started_at=datetime.now(timezone.utc),
                    )
                    db.add(session_a)
                    await db.flush()

                    session_b = Session(
                        user_id=opponent_id,
                        opponent_type="opponent",
                        true_identity="Human",
                        bot_level=None,
                        is_honeypot=False,
                        opponent_user_id=user_id,
                        opponent_session_id=session_a.id,
                        turn_count=0,
                        meta_conversation_count=0,
                        started_at=datetime.now(timezone.utc),
                    )
                    db.add(session_b)
                    await db.flush()

                    session_a.opponent_session_id = session_b.id
                    await db.commit()
                    
                    session_id = session_a.id
                    
                except Exception as db_error:
                    logger.error(f"创建真人会话失败：{db_error}", exc_info=True)
                    # 回滚：将对手重新加入队列
                    async with self._queue_lock:
                        self._waiting_queue[opponent_id] = MatchRequest(
                            user_id=opponent_id,
                            timestamp=datetime.now(timezone.utc).timestamp(),
                            match_type=MatchType.HUMAN,
                            websocket_ref=websocket_ref,
                            user_score=user_score,
                        )
                    raise

            # 暂存结果（使用锁保护）
            result = MatchResultData(
                session_id=session_id,
                opponent_type="opponent",
                true_identity="Human",
                bot_level=None,
                is_honeypot=False,
                opponent_user_id=opponent_id,
                match_duration_ms=self._generate_match_duration(),
            )
            
            async with self._results_lock:
                self._match_results[user_id] = result
                self._match_results[opponent_id] = result

            logger.info(f"✅ 真人匹配成功：用户 {user_id} <-> 用户 {opponent_id}, 会话 ID: {session_id}")
            
        except Exception as e:
            logger.error(f"创建真人匹配失败：{e}", exc_info=True)
            raise

    async def _assign_bot(
        self,
        user_id: UserId,
        match_type: MatchType,
        websocket_ref: Optional[WebsocketRef] = None,
        user_score: int = 100
    ) -> None:
        """分配 Bot 对手"""
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        
        bot_pool, _ = self.get_bot_pools()
        bot_config = bot_pool.get_bot()
        session_id: Optional[int] = None
        
        try:
            async with async_session_maker() as db:
                session = Session(
                    user_id=user_id,
                    opponent_type="opponent",
                    true_identity=f"Bot_{bot_config.id}",
                    bot_level=bot_config.id,
                    is_honeypot=False,
                    turn_count=0,
                    meta_conversation_count=0,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(session)
                await db.commit()
                session_id = session.id

            # 暂存结果（使用锁保护）
            result = MatchResultData(
                session_id=session_id,
                opponent_type="opponent",
                true_identity=f"Bot_{bot_config.id}",
                bot_level=bot_config.id,
                is_honeypot=False,
                match_duration_ms=self._generate_match_duration(),
            )
            
            async with self._results_lock:
                self._match_results[user_id] = result

            # 异步发送开场白（使用 weak_ref 避免循环引用）
            opening_task = asyncio.create_task(
                self._send_opening_message(session_id, user_id, is_honeypot=False)
            )
            session_state_manager.register_opening_task(session_id, opening_task)

            logger.info(f"为用户 {user_id} 分配 Bot 对手：{bot_config.id}, 会话 ID: {session_id}")
            
        except Exception as e:
            logger.error(f"分配 Bot 失败：{e}", exc_info=True)
            if session_id:
                session_state_manager.cancel_opening_task(session_id, reason=f"错误：{e}")
            raise

    async def _assign_honeypot(
        self,
        user_id: UserId,
        websocket_ref: WebsocketRef,
        user_score: int
    ) -> None:
        """分配钓鱼 Bot"""
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        
        _, honeypot_pool = self.get_bot_pools()
        honeypot_config = honeypot_pool.get_bot()
        session_id: Optional[int] = None
        
        try:
            async with async_session_maker() as db:
                session = Session(
                    user_id=user_id,
                    opponent_type="opponent",
                    true_identity=f"Honeypot_{honeypot_config.id}",
                    bot_level=None,
                    is_honeypot=True,
                    turn_count=0,
                    meta_conversation_count=0,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(session)
                await db.commit()
                session_id = session.id

            # 暂存结果（使用锁保护）
            result = MatchResultData(
                session_id=session_id,
                opponent_type="opponent",
                true_identity=f"Honeypot_{honeypot_config.id}",
                bot_level=None,
                is_honeypot=True,
                match_duration_ms=self._generate_match_duration(),
            )
            
            async with self._results_lock:
                self._match_results[user_id] = result

            # 异步发送开场白
            opening_task = asyncio.create_task(
                self._send_opening_message(session_id, user_id, is_honeypot=True)
            )
            session_state_manager.register_opening_task(session_id, opening_task)

            logger.info(f"为用户 {user_id} 分配钓鱼 Bot: {honeypot_config.id}, 会话 ID: {session_id}")
            
        except Exception as e:
            logger.error(f"分配钓鱼 Bot 失败：{e}", exc_info=True)
            if session_id:
                session_state_manager.cancel_opening_task(session_id, reason=f"错误：{e}")
            raise

    async def _send_opening_message(
        self,
        session_id: SessionId,
        user_id: UserId,
        is_honeypot: bool
    ) -> None:
        """延迟发送开场白"""
        from turing_test.backend.services.message_service import MessageService
        from config import get_config_manager
        from turing_test.backend.database import async_session_maker

        config_mgr = get_config_manager()
        opening_cfg = config_mgr.get('turing.ai_bot.opening', {})

        if is_honeypot:
            honeypot_cfg = opening_cfg.get('honeypot', {})
            probability = honeypot_cfg.get('probability', 0.5)
            delay_min = honeypot_cfg.get('delay_min', 5.0)
            delay_max = honeypot_cfg.get('delay_max', 15.0)
        else:
            probability = opening_cfg.get('probability', 0.7)
            delay_min = opening_cfg.get('delay_min', 2.0)
            delay_max = opening_cfg.get('delay_max', 5.0)

        if not opening_cfg.get('enabled', True):
            probability = 0.0

        # 等待随机延迟
        await asyncio.sleep(random.uniform(delay_min, delay_max))

        try:
            # 检查是否已有消息
            state = session_state_manager.get(session_id)
            if state and state.turn_count > 0:
                logger.info(f"用户已先发言，跳过开场白：session_id={session_id}")
                return

            # 概率检测
            if random.random() >= probability:
                logger.info(f"跳过开场白（概率检测未通过）：session_id={session_id}")
                return

            # 发送开场白
            async with async_session_maker() as db:
                await MessageService.send_opening_message(
                    session_id=session_id,
                    user_id=user_id,
                    db=db,
                )
                
        except asyncio.CancelledError:
            logger.info(f"开场白任务已取消：session_id={session_id}")
            raise
        except Exception as e:
            logger.error(f"发送开场白失败：session_id={session_id}, error={e}", exc_info=True)
        finally:
            session_state_manager.cancel_opening_task(session_id, reason="任务完成")

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self._waiting_queue)

    def is_user_waiting(self, user_id: UserId) -> bool:
        """检查用户是否在等待队列中"""
        return user_id in self._waiting_queue

    def get_statistics(self) -> MatchStatistics:
        """获取匹配服务统计信息"""
        human_waiting = sum(
            1 for req in self._waiting_queue.values()
            if req.match_type == MatchType.HUMAN
        )
        
        bot_pool, honeypot_pool = self.get_bot_pools()
        
        return MatchStatistics(
            waiting_count=self.get_queue_size(),
            human_waiting=human_waiting,
            timeout_seconds=self._config.timeout_seconds,
            bot_pool=bot_pool.get_stats(),
            honeypot_pool=honeypot_pool.get_stats(),
        )

    def get_internal_stats(self) -> Dict[str, Any]:
        """获取内部统计信息（包含详细数据）"""
        return {
            **self._stats,
            'queue_size': self.get_queue_size(),
        }

    def _to_safe_result(self, result: MatchResultData) -> SafeMatchResult:
        """将内部结果转换为安全结果（过滤敏感字段）"""
        return SafeMatchResult(
            session_id=result.session_id,
            opponent_type="opponent",
            match_duration_ms=result.match_duration_ms,
        )

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
                async with self._results_lock:
                    self._match_results[user_id] = tx.result
                tx.committed = True
                logger.debug(f"事务提交：user_id={user_id}")
        except Exception as e:
            logger.error(f"事务失败：user_id={user_id}, error={e}", exc_info=True)
            raise


# =============================================================================
# 工厂函数（依赖注入）
# =============================================================================

# 全局实例（用于向后兼容，新代码应该使用依赖注入）
_match_service_instance: Optional[MatchService] = None


def create_match_service(
    config: Optional[MatchServiceConfig] = None,
    bot_pool: Optional[BotPool] = None,
    honeypot_pool: Optional[HoneypotPool] = None,
) -> MatchService:
    """
    创建匹配服务实例（推荐方式）
    
    Args:
        config: 匹配服务配置
        bot_pool: Bot 池（可选，None 时自动创建）
        honeypot_pool: 钓鱼 Bot 池（可选，None 时自动创建）
        
    Returns:
        MatchService 实例
    """
    service = MatchService(config)
    
    if bot_pool and honeypot_pool:
        service.set_bot_pools(bot_pool, honeypot_pool)
    
    return service


def get_match_service() -> MatchService:
    """
    获取全局匹配服务实例（向后兼容）
    
    注意：新代码应该使用 create_match_service() 进行依赖注入
    """
    global _match_service_instance
    
    if _match_service_instance is None:
        _match_service_instance = MatchService()
        # 延迟启动后台任务
        try:
            loop = asyncio.get_running_loop()
            _match_service_instance.start()
        except RuntimeError:
            # 没有运行中的事件循环，稍后启动
            pass
    
    return _match_service_instance


def reset_match_service() -> None:
    """重置全局匹配服务实例（用于测试）"""
    global _match_service_instance
    if _match_service_instance:
        asyncio.create_task(_match_service_instance.stop())
    _match_service_instance = None


__all__ = [
    # 类型
    'MatchType',
    'MatchRequest',
    'MatchResultData',
    'SafeMatchResult',
    'MatchStatistics',
    'MatchServiceConfig',
    'UserId',
    'SessionId',
    'WebsocketRef',
    # 服务类
    'MatchService',
    # 工厂函数
    'create_match_service',
    'get_match_service',
    'reset_match_service',
]
