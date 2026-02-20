#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话主引擎模块 - 重构版

负责对话流程控制，整合各个组件完成对话任务。

核心特性:
- 正确调用 NLP 引擎进行句法分析
- 基于 YAML 脚本引擎的意图匹配
- 优先级调度的响应生成
- 插件系统支持
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from alice.plugins import PluginManager, CuriosityPlugin, PluginResult
from alice.processors import TextPreprocessor
from alice.managers import ContextManager
from alice.core.intent_matcher import IntentMatcher, IntentMatch
from alice.core.response_generator import ResponseGenerator
from alice.scripts.yaml_script_engine import YAMLScriptEngine
from alice.nlp.syntax_reassembly import SyntaxReassembly
from alice.nlp.factory import NlpFactory, NlpPipeline
from alice.exceptions import (
    DialogueError,
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
)
from alice.utils.sanitizer import sanitize_text
from alice.config import (
    ENABLE_LTP_BY_DEFAULT,
    ENABLE_NER_BY_DEFAULT,
    NER_USE_LTP_BY_DEFAULT,
)

logger = logging.getLogger(__name__)


class DialogueEngine:
    """
    对话主引擎 - 重构版

    职责:
    - 对话流程控制
    - 组件协调和调度
    - NLP 引擎调用
    - 插件管理
    - 上下文管理

    对话流程:
    1. 文本预处理
    2. NLP 句法分析（可选 LTP）
    3. 语义分析（情感、意图、实体）
    4. YAML 脚本引擎匹配
    5. 插件处理
    6. 响应生成
    7. 上下文更新
    """

    def __init__(
        self,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        enable_plugins: bool = True,
        use_ltp: Optional[bool] = None,
        enable_ner: Optional[bool] = None,
        ner_use_ltp: Optional[bool] = None,
    ):
        """
        初始化对话引擎

        Args:
            script_file: 脚本文件路径
            rules_file: 反射规则文件路径
            enable_plugins: 是否启用插件系统
            use_ltp: 是否使用 LTP 增强（默认使用 config.ENABLE_LTP_BY_DEFAULT）
            enable_ner: 是否启用 NER 实体识别（默认使用 config.ENABLE_NER_BY_DEFAULT）
            ner_use_ltp: NER 是否使用 LTP 增强（默认使用 config.NER_USE_LTP_BY_DEFAULT）
        """
        self.enable_plugins = enable_plugins
        # 使用配置文件的默认值，如果调用方未指定
        self.use_ltp = use_ltp if use_ltp is not None else ENABLE_LTP_BY_DEFAULT
        self.enable_ner = enable_ner if enable_ner is not None else ENABLE_NER_BY_DEFAULT
        self.ner_use_ltp = ner_use_ltp if ner_use_ltp is not None else NER_USE_LTP_BY_DEFAULT

        # 保存配置
        self.script_file = script_file
        self.rules_file = rules_file

        # 初始化核心组件
        self.preprocessor = TextPreprocessor()

        # NLP 工厂（统一管理所有 NLP 引擎）
        nlp_config = {
            'use_ltp': self.use_ltp,
        }
        self.nlp_factory = NlpFactory(config=nlp_config)

        # NLP 流水线（分词 + 实体识别）
        # 分词策略：
        # - 仅使用分词功能时：使用 jieba
        # - 使用高级功能（句法分析、命名实体识别）时：使用 LTP（分词也顺便用 LTP 来做）
        components = []

        # 检查是否使用高级功能
        use_advanced = self.use_ltp or (self.enable_ner and self.ner_use_ltp)

        if use_advanced:
            # 使用 LTP 进行分词和高级分析
            if self.use_ltp:
                components.append('syntax')  # LTP 句法分析（包含分词）
            if self.enable_ner:
                components.append('ner')  # 实体识别
        else:
            # 仅使用 jieba 分词
            components.append('jieba')  # jieba 分词
            if self.enable_ner:
                components.append('ner')  # 基于词典的 NER

        self.nlp_pipeline = self.nlp_factory.create_pipeline(components)

        self.context_manager = ContextManager()

        # YAML 脚本引擎（核心）
        self.script_engine: Optional[YAMLScriptEngine] = None

        # 重组引擎
        self.reassembly_engine: Optional[SyntaxReassembly] = None

        # 意图匹配器（基于 YAML 脚本引擎）
        self.intent_matcher = IntentMatcher()

        # 响应生成器（基于 YAML 脚本引擎）
        self.response_generator = ResponseGenerator()

        # 插件管理器
        self.plugin_manager = PluginManager()

        # 状态
        self._initialized = False
        self._last_intent_match: Optional[IntentMatch] = None

    def initialize(self) -> bool:
        """
        初始化引擎

        Returns:
            是否初始化成功
        """
        try:
            # 1. 初始化 YAML 脚本引擎
            if self.script_file:
                self.script_engine = YAMLScriptEngine(script_file=self.script_file)
                logger.info(f"YAML 脚本引擎已加载，支持 {len(self.script_engine.intents)} 个意图")
            else:
                logger.warning("未指定脚本文件，脚本引擎将不可用")

            # 2. 初始化重组引擎
            if self.rules_file:
                self.reassembly_engine = SyntaxReassembly(rules_file=self.rules_file)
                logger.info("重组引擎已加载")
            else:
                logger.warning("未指定规则文件，重组引擎将不可用")

            # 3. 绑定脚本引擎到意图匹配器
            if self.script_engine:
                self.intent_matcher.set_script_engine(self.script_engine)

            # 4. 绑定脚本引擎和重组引擎到响应生成器
            self.response_generator.set_script_engine(self.script_engine)
            self.response_generator.set_reassembly_engine(self.reassembly_engine)

            # 5. 初始化插件
            if self.enable_plugins:
                self._initialize_plugins()
                self.plugin_manager.initialize_all()

            self._initialized = True
            logger.info("对话引擎初始化成功")
            return True

        except Exception as e:
            logger.error(f"对话引擎初始化失败：{e}", exc_info=True)
            return False

    def _initialize_plugins(self) -> None:
        """
        初始化插件系统
        """
        # 注册好奇心插件
        curiosity_config = {
            "script_file": self.script_file,
            "rules_file": self.rules_file,
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

        start_time = time.time()

        # 1. 文本预处理
        try:
            standardized_text = self.preprocessor.standardize_text(user_input)
        except Exception as e:
            logger.error(
                "文本预处理失败",
                extra={
                    'component': 'dialogue_engine',
                    'step': 'preprocessing',
                    'error_type': type(e).__name__,
                    'input_length': len(user_input),
                    'input_preview': sanitize_text(user_input[:50]),
                },
                exc_info=True,
            )
            raise TextProcessingError(
                f"文本预处理失败：{type(e).__name__}",
                context={
                    'input_length': len(user_input),
                    'error_type': type(e).__name__,
                }
            ) from e

        # 2. NLP 流水线分析（分词 + 实体 + 句法）
        try:
            nlp_result = self.nlp_pipeline.process(standardized_text)

            logger.debug(
                "NLP 分析完成",
                extra={
                    'component': 'nlp_pipeline',
                    'tokens_count': len(nlp_result.tokens),
                    'entities_count': len(nlp_result.entities),
                }
            )
        except Exception as e:
            logger.error(
                "NLP 分析失败",
                extra={
                    'component': 'dialogue_engine',
                    'step': 'nlp_analysis',
                    'error_type': type(e).__name__,
                    'input_length': len(standardized_text),
                    'input_preview': sanitize_text(standardized_text[:50]),
                },
                exc_info=True,
            )
            raise TextProcessingError(
                f"NLP 分析失败：{type(e).__name__}",
                context={
                    'input_length': len(standardized_text),
                    'error_type': type(e).__name__,
                }
            ) from e

        # 3. 构建语义信息
        semantic_info = {
            'tokens': nlp_result.tokens,
            'entities': [(e.entity_type.value, e.text) for e in nlp_result.entities],
            'syntax': nlp_result.syntax.to_dict() if nlp_result.syntax else None,
            'original_text': user_input,
            'standardized_text': standardized_text,
        }

        # 4. 上下文信息注入
        semantic_info['recent_turns'] = self.context_manager.get_recent_turns(3)

        # 5. 意图匹配（基于 YAML 脚本引擎）
        intent_match = self.intent_matcher.match(standardized_text, semantic_info)
        self._last_intent_match = intent_match
        intent = intent_match.intent

        logger.debug(
            f"意图匹配结果：{intent}",
            extra={
                'component': 'intent_matcher',
                'intent': intent,
                'confidence': intent_match.confidence,
                'priority': intent_match.priority,
            }
        )

        # 6. 插件处理（优先级高于响应生成器）
        response = None
        rule_info = {}

        if self.enable_plugins:
            plugin_response = self._process_with_plugins(
                standardized_text,
                semantic_info,
                intent_match,
            )
            if plugin_response and plugin_response.success and plugin_response.response:
                response = plugin_response.response
                rule_info = {
                    "source": "plugin",
                    "plugin_name": "curiosity",
                    "script_id": plugin_response.metadata.get("script_id", "") if plugin_response.metadata else "",
                    "intent": intent,
                    "priority": intent_match.priority,
                }
                logger.debug(
                    f"插件响应：{response[:30]}...",
                    extra={'component': 'plugin', 'source': 'plugin'}
                )

        # 7. 响应生成（如果插件未返回）
        if response is None:
            try:
                response = self.response_generator.generate(
                    user_input=standardized_text,
                    semantic_info=semantic_info,
                    intent=intent,
                    intent_match=intent_match,
                )
                rule_info = {
                    "source": "response_generator",
                    "intent": intent,
                    "priority": intent_match.priority,
                }
                logger.debug(
                    f"响应生成器响应：{response[:30]}...",
                    extra={'component': 'response_generator', 'source': 'response_generator'}
                )
            except Exception as e:
                logger.error(
                    "响应生成失败",
                    extra={
                        'component': 'dialogue_engine',
                        'step': 'response_generation',
                        'error_type': type(e).__name__,
                        'input_length': len(standardized_text),
                        'input_preview': sanitize_text(standardized_text[:50]),
                    },
                    exc_info=True,
                )
                raise ResponseGenerationError(
                    f"响应生成失败：{type(e).__name__}",
                    context={
                        'input_length': len(standardized_text),
                        'error_type': type(e).__name__,
                    }
                ) from e

        # 8. 更新上下文
        try:
            self.context_manager.update(
                user_input=user_input,
                bot_response=response,
                entities=semantic_info.get("entities", []),
                intent=intent,
            )
        except Exception as e:
            logger.error(
                "上下文更新失败",
                extra={
                    'component': 'dialogue_engine',
                    'step': 'context_update',
                    'error_type': type(e).__name__,
                },
                exc_info=True,
            )
            # 上下文更新失败不影响响应返回

        # 记录响应时间
        duration = time.time() - start_time
        logger.debug(
            f"响应生成耗时：{duration*1000:.2f}ms",
            extra={
                'component': 'dialogue_engine',
                'duration_ms': duration * 1000,
            }
        )

        # 保存 rule_info 供上层使用
        self._last_rule_info = rule_info

        return response

    def get_last_rule_info(self) -> Dict[str, Any]:
        """
        获取最后一次响应的规则触发信息

        Returns:
            规则触发信息字典
        """
        return getattr(self, '_last_rule_info', {})

    def _process_with_plugins(
        self,
        text: str,
        semantic_info: Dict[str, Any],
        intent_match: IntentMatch,
    ) -> Optional[PluginResult]:
        """
        使用插件处理输入

        Args:
            text: 标准化文本
            semantic_info: 语义分析结果
            intent_match: 意图匹配结果

        Returns:
            插件处理结果
        """
        if not self.enable_plugins:
            return None

        context = {
            "semantic_info": semantic_info,
            "recent_turns": self.context_manager.get_recent_turns(3),
            "intent_match": intent_match,
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
            "nlp_pipeline": {
                "enabled": self.nlp_pipeline is not None,
            },
            "script_engine": {
                "enabled": self.script_engine is not None,
                "intents_count": len(self.script_engine.intents) if self.script_engine else 0,
            },
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
        self._last_intent_match = None
        logger.info("对话引擎已重置")

    def cleanup(self) -> None:
        """清理引擎资源"""
        if self.enable_plugins:
            self.plugin_manager.cleanup_all()
        self._initialized = False
        logger.info("对话引擎已清理")
