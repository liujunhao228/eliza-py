"""
AliceBot 池管理器

管理多个轻量级 AliceBot 实例，支持负载均衡和动态扩缩容。

特性：
- 线程安全的实例管理
- 自动负载均衡
- 动态扩缩容
- 故障转移
- 空闲实例清理
"""

import threading
import time
from typing import Dict, List, Optional
from loguru import logger

from alice.bots.lightweight_alice_bot import LightweightAliceBot
from alice.services.shared_nlp_service import SharedNLPService


class BotInstanceInfo:
    """Bot 实例信息"""

    def __init__(self, bot: LightweightAliceBot):
        self.bot = bot
        self.bot_id = id(bot)
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.request_count = 0
        self.is_busy = False
        self.assigned_at: Optional[float] = None

    def mark_busy(self):
        """标记为忙碌状态"""
        self.is_busy = True
        self.assigned_at = time.time()

    def mark_idle(self):
        """标记为空闲状态"""
        self.is_busy = False
        self.last_used_at = time.time()
        self.request_count += 1

    def get_idle_duration(self) -> float:
        """获取空闲时长（秒）"""
        return time.time() - self.last_used_at

    def get_stats(self) -> Dict:
        """获取实例统计信息"""
        return {
            "bot_id": self.bot_id,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "request_count": self.request_count,
            "is_busy": self.is_busy,
            "idle_duration": self.get_idle_duration(),
        }


class AliceBotPool:
    """
    AliceBot 池管理器

    管理多个轻量级 AliceBot 实例，支持负载均衡。

    使用示例:
        # 初始化
        nlp_service = SharedNLPService()
        pool = AliceBotPool(nlp_service)

        # 获取 Bot
        bot = pool.acquire()
        if bot:
            response = bot.respond("你好")
            pool.release(bot)

        # 关闭
        pool.shutdown()
    """

    def __init__(
        self,
        nlp_service: SharedNLPService,
        min_instances: int = 2,
        max_instances: int = 10,
        idle_timeout: int = 300,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        enable_plugins: bool = True,
    ):
        """
        初始化 Bot 池

        Args:
            nlp_service: 共享 NLP 服务
            min_instances: 最小实例数
            max_instances: 最大实例数
            idle_timeout: 空闲超时时间（秒）
            script_file: 脚本文件路径
            rules_file: 规则文件路径
            enable_plugins: 是否启用插件
        """
        self.nlp_service = nlp_service
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.idle_timeout = idle_timeout
        self.script_file = script_file
        self.rules_file = rules_file
        self.enable_plugins = enable_plugins

        # 实例池
        self._instances: Dict[int, BotInstanceInfo] = {}
        self._available: List[int] = []  # 可用实例 ID 列表
        self._lock = threading.RLock()

        # 统计信息
        self._stats = {
            "total_acquires": 0,
            "total_releases": 0,
            "total_creates": 0,
            "total_destroys": 0,
            "failed_acquires": 0,
        }

        # 初始化池
        self._initialize_pool()

        # 启动维护线程
        self._maintenance_active = True
        self._maintenance_thread = threading.Thread(
            target=self._maintain_pool,
            daemon=True,
            name="BotPool-Maintenance",
        )
        self._maintenance_thread.start()

        logger.info(
            f"✅ Bot 池初始化完成：最小实例={min_instances}, "
            f"最大实例={max_instances}, 空闲超时={idle_timeout}秒"
        )

    def _initialize_pool(self):
        """初始化 Bot 池，创建最小实例数"""
        with self._lock:
            for i in range(self.min_instances):
                self._create_instance()

    def _create_instance(self) -> Optional[BotInstanceInfo]:
        """创建一个新的 Bot 实例"""
        try:
            bot = LightweightAliceBot(
                nlp_service=self.nlp_service,
                script_file=self.script_file,
                rules_file=self.rules_file,
                enable_logging=False,  # 减少日志开销
                enable_plugins=self.enable_plugins,
                cache_size=50,
                use_ltp=False,  # 禁用 LTP 以避免重复加载
            )

            if bot and bot._initialized:
                info = BotInstanceInfo(bot)
                self._instances[info.bot_id] = info
                self._available.append(info.bot_id)
                self._stats["total_creates"] += 1

                logger.debug(f"创建 Bot 实例 {info.bot_id}")
                return info
            else:
                logger.warning("Bot 实例创建失败：初始化未完成")
                return None

        except Exception as e:
            logger.error(f"创建 Bot 实例失败：{e}", exc_info=True)
            return None

    def _destroy_instance(self, bot_id: int) -> bool:
        """销毁一个 Bot 实例"""
        with self._lock:
            if bot_id not in self._instances:
                return False

            info = self._instances[bot_id]

            # 如果实例正在使用中，不能销毁
            if info.is_busy:
                logger.warning(f"Bot 实例 {bot_id} 正在使用中，无法销毁")
                return False

            # 清理资源
            try:
                info.bot.cleanup()
            except Exception as e:
                logger.error(f"清理 Bot 实例 {bot_id} 失败：{e}")

            # 从可用列表中移除
            if bot_id in self._available:
                self._available.remove(bot_id)

            # 删除实例信息
            del self._instances[bot_id]
            self._stats["total_destroys"] += 1

            logger.debug(f"销毁 Bot 实例 {bot_id}")
            return True

    def acquire(self, timeout: Optional[float] = None) -> Optional[LightweightAliceBot]:
        """
        获取一个可用的 Bot 实例

        Args:
            timeout: 等待超时时间（秒），None 表示立即返回

        Returns:
            Bot 实例，如果无法获取则返回 None
        """
        start_time = time.time()

        while True:
            with self._lock:
                # 首先尝试从可用池中获取
                if self._available:
                    bot_id = self._available.pop(0)
                    info = self._instances[bot_id]
                    info.mark_busy()
                    self._stats["total_acquires"] += 1

                    logger.debug(f"获取 Bot 实例 {bot_id}")
                    return info.bot

                # 如果可用池为空且未达到最大实例数，创建新实例
                if len(self._instances) < self.max_instances:
                    info = self._create_instance()
                    if info:
                        info.mark_busy()
                        self._stats["total_acquires"] += 1
                        return info.bot

                # 如果达到最大实例数，根据超时策略处理
                if timeout is None:
                    # 不等待，直接返回 None
                    self._stats["failed_acquires"] += 1
                    logger.warning("Bot 池已满且无可用实例")
                    return None

                # 检查是否超时
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    self._stats["failed_acquires"] += 1
                    logger.warning(f"获取 Bot 实例超时（{timeout}秒）")
                    return None

            # 等待一小段时间后重试
            time.sleep(0.1)

    def release(self, bot: LightweightAliceBot):
        """
        释放 Bot 实例回池中

        Args:
            bot: 要释放的 Bot 实例
        """
        with self._lock:
            bot_id = id(bot)

            if bot_id not in self._instances:
                logger.warning(f"释放未知的 Bot 实例 {bot_id}")
                return

            info = self._instances[bot_id]

            if not info.is_busy:
                logger.warning(f"Bot 实例 {bot_id} 未处于忙碌状态")
                return

            info.mark_idle()
            self._available.append(bot_id)
            self._stats["total_releases"] += 1

            logger.debug(f"释放 Bot 实例 {bot_id}")

    def _maintain_pool(self):
        """维护池：定期清理空闲实例"""
        while self._maintenance_active:
            time.sleep(60)  # 每分钟检查一次
            self._cleanup_idle_instances()

    def _cleanup_idle_instances(self):
        """清理空闲实例，但保持最少实例数"""
        with self._lock:
            current_time = time.time()
            to_remove = []

            # 找出空闲时间过长的实例
            for bot_id, info in self._instances.items():
                if not info.is_busy:
                    idle_duration = info.get_idle_duration()
                    if idle_duration > self.idle_timeout:
                        to_remove.append(bot_id)

            # 排序，优先删除空闲时间最长的
            to_remove.sort(
                key=lambda bid: self._instances[bid].get_idle_duration(),
                reverse=True,
            )

            # 删除空闲实例，但保持最少实例数
            for bot_id in to_remove:
                if len(self._instances) <= self.min_instances:
                    break
                self._destroy_instance(bot_id)

            if to_remove:
                logger.info(f"清理了 {len(to_remove)} 个空闲 Bot 实例")

    def get_stats(self) -> Dict:
        """获取池统计信息"""
        with self._lock:
            busy_count = sum(1 for info in self._instances.values() if info.is_busy)
            available_count = len(self._available)

            return {
                "total_instances": len(self._instances),
                "available_instances": available_count,
                "busy_instances": busy_count,
                "min_instances": self.min_instances,
                "max_instances": self.max_instances,
                "pool_stats": self._stats.copy(),
                "instances": [info.get_stats() for info in self._instances.values()],
            }

    def get_available_count(self) -> int:
        """获取可用实例数"""
        with self._lock:
            return len(self._available)

    def get_total_count(self) -> int:
        """获取总实例数"""
        with self._lock:
            return len(self._instances)

    def shutdown(self):
        """关闭池，清理所有实例"""
        logger.info("正在关闭 Bot 池...")

        self._maintenance_active = False

        with self._lock:
            # 清理所有实例
            for bot_id in list(self._instances.keys()):
                self._destroy_instance(bot_id)

            self._instances.clear()
            self._available.clear()

        logger.info("✅ Bot 池已关闭")


