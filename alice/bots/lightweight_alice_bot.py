"""
轻量级 AliceBot，移除了内置 NLP 组件
通过依赖注入接收 NLP 服务

支持从配置模板创建实例:
    from config import BotTemplate

    template = BotTemplate(
        id="default",
        name="默认 Bot",
        script_file=Path("alice/scripts/demo.yaml"),
        rules_file=Path("alice/scripts/rules/mapping.yaml"),
    )
    bot = LightweightAliceBot.from_template(nlp_service, template)
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional

from alice.core.dialogue_engine import DialogueEngine
from alice.services.shared_nlp_service import SharedNLPService
from alice.utils.monitor import UnifiedMonitor, DialogueLogger
from alice.cache.intelligent_cache import IntelligentCache
from alice.exceptions import (
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
)
from alice.utils.sanitizer import sanitize_text
import logging

logger = logging.getLogger(__name__)


class LightweightAliceBot:
    """
    轻量级 AliceBot，移除了内置 NLP 组件
    通过依赖注入接收 NLP 服务

    支持从配置模板创建实例。
    """

    def __init__(
        self,
        nlp_service: SharedNLPService,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        enable_logging: bool = True,
        cache_size: int = 50,
        use_ltp: bool = False,
    ):
        """
        初始化轻量级 AliceBot

        Args:
            nlp_service: 共享 NLP 服务
            script_file: 脚本文件路径
            rules_file: 规则文件路径
            enable_logging: 是否启用日志
            cache_size: 缓存大小
            use_ltp: 是否使用 LTP（应设为 False 以避免重复加载）
        """
        self.nlp_service = nlp_service

        # 对话引擎（使用外部 NLP 服务）
        # 注意：DialogueEngine 从配置管理器加载配置，不支持直接传入脚本文件路径
        # 这里先创建实例，然后在 initialize 中配置脚本文件
        self._script_file = script_file
        self._rules_file = rules_file
        self._use_ltp = use_ltp

        self.dialogue_engine = DialogueEngine()

        # 监控器
        self.monitor = UnifiedMonitor()
        self.dialogue_logger = DialogueLogger() if enable_logging else None

        # 独立缓存（每个实例）
        self.cache = IntelligentCache(max_size=cache_size)

        # 初始化
        self._initialized = False
        self.initialize()

    @classmethod
    def from_template(
        cls,
        nlp_service: SharedNLPService,
        template: "BotTemplate",
        enable_logging: bool = True,
        use_ltp: bool = False,
    ) -> "LightweightAliceBot":
        """
        从配置模板创建 Bot 实例

        Args:
            nlp_service: 共享 NLP 服务
            template: Bot 配置模板
            enable_logging: 是否启用日志
            use_ltp: 是否使用 LTP

        Returns:
            LightweightAliceBot 实例
        """
        return cls(
            nlp_service=nlp_service,
            script_file=str(template.script_file) if template.script_file else None,
            rules_file=str(template.rules_file) if template.rules_file else None,
            enable_logging=enable_logging,
            cache_size=template.cache_size,
            use_ltp=use_ltp,
        )

    def initialize(self) -> bool:
        """初始化机器人"""
        try:
            # 在初始化前配置脚本文件路径
            if self._script_file:
                self.dialogue_engine.yaml_script_file = self._script_file
            if self._rules_file:
                self.dialogue_engine.rules_file = self._rules_file
            if hasattr(self.dialogue_engine, 'use_ltp'):
                self.dialogue_engine.use_ltp = self._use_ltp

            success = self.dialogue_engine.initialize()
            if not success:
                logger.error("对话引擎初始化失败")
                return False
            self._initialized = True
            logger.info("轻量级 AliceBot 初始化成功")
            return True
        except Exception as e:
            logger.error(f"轻量级 AliceBot 初始化失败：{e}")
            return False

    def respond(self, user_input: str) -> str:
        """生成响应"""
        if not self._initialized:
            return "系统未初始化，请稍后再试"

        # 输入验证 - 空输入返回友好提示
        if not user_input or not user_input.strip():
            return "请输入一些内容吧？"

        # 检查缓存
        cached_response = self.cache.get(user_input)
        if cached_response:
            logger.debug(
                "使用缓存响应",
                extra={
                    'component': 'lightweight_alice_bot',
                    'action': 'cache_hit',
                    'input_preview': sanitize_text(user_input[:20]),
                }
            )
            return cached_response

        start_time = time.time()

        try:
            # 使用外部 NLP 服务进行预处理
            processed_input = user_input

            # 通过对话引擎生成响应
            response = self.dialogue_engine.respond(processed_input)

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
            if self.dialogue_logger:
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
                    'component': 'lightweight_alice_bot',
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
                    'component': 'lightweight_alice_bot',
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
                    'component': 'lightweight_alice_bot',
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
                    'component': 'lightweight_alice_bot',
                    'error_type': type(e).__name__,
                    'input_preview': sanitize_text(user_input[:50]),
                },
                exc_info=True,
            )
            # 不降级，重新抛出供上层处理
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

    def reset(self):
        """重置对话状态（仅重置本实例的上下文）"""
        self.dialogue_engine.reset()
        self.cache.clear()
        logger.info("轻量级 AliceBot 已重置")

    def cleanup(self):
        """清理资源"""
        self.dialogue_engine.cleanup()
        self.monitor.clear()
        if self.dialogue_logger:
            self.dialogue_logger.clear()
        self._initialized = False
        logger.info("轻量级 AliceBot 已清理")
