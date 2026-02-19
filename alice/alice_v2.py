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
from alice.managers import ConfigManager
from alice.utils.monitor import UnifiedMonitor, DialogueLogger
from alice.cache import IntelligentCache
from alice.processors import TextPreprocessor

logger = logging.getLogger(__name__)


class AliceBot:
    """
    Alice 聊天机器人 - 重构版
    
    新架构特性:
    - 模块化设计：各组件职责清晰
    - 插件化架构：支持动态扩展
    - 统一监控：性能和错误追踪
    - 智能缓存：减少重复计算
    - 轻量化处理：不依赖重型模型
    """

    def __init__(
        self,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        enable_logging: bool = True,
        enable_plugins: bool = True,
        cache_size: int = 100,
        use_ltp: bool = False,
    ):
        """
        初始化 Alice 机器人

        Args:
            script_file: 脚本文件路径
            rules_file: 反射规则文件路径
            enable_logging: 是否启用日志
            enable_plugins: 是否启用插件系统
            cache_size: 缓存大小
            use_ltp: 是否使用 LTP 增强（默认 False）
        """
        # 配置管理器
        self.config_manager = ConfigManager()

        # 对话引擎
        self.dialogue_engine = DialogueEngine(
            script_file=script_file,
            rules_file=rules_file,
            enable_plugins=enable_plugins,
            use_ltp=use_ltp,
        )
        
        # 监控器
        self.enable_logging = enable_logging
        self.monitor = UnifiedMonitor()
        self.dialogue_logger = DialogueLogger() if enable_logging else None
        
        # 缓存
        self.cache = IntelligentCache(max_size=cache_size)
        
        # 文本预处理
        self.preprocessor = TextPreprocessor()
        
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
            logger.error(f"Alice 机器人初始化失败：{e}", exc_info=True)
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
        
        # 输入验证
        if not user_input or not user_input.strip():
            return "请输入一些内容吧？"
        
        # 检查缓存
        cached_response = self.cache.get(user_input)
        if cached_response:
            logger.debug(f"使用缓存响应：{user_input[:20]}...")
            return cached_response
        
        start_time = time.time()
        
        try:
            # 使用对话引擎生成响应
            response = self.dialogue_engine.respond(user_input)
            
            # 记录性能
            duration = time.time() - start_time
            self.monitor.record_interaction(
                request_time=start_time,
                response_time=time.time(),
                success=True,
                metadata={"input_length": len(user_input)},
            )
            
            # 记录日志
            if self.enable_logging and self.dialogue_logger:
                self.dialogue_logger.log_dialogue(user_input, response)
                self.dialogue_logger.log_performance("respond", duration * 1000)
            
            # 缓存响应
            self.cache.set(user_input, response, ttl=3600)
            
            return response
            
        except Exception as e:
            # 记录错误
            self.monitor.log_error("respond", e, {"input": user_input})
            
            if self.enable_logging and self.dialogue_logger:
                self.dialogue_logger.log_performance("respond", (time.time() - start_time) * 1000, success=False)
            
            logger.error(f"响应生成失败：{e}", exc_info=True)
            return "抱歉，我走神了，能再说一遍吗？"

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
