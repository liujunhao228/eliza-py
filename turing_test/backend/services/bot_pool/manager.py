"""
Bot 池管理模块

负责 Bot 池的获取/释放、负载均衡、扩缩容。
"""

import threading
import time
from typing import Dict, List, Optional

from loguru import logger

from alice.services.shared_nlp_service import SharedNLPService
from alice.bots.lightweight_alice_bot import LightweightAliceBot
from config import BotTemplate

from .instance import BotInstanceInfo
from .config import create_default_templates


class AliceBotPool:
    """
    AliceBot 池管理器

    管理多个轻量级 AliceBot 实例，支持负载均衡和多配置模板。

    使用示例:
        # 初始化
        nlp_service = SharedNLPService()
        templates = {"default": template1, "honeypot": template2}
        pool = AliceBotPool(nlp_service, templates=templates)

        # 获取 Bot (使用默认模板)
        bot = pool.acquire()
        if bot:
            response = bot.respond("你好")
            pool.release(bot)

        # 获取特定模板的 Bot
        bot = pool.acquire(template_id="honeypot")

        # 关闭
        pool.shutdown()
    """

    def __init__(
        self,
        nlp_service: SharedNLPService,
        templates: Optional[Dict[str, BotTemplate]] = None,
        default_template: str = "default",
        min_instances: int = 2,
        max_instances: int = 10,
        idle_timeout: int = 300,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
    ):
        """
        初始化 Bot 池

        Args:
            nlp_service: 共享 NLP 服务
            templates: Bot 模板字典 (模板 ID -> BotTemplate)
            default_template: 默认模板 ID
            min_instances: 最小实例数
            max_instances: 最大实例数
            idle_timeout: 空闲超时时间（秒）
            script_file: 脚本文件路径 (向后兼容，不使用模板时有效)
            rules_file: 规则文件路径 (向后兼容，不使用模板时有效)
        """
        self.nlp_service = nlp_service
        self.templates = templates or {}
        self.default_template = default_template
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.idle_timeout = idle_timeout

        # 向后兼容：如果没有模板，使用默认配置创建
        if not self.templates:
            self.templates = create_default_templates(script_file, rules_file)

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
        """初始化 Bot 池，创建最小实例数（使用默认模板）"""
        with self._lock:
            for i in range(self.min_instances):
                self._create_instance(self.default_template)

    def _create_instance(self, template_id: Optional[str] = None) -> Optional[BotInstanceInfo]:
        """创建一个新的 Bot 实例

        Args:
            template_id: 模板 ID，None 则使用默认模板

        Returns:
            Bot 实例信息，创建失败则返回 None
        """
        # 获取模板
        tid = template_id or self.default_template
        template = self.templates.get(tid)

        if not template:
            logger.error(f"创建 Bot 实例失败：模板不存在 '{tid}'")
            return None

        try:
            bot = LightweightAliceBot(
                nlp_service=self.nlp_service,
                script_file=str(template.script_file) if template.script_file else None,
                rules_file=str(template.rules_file) if template.rules_file else None,
                enable_logging=False,  # 减少日志开销
                cache_size=template.cache_size,
                use_ltp=False,  # 禁用 LTP 以避免重复加载
            )

            if bot and bot._initialized:
                info = BotInstanceInfo(bot, template_id=tid)
                self._instances[info.bot_id] = info
                self._available.append(info.bot_id)
                self._stats["total_creates"] += 1

                logger.debug(f"创建 Bot 实例 {info.bot_id} (模板：{tid})")
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

    def acquire(self, template_id: Optional[str] = None, timeout: Optional[float] = None) -> Optional[LightweightAliceBot]:
        """
        获取一个可用的 Bot 实例

        Args:
            template_id: 模板 ID，None 则使用默认模板
            timeout: 等待超时时间（秒），None 表示立即返回

        Returns:
            Bot 实例，如果无法获取则返回 None
        """
        tid = template_id or self.default_template
        start_time = time.time()

        while True:
            with self._lock:
                # 首先尝试从可用池中获取（优先相同模板的实例）
                available_bot = self._find_available_instance(tid)
                if available_bot:
                    bot_id, info = available_bot
                    info.mark_busy()
                    self._stats["total_acquires"] += 1
                    logger.debug(f"获取 Bot 实例 {bot_id} (模板：{info.template_id})")
                    return info.bot

                # 如果可用池为空且未达到最大实例数，创建新实例
                if len(self._instances) < self.max_instances:
                    info = self._create_instance(tid)
                    if info:
                        info.mark_busy()
                        self._stats["total_acquires"] += 1
                        return info.bot

                # 如果达到最大实例数，根据超时策略处理
                if timeout is None:
                    # 不等待，直接返回 None
                    self._stats["failed_acquires"] += 1
                    logger.warning(f"Bot 池已满且无可用实例 (模板：{tid})")
                    return None

                # 检查是否超时
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    self._stats["failed_acquires"] += 1
                    logger.warning(f"获取 Bot 实例超时（{timeout}秒，模板：{tid}）")
                    return None

            # 等待一小段时间后重试
            time.sleep(0.1)

    def _find_available_instance(self, template_id: str) -> Optional[tuple]:
        """
        查找可用的 Bot 实例

        Args:
            template_id: 优先查找的模板 ID

        Returns:
            (bot_id, info) 元组，如果没有可用实例则返回 None
        """
        # 优先查找相同模板的实例
        for bot_id in self._available:
            info = self._instances.get(bot_id)
            if info and info.template_id == template_id:
                self._available.remove(bot_id)
                return (bot_id, info)

        # 其次查找其他模板的实例
        for bot_id in self._available:
            info = self._instances.get(bot_id)
            if info:
                self._available.remove(bot_id)
                return (bot_id, info)

        return None

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
        """
        维护池：定期清理空闲实例和补充最小实例数

        优化：
        - 动态检查间隔：根据实例数量调整 (60-120 秒)
        - 智能清理：根据负载动态调整清理策略
        - 自动补充：当实例数低于最小值时自动补充
        """
        while self._maintenance_active:
            # 动态检查间隔：实例越多，检查间隔越长
            with self._lock:
                instance_count = len(self._instances)
            
            # 基础间隔 60 秒，每多一个实例增加 10 秒，最大 120 秒
            check_interval = min(120, max(60, 60 + instance_count * 10))
            time.sleep(check_interval)
            
            self._cleanup_idle_instances()
            self._replenish_min_instances()

    def _cleanup_idle_instances(self):
        """
        清理空闲实例，但保持最少实例数

        优化：
        - 动态空闲超时：根据请求频率调整
        - 批量清理：减少锁竞争
        """
        with self._lock:
            current_time = time.time()
            to_remove = []

            # 计算当前忙碌比例
            busy_count = sum(1 for info in self._instances.values() if info.is_busy)
            total_count = len(self._instances)
            busy_ratio = busy_count / total_count if total_count > 0 else 0

            # 动态调整空闲超时：忙碌时延长，空闲时缩短
            effective_timeout = self.idle_timeout
            if busy_ratio > 0.7:
                effective_timeout *= 1.5  # 忙碌时延长 50%
            elif busy_ratio < 0.3:
                effective_timeout *= 0.7  # 空闲时缩短 30%

            # 找出空闲时间过长的实例
            for bot_id, info in self._instances.items():
                if not info.is_busy:
                    idle_duration = info.get_idle_duration()
                    if idle_duration > effective_timeout:
                        to_remove.append(bot_id)

            # 排序，优先删除空闲时间最长的
            to_remove.sort(
                key=lambda bid: self._instances[bid].get_idle_duration(),
                reverse=True,
            )

            # 删除空闲实例，但保持最少实例数
            removed_count = 0
            for bot_id in to_remove:
                if len(self._instances) - removed_count <= self.min_instances:
                    break
                if self._destroy_instance(bot_id):
                    removed_count += 1

            if removed_count > 0:
                logger.info(f"清理了 {removed_count} 个空闲 Bot 实例")

    def _replenish_min_instances(self):
        """
        补充实例到最小数量

        优化：
        - 按需补充：仅当可用实例不足时补充
        - 使用默认模板：确保有足够的基础实例
        """
        with self._lock:
            available_count = len(self._available)
            needed_count = self.min_instances - len(self._instances)

            if needed_count > 0 and available_count < self.min_instances:
                logger.info(f"补充 {needed_count} 个 Bot 实例到最小数量")
                for _ in range(needed_count):
                    self._create_instance(self.default_template)

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
