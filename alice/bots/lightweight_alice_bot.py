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

import random
import time
from pathlib import Path
from typing import Any, Dict, Optional

from alice.core.dialogue_engine import DialogueEngine
from alice.services.shared_nlp_service import SharedNLPService
from alice.services.monitoring_service import UnifiedMonitor, DialogueLogger
from alice.cache.intelligent_cache import IntelligentCache
from alice.exceptions import (
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
)
from alice.utils.sanitizer import sanitize_text
from config.types import OpeningConfig
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
        opening_script: Optional[str] = None,
        opening_config: Optional[OpeningConfig] = None,
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
            opening_script: 开场白脚本文件路径（旧格式，向后兼容）
            opening_config: 开场白配置对象（新格式）
        """
        self.nlp_service = nlp_service

        # 对话引擎（使用外部 NLP 服务）
        # 注意：DialogueEngine 从配置管理器加载配置，不支持直接传入脚本文件路径
        # 这里先创建实例，然后在 initialize 中配置脚本文件
        self._script_file = script_file
        self._rules_file = rules_file
        self._use_ltp = use_ltp
        self._opening_script = opening_script
        self._opening_config = opening_config

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
        # 处理开场白配置：新格式优先，旧格式向后兼容
        opening_config = None
        opening_script = None

        if hasattr(template, 'opening') and template.opening:
            opening_config = template.opening
        elif hasattr(template, 'opening_script') and template.opening_script:
            opening_script = str(template.opening_script)

        return cls(
            nlp_service=nlp_service,
            script_file=str(template.script_file) if template.script_file else None,
            rules_file=str(template.rules_file) if template.rules_file else None,
            enable_logging=enable_logging,
            cache_size=template.cache_size,
            use_ltp=use_ltp,
            opening_script=opening_script,
            opening_config=opening_config,
        )

    def initialize(self) -> bool:
        """初始化机器人"""
        try:
            # 在初始化前配置脚本文件路径
            if self._script_file:
                self.dialogue_engine.yaml_script_file = self._script_file
            if self._rules_file:
                self.dialogue_engine.rules_file = self._rules_file
            if self._opening_script:
                self.dialogue_engine.opening_script_file = self._opening_script
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

    def get_opening_message(self) -> Optional[str]:
        """
        获取开场白消息

        根据配置的概率和策略返回开场白。

        Returns:
            随机开场白，不满足条件时返回 None
        """
        if not self._initialized:
            logger.warning("Bot 未初始化")
            return None

        # 获取有效的开场白配置
        opening_cfg = self._get_effective_opening_config()

        if not opening_cfg:
            # 没有配置开场白，回退到默认行为
            return self.dialogue_engine.get_opening_message("default")

        if not opening_cfg.enabled:
            logger.debug(f"Bot 开场白已禁用")
            return None

        if opening_cfg.strategy == "never":
            logger.debug(f"Bot 策略为 never，不发送开场白")
            return None

        if opening_cfg.strategy == "always":
            # 总是发送，跳过概率检测
            return self._get_raw_opening_message(opening_cfg)

        # 概率检测
        if not self._check_opening_probability(opening_cfg):
            return None

        return self._get_raw_opening_message(opening_cfg)

    def _get_effective_opening_config(self) -> Optional[OpeningConfig]:
        """获取有效的开场白配置"""
        if self._opening_config:
            return self._opening_config
        return None

    def _check_opening_probability(self, cfg: OpeningConfig) -> bool:
        """
        检查是否通过概率检测

        Args:
            cfg: 开场白配置

        Returns:
            是否通过检测
        """
        if cfg.strategy == "first_only":
            # 仅第一次调用时检测，后续保持一致
            if not hasattr(self, '_opening_checked'):
                result = random.random() < cfg.probability
                self._opening_checked = True
                self._opening_result = result
                logger.debug(f"first_only 策略概率检测：{'通过' if result else '未通过'}")
                return result

            return getattr(self, '_opening_result', True)

        # random 策略：每次都检测
        result = random.random() < cfg.probability
        logger.debug(f"random 策略概率检测 ({cfg.probability}): {'通过' if result else '未通过'}")
        return result

    def _get_raw_opening_message(self, cfg: OpeningConfig) -> Optional[str]:
        """
        获取原始开场白消息（不进行概率检测）

        Args:
            cfg: 开场白配置

        Returns:
            开场白消息
        """
        if cfg.script:
            # 使用配置的脚本
            script_id = cfg.script.stem
            if not self.dialogue_engine.yaml_engine:
                logger.warning("YAML 引擎未初始化")
                return None

            # 检查是否已加载，未加载则加载
            if not self.dialogue_engine.yaml_engine.opening_manager.is_loaded(script_id):
                self.dialogue_engine.yaml_engine.load_opening_script(script_id, cfg.script)

            return self.dialogue_engine.yaml_engine.get_opening_message(script_id)

        # 回退到默认开场白
        return self.dialogue_engine.get_opening_message("default")

    def should_send_opening(self) -> bool:
        """
        检查是否应该发送开场白

        Returns:
            是否应该发送
        """
        cfg = self._get_effective_opening_config()
        if not cfg or not cfg.enabled:
            return False
        if cfg.strategy == "never":
            return False
        if cfg.strategy == "always":
            return True
        return self._check_opening_probability(cfg)

    def get_opening_config(self) -> Optional[OpeningConfig]:
        """获取开场白配置"""
        return self._get_effective_opening_config()

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
