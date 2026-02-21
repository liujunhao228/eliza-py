"""
AliceBot与Turing-Test集成后的AI机器人模块
使用共享NLP服务和Bot池管理器
"""

import random
from typing import Tuple
from turing_test.backend.config_manager import ConfigManager
from turing_test.backend.bot_pool import AliceBotPool
from alice.services.shared_nlp_service import SharedNLPService


# 全局配置管理器
config_manager = ConfigManager("config/turing_test_config.json")

# 全局NLP服务
nlp_service = SharedNLPService()
nlp_service.initialize_ltp(config_manager.get("nlp_service.enable_ltp", False))

# 全局Bot池
bot_pool = AliceBotPool(
    nlp_service=nlp_service,
    min_instances=config_manager.get("bot_pool.min_instances", 2),
    max_instances=config_manager.get("bot_pool.max_instances", 10),
    idle_timeout=config_manager.get("bot_pool.idle_timeout", 300),
    script_file=config_manager.get("alice_bot.script_file", "alice/scripts/demo.yaml"),
    rules_file=config_manager.get("alice_bot.rules_file", "alice/scripts/rules/mapping.yaml"),
)


def get_bot_response(user_input: str) -> Tuple[str, float]:
    """
    获取AI回复
    
    Returns:
        (回复内容，打字延迟秒数)
    """
    # 从池中获取Bot
    bot = bot_pool.acquire_bot()
    if not bot:
        # 如果获取不到Bot，返回默认回复
        return "抱歉，我现在比较忙，请稍后再试。", 1.0
    
    try:
        # 生成回复
        response = bot.respond(user_input)
        
        # 计算打字延迟（模拟人类打字）
        delay = calculate_typing_delay(response)
        
        return response, delay
    finally:
        # 释放Bot回池中
        bot_pool.release_bot(bot)


def calculate_typing_delay(response: str) -> float:
    """
    计算打字延迟，模拟人类打字行为
    """
    base_delay = config_manager.get("performance.base_typing_delay", 0.5)
    chars_per_second = config_manager.get("performance.chars_per_second", 5.0)
    
    delay = base_delay + len(response) / chars_per_second
    # 添加随机波动
    delay += random.uniform(-0.5, 0.5)
    return max(0.5, delay)  # 确保最小延迟


def reset_bot():
    """重置Bot状态（如果需要）"""
    # 当前实现中，Bot的状态在每次使用后会保持独立
    # 如果需要重置特定Bot，可以通过Bot池获取并重置
    pass


def get_pool_stats():
    """获取Bot池统计信息"""
    return bot_pool.get_stats()

