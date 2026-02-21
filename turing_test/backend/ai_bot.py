"""
AliceBot 与 Turing-Test 集成后的 AI 机器人模块
使用共享 NLP 服务和 Bot 池管理器
"""

import random
from typing import Tuple
from config import settings
from turing_test.backend.bot_pool import AliceBotPool
from alice.services.shared_nlp_service import SharedNLPService


# 全局 NLP 服务
nlp_service = SharedNLPService()
nlp_service.initialize_ltp(settings.turing.nlp_service.enable_ltp)

# 全局 Bot 池
bot_pool = AliceBotPool(
    nlp_service=nlp_service,
    min_instances=settings.turing.bot_pool.min_instances,
    max_instances=settings.turing.bot_pool.max_instances,
    idle_timeout=settings.turing.bot_pool.idle_timeout,
    script_file=settings.turing.alice_bot.script_file,
    rules_file=settings.turing.alice_bot.rules_file,
)


def get_bot_response(user_input: str) -> Tuple[str, float]:
    """
    获取 AI 回复

    Returns:
        (回复内容，打字延迟秒数)
    """
    # 从池中获取 Bot
    bot = bot_pool.acquire_bot()
    if not bot:
        # 如果获取不到 Bot，返回默认回复
        return "抱歉，我现在比较忙，请稍后再试。", 1.0

    try:
        # 生成回复
        response = bot.respond(user_input)

        # 计算打字延迟（模拟人类打字）
        delay = calculate_typing_delay(response)

        return response, delay
    finally:
        # 释放 Bot 回池中
        bot_pool.release_bot(bot)


def calculate_typing_delay(response: str) -> float:
    """
    计算打字延迟，模拟人类打字行为
    """
    base_delay = settings.turing.performance.base_typing_delay
    chars_per_second = settings.turing.performance.chars_per_second

    delay = base_delay + len(response) / chars_per_second
    # 添加随机波动
    delay += random.uniform(-0.5, 0.5)
    return max(0.5, delay)  # 确保最小延迟


def reset_bot():
    """重置 Bot 状态（如果需要）"""
    # 当前实现中，Bot 的状态在每次使用后会保持独立
    # 如果需要重置特定 Bot，可以通过 Bot 池获取并重置
    pass


def get_pool_stats():
    """获取 Bot 池统计信息"""
    return bot_pool.get_stats()
