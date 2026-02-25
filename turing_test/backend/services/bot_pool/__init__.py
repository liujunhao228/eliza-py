"""
Bot 池模块

提供 AliceBot 池管理功能。
"""

import threading
from typing import Dict, Optional

from loguru import logger

from alice.services.shared_nlp_service import SharedNLPService
from config import BotTemplate

from .manager import AliceBotPool
from .instance import BotInstanceInfo
from .config import BotTemplateConfig, create_default_templates

# 全局 Bot 池实例
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
    templates: Optional[Dict[str, BotTemplate]] = None,
    default_template: str = "default",
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
        templates: Bot 模板字典 (模板 ID -> BotTemplate)
        default_template: 默认模板 ID
        min_instances: 最小实例数
        max_instances: 最大实例数
        idle_timeout: 空闲超时时间（秒）
        script_file: 脚本文件路径 (向后兼容)
        rules_file: 规则文件路径 (向后兼容)
        enable_plugins: 是否启用插件 (向后兼容)

    Returns:
        AliceBotPool 实例
    """
    global _bot_pool_instance

    with _bot_pool_lock:
        if _bot_pool_instance is None:
            _bot_pool_instance = AliceBotPool(
                nlp_service=nlp_service,
                templates=templates,
                default_template=default_template,
                min_instances=min_instances,
                max_instances=max_instances,
                idle_timeout=idle_timeout,
                script_file=script_file,
                rules_file=rules_file,
                enable_plugins=enable_plugins,
            )
            logger.info(f"✅ 全局 Bot 池已初始化 (模板数：{len(templates) if templates else 1})")
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


def reset_bot_pool():
    """
    重置全局 Bot 池（用于测试）

    强制关闭现有 Bot 池并清空全局实例，以便重新初始化
    """
    global _bot_pool_instance

    with _bot_pool_lock:
        if _bot_pool_instance:
            _bot_pool_instance.shutdown()
            _bot_pool_instance = None
            logger.info("✅ 全局 Bot 池已重置")


__all__ = [
    "AliceBotPool",
    "BotInstanceInfo",
    "BotTemplateConfig",
    "create_default_templates",
    "get_bot_pool",
    "init_bot_pool",
    "shutdown_bot_pool",
    "reset_bot_pool",
]