# =============================================================================
# 全局 Bot 池实例（懒加载）
# =============================================================================

_bot_pool_instance: Optional[AliceBotPool] = None
_bot_pool_lock = threading.Lock()


def get_bot_pool() -> Optional[AliceBotPool]:
    """
    获取全局 Bot 池实例

    Returns:
        AliceBotPool 实例，如果未初始化则返回 None
    """
    return _bot_pool_instance


def init_bot_pool(
    nlp_service: SharedNLPService,
    min_instances: int = 2,
    max_instances: int = 10,
    idle_timeout: int = 300,
    script_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    enable_plugins: bool = True,
) -> AliceBotPool:
    """
    初始化全局 Bot 池

    Args:
        nlp_service: 共享 NLP 服务
        min_instances: 最小实例数
        max_instances: 最大实例数
        idle_timeout: 空闲超时时间（秒）
        script_file: 脚本文件路径
        rules_file: 规则文件路径
        enable_plugins: 是否启用插件

    Returns:
        AliceBotPool 实例
    """
    global _bot_pool_instance

    with _bot_pool_lock:
        if _bot_pool_instance is None:
            _bot_pool_instance = AliceBotPool(
                nlp_service=nlp_service,
                min_instances=min_instances,
                max_instances=max_instances,
                idle_timeout=idle_timeout,
                script_file=script_file,
                rules_file=rules_file,
                enable_plugins=enable_plugins,
            )
            logger.info(f"✅ 全局 Bot 池已初始化")
        else:
            logger.warning("全局 Bot 池已存在，重复初始化被忽略")

    return _bot_pool_instance


def shutdown_bot_pool():
    """关闭全局 Bot 池"""
    global _bot_pool_instance

    with _bot_pool_lock:
        if _bot_pool_instance:
            _bot_pool_instance.shutdown()
            _bot_pool_instance = None
            logger.info("✅ 全局 Bot 池已关闭")
