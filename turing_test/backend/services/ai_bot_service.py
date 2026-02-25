"""
AI Bot 服务

集成 AliceBot 池，提供 AI 响应生成服务。
支持打字延迟模拟和负载均衡。
"""

import asyncio
import random
from typing import Tuple, Optional
from loguru import logger

from config import settings


class AIBotService:
    """
    AI Bot 服务

    提供 AI 响应生成服务，集成 Bot 池管理和打字延迟模拟。

    使用示例:
        service = AIBotService()
        response, delay = await service.get_response("你好")
    """

    def __init__(self):
        """初始化 AI Bot 服务"""
        self._initialized = False
        self._nlp_service = None
        self._bot_pool = None

    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return

        try:
            # 导入共享 NLP 服务
            from alice.services.shared_nlp_service import SharedNLPService
            self._nlp_service = SharedNLPService()

            # 初始化 Bot 池
            from turing_test.backend.bot_pool import init_bot_pool

            # 使用 getattr 提供默认值以兼容不同配置
            # 注意：script_file 和 rules_file 在 settings.alice.scripting 下
            script_file = None
            rules_file = None
            
            if hasattr(settings, 'alice') and settings.alice:
                alice_cfg = settings.alice
                # 从 scripting.yaml.script_file 获取
                if hasattr(alice_cfg, 'scripting') and alice_cfg.scripting:
                    scripting_cfg = alice_cfg.scripting
                    if hasattr(scripting_cfg, 'yaml') and scripting_cfg.yaml:
                        script_file = str(scripting_cfg.yaml.script_file) if scripting_cfg.yaml.script_file else None
                    rules_file = str(scripting_cfg.rules_file) if hasattr(scripting_cfg, 'rules_file') and scripting_cfg.rules_file else None
            
            self._bot_pool = init_bot_pool(
                nlp_service=self._nlp_service,
                min_instances=getattr(settings, 'BOT_POOL_MIN_INSTANCES', 2),
                max_instances=getattr(settings, 'BOT_POOL_MAX_INSTANCES', 10),
                idle_timeout=getattr(settings, 'BOT_POOL_IDLE_TIMEOUT', 300),
                script_file=script_file,
                rules_file=rules_file,
                enable_plugins=True,
            )

            self._initialized = True
            logger.info(f"✅ AI Bot 服务初始化成功 (script_file={script_file}, rules_file={rules_file})")

        except Exception as e:
            logger.error(f"AI Bot 服务初始化失败：{e}", exc_info=True)
            raise

    async def shutdown(self):
        """关闭服务"""
        if not self._initialized:
            return

        try:
            from turing_test.backend.bot_pool import shutdown_bot_pool
            shutdown_bot_pool()
            self._initialized = False
            logger.info("✅ AI Bot 服务已关闭")
        except Exception as e:
            logger.error(f"AI Bot 服务关闭失败：{e}")

    async def get_response(
        self,
        user_input: str,
        simulate_typing: bool = True,
    ) -> Tuple[str, float]:
        """
        获取 AI 响应

        Args:
            user_input: 用户输入
            simulate_typing: 是否模拟打字延迟

        Returns:
            (响应内容，打字延迟秒数)
        """
        if not self._initialized:
            logger.warning("AI Bot 服务未初始化")
            return "系统未初始化，请稍后再试。", 1.0

        # 从 Bot 池获取 Bot
        bot = self._bot_pool.acquire(timeout=5.0)
        if not bot:
            logger.warning("无法获取 Bot 实例")
            return "抱歉，我现在比较忙，请稍后再试。", 1.0

        try:
            # 生成响应
            response = bot.respond(user_input)

            # 计算打字延迟
            delay = self._calculate_typing_delay(response) if simulate_typing else 0.0

            # 模拟打字延迟
            if simulate_typing and delay > 0:
                await asyncio.sleep(delay)

            logger.debug(f"AI 响应生成：输入长度={len(user_input)}, 响应长度={len(response)}, 延迟={delay:.2f}秒")

            return response, delay

        except Exception as e:
            logger.error(f"生成 AI 响应失败：{e}", exc_info=True)
            return "系统出现故障，请稍后再试。", 1.0

        finally:
            # 释放 Bot 回池中
            self._bot_pool.release(bot)

    def _calculate_typing_delay(self, response: str) -> float:
        """
        计算打字延迟，模拟人类打字行为

        考虑因素:
        - 基础延迟
        - 响应长度
        - 随机波动

        Args:
            response: AI 响应内容

        Returns:
            打字延迟（秒）
        """
        # 基础延迟
        base_delay = getattr(settings, 'TYPING_DELAY_BASE', 1.0)

        # 根据响应长度计算延迟
        chars_per_second = getattr(settings, 'TYPING_DELAY_PER_CHAR', 0.05)
        length_delay = len(response) * chars_per_second

        # 总延迟
        total_delay = base_delay + length_delay

        # 添加随机波动（±20%）
        jitter = random.uniform(-0.2, 0.2) * total_delay
        total_delay += jitter

        # 确保最小延迟
        return max(0.5, total_delay)

    def get_pool_stats(self) -> dict:
        """
        获取 Bot 池统计信息

        Returns:
            统计信息字典
        """
        if not self._initialized or not self._bot_pool:
            return {"error": "服务未初始化"}

        return self._bot_pool.get_stats()


# =============================================================================
# 全局服务实例
# =============================================================================

_ai_bot_service: Optional[AIBotService] = None
_ai_bot_service_lock = asyncio.Lock()


async def get_ai_bot_service() -> AIBotService:
    """
    获取全局 AI Bot 服务实例（懒加载）

    Returns:
        AIBotService 实例
    """
    global _ai_bot_service

    if _ai_bot_service is None:
        async with _ai_bot_service_lock:
            if _ai_bot_service is None:
                _ai_bot_service = AIBotService()
                await _ai_bot_service.initialize()

    return _ai_bot_service


async def shutdown_ai_bot_service():
    """关闭全局 AI Bot 服务"""
    global _ai_bot_service

    if _ai_bot_service:
        await _ai_bot_service.shutdown()
        _ai_bot_service = None


# =============================================================================
# 便捷函数
# =============================================================================

async def get_bot_response(user_input: str) -> Tuple[str, float]:
    """
    获取 AI 响应（便捷函数）

    Args:
        user_input: 用户输入

    Returns:
        (响应内容，打字延迟秒数)
    """
    service = await get_ai_bot_service()
    return await service.get_response(user_input)


async def reset_bot_pool():
    """重置 Bot 池（主要用于测试）"""
    await shutdown_ai_bot_service()
    await get_ai_bot_service()
