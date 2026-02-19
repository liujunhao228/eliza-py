#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话主引擎模块

负责对话流程控制，整合各个组件完成对话任务。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from alice.plugins import PluginManager, CuriosityPlugin, PluginResult
from alice.processors import TextPreprocessor, SemanticAnalyzer
from alice.managers import ContextManager
from alice.core.intent_matcher import IntentMatcher
from alice.core.response_generator import ResponseGenerator
from alice.nlp import LtpEngine

logger = logging.getLogger(__name__)


class DialogueEngine:
    """
    对话主引擎
    
    职责:
    - 对话流程控制
    - 组件协调和调度
    - 插件管理
    - 上下文管理
    
    对话流程:
    1. 文本预处理
    2. 语义分析
    3. 意图匹配
    4. 插件处理
    5. 响应生成
    6. 上下文更新
    """

    def __init__(
        self,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        enable_plugins: bool = True,
        use_ltp: bool = False,
    ):
        """
        初始化对话引擎

        Args:
            script_file: 脚本文件路径
            rules_file: 反射规则文件路径
            enable_plugins: 是否启用插件系统
            use_ltp: 是否使用 LTP 增强
        """
        self.enable_plugins = enable_plugins
        self.use_ltp = use_ltp

        # 初始化核心组件
        self.preprocessor = TextPreprocessor()

        # LTP 引擎（可选）
        self.ltp_engine: Optional[LtpEngine] = None
        if use_ltp:
            self.ltp_engine = LtpEngine(lazy_load=True)

        # 语义分析器（可选 LTP 增强）
        self.analyzer = SemanticAnalyzer(
            use_ltp=use_ltp,
            ltp_engine=self.ltp_engine,
        )

        self.context_manager = ContextManager()

        # 意图匹配器
        self.intent_matcher = IntentMatcher()

        # 响应生成器
        self.response_generator = ResponseGenerator(
            rules_file=rules_file,
        )

        # 插件管理器
        self.plugin_manager = PluginManager()
        if enable_plugins:
            self._initialize_plugins(script_file, rules_file)

        # 状态
        self._initialized = False

    def _initialize_plugins(
        self,
        script_file: Optional[str],
        rules_file: Optional[str],
    ) -> None:
        """
        初始化插件系统
        
        Args:
            script_file: 脚本文件路径
            rules_file: 反射规则文件路径
        """
        # 注册好奇心插件
        curiosity_config = {
            "script_file": script_file,
            "rules_file": rules_file,
            "priority": 50,
        }
        
        success = self.plugin_manager.register_plugin(
            name="curiosity",
            plugin_class=CuriosityPlugin,
            config=curiosity_config,
        )
        
        if success:
            logger.info("好奇心插件已注册")
        else:
            logger.warning("好奇心插件注册失败")

    def initialize(self) -> bool:
        """
        初始化引擎
        
        Returns:
            是否初始化成功
        """
        try:
            # 初始化插件
            if self.enable_plugins:
                self.plugin_manager.initialize_all()
            
            self._initialized = True
            logger.info("对话引擎初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"对话引擎初始化失败：{e}")
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
            logger.warning("对话引擎未初始化")
            return "系统未初始化，请稍后再试"
        
        try:
            # 1. 文本预处理
            standardized_text = self.preprocessor.standardize_text(user_input)
            
            # 2. 语义分析
            semantic_info = self.analyzer.analyze(standardized_text)
            
            # 3. 意图匹配
            intent = semantic_info["intent"]
            
            # 4. 插件处理
            plugin_response = self._process_with_plugins(
                standardized_text,
                semantic_info,
            )
            
            # 5. 生成响应
            if plugin_response and plugin_response.success:
                response = plugin_response.response
            else:
                response = self.response_generator.generate(
                    user_input=standardized_text,
                    semantic_info=semantic_info,
                    intent=intent,
                )
            
            # 6. 更新上下文
            self.context_manager.update(
                user_input=user_input,
                bot_response=response,
                entities=semantic_info.get("entities", []),
                sentiment=semantic_info.get("sentiment", 0.0),
                intent=intent,
            )
            
            return response
            
        except Exception as e:
            logger.error(f"对话处理失败：{e}", exc_info=True)
            return "抱歉，我走神了，能再说一遍吗？"

    def _process_with_plugins(
        self,
        text: str,
        semantic_info: Dict[str, Any],
    ) -> Optional[PluginResult]:
        """
        使用插件处理输入
        
        Args:
            text: 标准化文本
            semantic_info: 语义分析结果
            
        Returns:
            插件处理结果
        """
        if not self.enable_plugins:
            return None
        
        context = {
            "semantic_info": semantic_info,
            "recent_turns": self.context_manager.get_recent_turns(3),
        }
        
        results = self.plugin_manager.process_input(text, context)
        
        # 返回第一个成功的结果（按优先级排序）
        for result in results:
            if result.success and result.response:
                return result
        
        return None

    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return self.context_manager.get_context_summary()

    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        stats = {
            "initialized": self._initialized,
            "plugins_enabled": self.enable_plugins,
            "ltp_enabled": self.use_ltp,
            "context": self.context_manager.get_stats(),
        }

        if self.enable_plugins:
            stats["plugins"] = self.plugin_manager.get_stats()

        return stats

    def reset(self) -> None:
        """重置对话状态"""
        self.context_manager.clear()
        if self.enable_plugins:
            for name in ["curiosity"]:
                plugin = self.plugin_manager.get_plugin(name)
                if plugin and hasattr(plugin, "reset"):
                    plugin.reset()
        
        logger.info("对话引擎已重置")

    def cleanup(self) -> None:
        """清理引擎资源"""
        if self.enable_plugins:
            self.plugin_manager.cleanup_all()
        
        self._initialized = False
        logger.info("对话引擎已清理")
