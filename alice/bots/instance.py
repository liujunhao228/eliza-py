#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 实例封装类

将原有的 AliceBot 功能封装为可多实例的 BotInstance
"""

import logging
import time
from typing import Any, Dict, Optional

from alice.bots.config import BotConfig
from alice.core import DialogueEngine
from alice.managers import ContextManager
from alice.utils.monitor import UnifiedMonitor, DialogueLogger
from alice.cache import IntelligentCache
from alice.services.nlp_service import NlpService
from alice.exceptions import (
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
)
from alice.utils.sanitizer import sanitize_text

logger = logging.getLogger(__name__)


class BotInstance:
    """
    Bot 实例类
    
    每个 Bot 实例拥有:
    - 独立的配置（脚本、规则）
    - 独立的上下文
    - 独立的缓存
    - 共享的 NLP 服务
    """
    
    def __init__(
        self,
        config: BotConfig,
        nlp_service: Optional[NlpService] = None,
    ):
        """
        初始化 Bot 实例
        
        Args:
            config: Bot 配置
            nlp_service: 共享 NLP 服务（可选，默认使用全局单例）
        """
        self.config = config
        self.name = config.name
        self.display_name = config.display_name
        
        # 获取或创建共享 NLP 服务
        self._nlp_service = nlp_service or NlpService.get_instance(
            enable_ltp=config.enable_ltp
        )
        
        # 对话引擎（独立实例）
        self.dialogue_engine = DialogueEngine(
            script_file=config.script_file,
            rules_file=config.rules_file,
            enable_plugins=config.enable_plugins,
            use_ltp=config.enable_ltp,
            enable_ner=config.enable_ner,
            enable_hot_reload=config.enable_hot_reload,
            hot_reload_mode=config.hot_reload_mode,
        )
        
        # 注入共享 NLP 服务到对话引擎
        self._inject_nlp_service()
        
        # 上下文管理器（独立实例）
        self.context_manager = ContextManager()
        
        # 监控器（独立实例）
        self.monitor = UnifiedMonitor()
        self.dialogue_logger = DialogueLogger() if config.enable_logging else None
        
        # 缓存（独立实例）
        self.cache = IntelligentCache(max_size=config.cache_size)
        
        # 状态
        self._initialized = False
        self.initialize()
    
    def _inject_nlp_service(self):
        """将共享 NLP 服务注入到对话引擎"""
        # DialogueEngine 会在 initialize 时使用 NlpFactory
        # 这里我们通过修改 factory 的配置来共享 NLP 服务
        if hasattr(self.dialogue_engine, 'nlp_factory'):
            # 使用共享服务的 factory
            self.dialogue_engine.nlp_factory = self._nlp_service.get_factory()
    
    def initialize(self) -> bool:
        """初始化 Bot 实例"""
        try:
            success = self.dialogue_engine.initialize()
            if not success:
                logger.error(f"Bot[{self.name}] 对话引擎初始化失败")
                return False
            
            self._initialized = True
            logger.info(f"Bot[{self.name}] 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"Bot[{self.name}] 初始化失败：{e}", exc_info=True)
            return False
    
    def respond(self, user_input: str) -> str:
        """
        生成响应
        
        Args:
            user_input: 用户输入
            
        Returns:
            Bot 响应
        """
        if not self._initialized:
            return "系统未初始化，请稍后再试"
        
        if not user_input or not user_input.strip():
            return "请输入一些内容吧？"
        
        # 检查缓存
        cached_response = self.cache.get(user_input)
        if cached_response:
            return cached_response
        
        start_time = time.time()
        
        try:
            response = self.dialogue_engine.respond(user_input)
            duration = time.time() - start_time
            
            # 记录性能
            self.monitor.record_interaction(
                request_time=start_time,
                response_time=time.time(),
                success=True,
            )
            
            # 记录日志
            if self.config.enable_logging and self.dialogue_logger:
                rule_info = self.dialogue_engine.get_last_rule_info()
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
            logger.warning(f"Bot[{self.name}] 输入处理失败：{e}")
            return "我暂时无法理解这个消息，能换种方式说吗？"
        except ResponseGenerationError as e:
            logger.error(f"Bot[{self.name}] 响应生成失败：{e}")
            return "系统出现故障，请稍后再试"
        except Exception as e:
            logger.error(f"Bot[{self.name}] 响应失败：{e}", exc_info=True)
            return "系统出现故障，请稍后再试"
    
    def reset(self) -> None:
        """重置对话状态"""
        self.dialogue_engine.reset()
        self.cache.clear()
        logger.info(f"Bot[{self.name}] 对话已重置")
    
    def cleanup(self) -> None:
        """清理资源"""
        self.dialogue_engine.cleanup()
        self.monitor.clear()
        if self.dialogue_logger:
            self.dialogue_logger.clear()
        self._initialized = False
        logger.info(f"Bot[{self.name}] 已清理")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "initialized": self._initialized,
            "cache": self.cache.get_stats(),
            "monitor": self.monitor.get_stats(),
            "dialogue_engine": self.dialogue_engine.get_stats(),
            "nlp_service": self._nlp_service.get_stats(),
        }
    
    def reload_scripts(self):
        """重载脚本"""
        return self.dialogue_engine.reload_scripts()
    
    def reload_rules(self):
        """重载规则"""
        return self.dialogue_engine.reload_rules()
    
    def reload_all(self):
        """重载所有配置"""
        return self.dialogue_engine.reload_all()
    
    def get_hot_reload_status(self) -> Dict[str, Any]:
        """获取热重载状态"""
        if self.dialogue_engine.hot_reloader:
            return self.dialogue_engine.hot_reloader.get_status()
        return {"enabled": False}
