#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 机器人主类 - 重构版

使用新的模块化架构：
- 插件系统
- 对话引擎
- 上下文管理
- 统一监控
"""

import logging
import time
from typing import Any, Dict, Optional

from alice.core import DialogueEngine
from alice.services.monitoring_service import UnifiedMonitor, DialogueLogger
from alice.cache import IntelligentCache
from alice.exceptions import (
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
)
from alice.utils.sanitizer import sanitize_text
from config import settings

logger = logging.getLogger(__name__)


class AliceBot:
    """
    Alice 聊天机器人 - 重构版

    新架构特性:
    - 模块化设计：各组件职责清晰
    - 统一监控：性能和错误追踪
    - 智能缓存：减少重复计算
    - 轻量化处理：不依赖重型模型
    """

    def __init__(
        self,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        enable_logging: Optional[bool] = None,
        cache_size: int = 100,
        use_ltp: Optional[bool] = None,
    ):
        """
        初始化 Alice 机器人

        Args:
            script_file: 脚本文件路径
            rules_file: 反射规则文件路径
            enable_logging: 是否启用日志（默认使用 config.ENABLE_LOGGING_BY_DEFAULT）
            cache_size: 缓存大小
            use_ltp: 是否使用 LTP 增强（默认使用 config.ENABLE_LTP_BY_DEFAULT）
        """
        # 使用配置文件的默认值，如果调用方未指定
        self.enable_logging = enable_logging if enable_logging is not None else settings.alice.enable_log

        # 使用默认配置（如果未指定）
        if script_file is None:
            script_file = str(settings.alice.script_file)
        if rules_file is None:
            rules_file = str(settings.alice.rules_file)

        # 对话引擎
        self.dialogue_engine = DialogueEngine(
            script_file=script_file,
            rules_file=rules_file,
            use_ltp=use_ltp,
        )

        # 监控器
        self.monitor = UnifiedMonitor()
        self.dialogue_logger = DialogueLogger() if self.enable_logging else None

        # 缓存
        self.cache = IntelligentCache(max_size=cache_size)

        # 初始化
        self._initialized = False
        self.initialize()

    def initialize(self) -> bool:
        """
        初始化机器人
        
        Returns:
            是否初始化成功
        """
        try:
            # 初始化对话引擎
            success = self.dialogue_engine.initialize()
            if not success:
                logger.error("对话引擎初始化失败")
                return False
            
            self._initialized = True
            logger.info("Alice 机器人初始化成功")
            return True
            
        except Exception as e:
            # 使用结构化日志
            logger.error(
                "Alice 机器人初始化失败",
                extra={
                    'component': 'alice_bot',
                    'error_type': type(e).__name__,
                },
                exc_info=True,
            )
            return False

    def respond(self, user_input: str) -> str:
        """
        生成响应

        Args:
            user_input: 用户输入

        Returns:
            机器人响应
        """
        if not self._initialized:
            return "系统未初始化，请稍后再试"

        # 输入验证 - 空输入返回友好提示（非核心验证，可降级）
        if not user_input or not user_input.strip():
            return "请输入一些内容吧？"

        # 检查缓存
        cached_response = self.cache.get(user_input)
        if cached_response:
            logger.debug(
                "使用缓存响应",
                extra={
                    'component': 'alice_bot',
                    'action': 'cache_hit',
                    'input_preview': sanitize_text(user_input[:20]),
                }
            )
            return cached_response

        start_time = time.time()

        try:
            # 使用对话引擎生成响应
            response = self.dialogue_engine.respond(user_input)

            # 获取规则触发信息
            rule_info = self.dialogue_engine.get_last_rule_info()

            # 记录性能
            duration = time.time() - start_time
            self.monitor.record_interaction(
                request_time=start_time,
                response_time=time.time(),
                success=True,
                metadata={"input_length": len(user_input)},
            )

            # 记录日志（包含规则触发信息）
            if self.enable_logging and self.dialogue_logger:
                self.dialogue_logger.log_dialogue(
                    user_input=user_input,
                    bot_response=response,
                    rule_info=rule_info,
                )
                self.dialogue_logger.log_performance("respond", duration * 1000)

            # 缓存响应
            self.cache.set(user_input, response, ttl=3600)

            return response

        except (InputValidationError, ScriptMatchingError) as e:
            # 业务异常 - 记录并返回友好提示
            logger.warning(
                "对话处理异常",
                extra={
                    'component': 'alice_bot',
                    'error_type': type(e).__name__,
                    'input_preview': sanitize_text(user_input[:50]),
                }
            )
            return "我暂时无法理解这个消息，能换种方式说吗？"
        except ResponseGenerationError as e:
            # 响应生成错误 - 记录错误并返回系统提示
            logger.error(
                "响应生成失败",
                extra={
                    'component': 'alice_bot',
                    'error_type': type(e).__name__,
                    'input_preview': sanitize_text(user_input[:50]),
                },
                exc_info=True,
            )
            return "系统出现故障，请稍后再试"
        except TextProcessingError as e:
            # 文本处理错误
            logger.warning(
                "文本处理失败",
                extra={
                    'component': 'alice_bot',
                    'error_type': type(e).__name__,
                    'input_preview': sanitize_text(user_input[:50]),
                }
            )
            return "我无法处理这个消息，请简化一下内容"
        except Exception as e:
            # 未预期的错误 - 记录详细错误但不降级，让上层处理
            logger.critical(
                "未预期的对话处理错误",
                extra={
                    'component': 'alice_bot',
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'input_preview': sanitize_text(user_input[:50]),
                },
                exc_info=True,
            )
            # 不降级，重新抛出供上层（main.py）处理
            raise ResponseGenerationError(
                f"响应生成失败：{type(e).__name__}",
                context={
                    'error_type': type(e).__name__,
                    'input_length': len(user_input),
                }
            ) from e

    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        summary = self.dialogue_engine.get_context_summary()
        summary["stats"] = self.get_stats()
        return summary

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "initialized": self._initialized,
            "cache": self.cache.get_stats(),
            "monitor": self.monitor.get_stats(),
            "dialogue_engine": self.dialogue_engine.get_stats(),
        }

    def reset(self) -> None:
        """重置对话状态"""
        self.dialogue_engine.reset()
        self.cache.clear()
        logger.info("对话已重置")

    def cleanup(self) -> None:
        """清理资源"""
        self.dialogue_engine.cleanup()
        self.monitor.clear()
        if self.dialogue_logger:
            self.dialogue_logger.clear()
        self._initialized = False
        logger.info("Alice 机器人已清理")


# 向后兼容：保留旧的 AliceBot 引用
# 新代码应该使用上面的 AliceBot 类
OldAliceBot = AliceBot
