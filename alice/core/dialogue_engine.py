#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话主引擎模块 - 重构版本

负责对话流程控制，整合统一脚本引擎架构完成对话任务。

核心特性:
- 统一 Lua 和 YAML 脚本引擎接口
- 基于 ScriptMatcher 的统一优先级调度
- 完整的上下文管理（ScriptContext）
- 配置管理器集成

对话流程:
1. 文本预处理
2. NLP 分析（分词、实体、句法）
3. 构建 ScriptContext
4. ScriptMatcher 统一匹配
5. 响应生成
6. 上下文更新
"""

import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from alice.processors import TextPreprocessor
from alice.core.context_manager import ContextManager
from alice.scripting import (
    ScriptMatcher,
    ScriptContext,
    ScriptConfig,
    ScriptMatchResult,
    ScriptResponse,
    LuaScriptEngine,
    YAMLScriptEngine,
    ScriptConfigLoader,
)
from alice.nlp.factory import NlpFactory, NlpPipeline
from alice.nlp.syntax_reassembly import SyntaxReassembly
from alice.exceptions import DialogueError
from config import Settings, ConfigManager, get_config_manager

logger = logging.getLogger(__name__)


# NLP 流水线单例缓存
_nlp_pipeline_cache: Dict[str, NlpPipeline] = {}


class DialogueEngine:
    """
    对话主引擎 - 重构版本

    职责:
    - 对话流程控制
    - 统一脚本引擎管理（Lua + YAML）
    - NLP 引擎调用
    - 上下文管理

    使用示例:
        # 方式 1：使用默认配置管理器
        engine = DialogueEngine()
        engine.initialize()

        # 方式 2：传入自定义配置管理器
        config_mgr = get_config_manager()
        engine = DialogueEngine(config_manager=config_mgr)
        engine.initialize()

        # 生成响应
        response = engine.respond("你好")
    """

    # 回退响应列表
    FALLBACK_RESPONSES = [
        "我还在思考这个问题，我们可以聊聊别的吗？",
        "这个角度很有意思，能再多说一些吗？",
        "我记下了，稍后给您详细回复。",
    ]

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
    ):
        """
        初始化对话引擎

        Args:
            config_manager: 配置管理器实例，默认使用全局实例

        Raises:
            ImportError: 当依赖库未安装时
        """
        # 配置管理器
        self.config_manager = config_manager or get_config_manager()

        # 从配置管理器获取脚本配置
        scripting_config = self.config_manager.get_scripting_config()

        # 获取 Alice 配置（用于 NLP 等设置）
        alice_config = None
        if hasattr(self.config_manager, '_settings') and self.config_manager._settings:
            alice_config = self.config_manager._settings.alice

        # 脚本配置
        self._load_scripting_config(scripting_config)

        # NLP 配置
        self._load_nlp_config(alice_config)

        # 核心组件初始化
        self.preprocessor = TextPreprocessor()
        self.context_manager = ContextManager()
        self.script_matcher = ScriptMatcher()

        # 脚本引擎（延迟初始化）
        self.lua_engine: Optional[LuaScriptEngine] = None
        self.yaml_engine: Optional[YAMLScriptEngine] = None
        self.config_loader = ScriptConfigLoader()

        # 重组引擎
        self.reassembly_engine: Optional[SyntaxReassembly] = None

        # 状态
        self._initialized = False
        self._last_match_result: Optional[ScriptMatchResult] = None
        self._last_rule_info: Dict[str, Any] = {}

        logger.info("对话引擎实例已创建")

    def _load_scripting_config(self, scripting_config: Optional[Any]) -> None:
        """
        加载脚本配置

        Args:
            scripting_config: 脚本配置对象
        """
        if scripting_config:
            self.yaml_script_file = str(scripting_config.yaml.script_file) if scripting_config.yaml else None
            self.opening_script_file = str(scripting_config.yaml.opening_script_file) if scripting_config.yaml else None
            self.lua_script_dir = str(scripting_config.lua.script_dir) if scripting_config.lua else None
            self.lua_metadata_file = str(scripting_config.lua.metadata_file) if scripting_config.lua else None
            self.rules_file = str(scripting_config.rules_file) if scripting_config.rules_file else None
            self.enable_lua = scripting_config.enable_lua
            self.enable_yaml = scripting_config.enable_yaml
            self.lua_sandbox_mode = scripting_config.lua.sandbox_mode if scripting_config.lua else True
            self.lua_max_execution_time = scripting_config.lua.max_execution_time if scripting_config.lua else 1.0
        else:
            # 默认配置
            self.yaml_script_file = None
            self.opening_script_file = None
            self.lua_script_dir = None
            self.lua_metadata_file = None
            self.rules_file = None
            self.enable_lua = True
            self.enable_yaml = True
            self.lua_sandbox_mode = True
            self.lua_max_execution_time = 1.0

    def _load_nlp_config(self, alice_config: Optional[Any]) -> None:
        """
        加载 NLP 配置

        Args:
            alice_config: Alice 配置对象
        """
        if alice_config:
            self.use_ltp = alice_config.enable_ltp
            self.enable_ner = alice_config.enable_ner
            self.ner_use_ltp = alice_config.ner_use_ltp
        else:
            # 默认配置
            self.use_ltp = True
            self.enable_ner = True
            self.ner_use_ltp = True

    def _init_nlp(self) -> None:
        """
        初始化 NLP 流水线（单例模式）

        组件优先级：LTP > NER > Jieba
        使用缓存避免重复创建 NLP 流水线
        """
        # 生成缓存键
        cache_key = f"ltp={self.use_ltp}:ner={self.enable_ner}:ner_use_ltp={self.ner_use_ltp}"
        
        # 检查缓存
        if cache_key in _nlp_pipeline_cache:
            self.nlp_pipeline = _nlp_pipeline_cache[cache_key]
            self.nlp_factory = None  # 使用缓存时不需要工厂
            logger.info(f"NLP 流水线从缓存加载：{cache_key}")
            return
        
        # 确定组件优先级：LTP > NER > Jieba
        components = []

        if self.use_ltp:
            components.append('ltp')
        elif self.enable_ner and self.ner_use_ltp:
            components.append('ner')
        else:
            components.append('jieba')
            if self.enable_ner:
                components.append('ner')

        # 创建 NLP 工厂和流水线
        nlp_config = {'use_ltp': self.use_ltp}
        self.nlp_factory = NlpFactory(config=nlp_config)

        # LTP 组件额外参数
        ltp_kwargs = {}
        if 'ltp' in components:
            ltp_kwargs = {'enable_srl': True, 'enable_sdp': True}

        self.nlp_pipeline = self.nlp_factory.create_pipeline(components, **ltp_kwargs)
        
        # 存入缓存
        _nlp_pipeline_cache[cache_key] = self.nlp_pipeline

        logger.info(f"NLP 流水线已初始化：{components}")
    
    def initialize(self) -> bool:
        """
        初始化引擎

        Returns:
            是否初始化成功
        """
        try:
            logger.info("开始初始化对话引擎...")

            # 1. 初始化 NLP 流水线
            self._init_nlp()

            # 2. 初始化 YAML 脚本引擎
            if self.enable_yaml and self.yaml_script_file:
                self._init_yaml_engine()

            # 3. 初始化 Lua 脚本引擎
            if self.enable_lua and self.lua_script_dir:
                self._init_lua_engine()

            # 4. 初始化重组引擎
            if self.rules_file:
                self._init_reassembly_engine()

            self._initialized = True
            logger.info(
                f"对话引擎初始化成功，"
                f"已注册引擎：{list(self.script_matcher.engines.keys())}"
            )
            return True

        except Exception as e:
            logger.error(f"对话引擎初始化失败：{e}", exc_info=True)
            return False

    def _init_yaml_engine(self) -> None:
        """
        初始化 YAML 脚本引擎

        使用 ScriptConfigLoader 加载脚本配置。
        """
        script_path = Path(self.yaml_script_file)
        if not script_path.exists():
            logger.warning(f"YAML 脚本文件不存在：{script_path}")
            return

        try:
            # 创建 YAML 引擎
            self.yaml_engine = YAMLScriptEngine(default_script_file=script_path)
            self.script_matcher.register_engine('yaml', self.yaml_engine)

            # 使用配置加载器加载额外脚本
            if self.yaml_engine:
                configs = self.config_loader.load_from_yaml(script_path)
                for config in configs:
                    if config.script_type == 'yaml':
                        self.yaml_engine.load_script(config)

            # 加载开场白脚本
            if self.opening_script_file:
                opening_path = Path(self.opening_script_file)
                if opening_path.exists():
                    self.yaml_engine.load_opening_script("default", opening_path)
                    logger.info(f"开场白脚本已加载：{self.opening_script_file}")
                else:
                    logger.warning(f"开场白脚本文件不存在：{opening_path}")

            logger.info(f"YAML 脚本引擎已加载：{self.yaml_script_file}")

        except Exception as e:
            logger.error(f"YAML 脚本引擎初始化失败：{e}")
            self.enable_yaml = False

    def _init_lua_engine(self) -> None:
        """
        初始化 Lua 脚本引擎

        使用 ScriptConfigLoader 加载元数据和扫描目录。
        """
        try:
            # 创建 Lua 引擎
            self.lua_engine = LuaScriptEngine(
                sandbox_mode=self.lua_sandbox_mode,
                max_execution_time=self.lua_max_execution_time,
            )

            # 从目录加载脚本
            lua_dir = Path(self.lua_script_dir)
            if lua_dir.exists():
                count = self.lua_engine.load_from_directory(
                    lua_dir,
                    metadata_file=self.lua_metadata_file,
                )
                logger.info(f"从目录加载 {count} 个 Lua 脚本：{self.lua_script_dir}")
            else:
                logger.warning(f"Lua 脚本目录不存在：{lua_dir}")

            # 注册到匹配器
            self.script_matcher.register_engine('lua', self.lua_engine)

        except ImportError as e:
            logger.warning(f"Lua 引擎不可用：{e}")
            self.enable_lua = False
        except Exception as e:
            logger.error(f"Lua 引擎初始化失败：{e}", exc_info=True)
            self.enable_lua = False

    def _init_reassembly_engine(self) -> None:
        """初始化重组引擎"""
        try:
            rules_path = Path(self.rules_file)
            if not rules_path.exists():
                logger.warning(f"重组规则文件不存在：{rules_path}")
                return

            self.reassembly_engine = SyntaxReassembly(rules_file=self.rules_file)
            logger.info("重组引擎已加载")

        except Exception as e:
            logger.error(f"重组引擎初始化失败：{e}")
            self.reassembly_engine = None

    def respond(self, user_input: str) -> str:
        """
        生成响应

        对话流程:
        1. 文本预处理
        2. NLP 分析
        3. 构建 ScriptContext
        4. 脚本匹配
        5. 响应生成
        6. 上下文更新

        Args:
            user_input: 用户输入

        Returns:
            机器人响应
        """
        if not self._initialized:
            logger.warning("对话引擎未初始化")
            return "系统未初始化，请稍后再试"

        start_time = time.time()

        try:
            # 1. 文本预处理
            standardized_text = self._preprocess(user_input)

            # 2. NLP 分析
            nlp_result = self._analyze_nlp(standardized_text)

            # 3. 构建 ScriptContext
            context = self._build_context(user_input, standardized_text, nlp_result)

            # 4. 脚本匹配
            match_result = self.script_matcher.match(context)
            self._last_match_result = match_result

            # 5. 响应生成（优先级：脚本 > 回退）
            response, rule_info = self._generate_response_with_priority(
                standardized_text, context, match_result
            )

            # 6. 更新上下文
            self._update_context(user_input, response, context)

            # 记录耗时
            duration = time.time() - start_time
            logger.debug(f"响应生成耗时：{duration*1000:.2f}ms")

            self._last_rule_info = rule_info
            return response

        except Exception as e:
            logger.error(f"对话处理失败：{e}", exc_info=True)
            return "抱歉，我遇到了一些问题，请稍后再试"

    def _generate_response_with_priority(
        self,
        text: str,
        context: ScriptContext,
        match_result: Optional[ScriptMatchResult],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        根据优先级生成响应

        优先级顺序:
        1. 脚本匹配响应
        2. 回退响应

        Args:
            text: 标准化文本
            context: 脚本上下文
            match_result: 脚本匹配结果

        Returns:
            (响应文本，规则信息)
        """
        # 尝试脚本匹配响应
        if match_result:
            script_response = self._generate_script_response(match_result, context)
            if script_response:
                return (
                    script_response,
                    {
                        "source": "script",
                        "script_id": match_result.script_id,
                        "script_type": match_result.script_type,
                        "priority": match_result.priority,
                        "confidence": match_result.confidence,
                    }
                )

        # 回退响应
        return (
            self._fallback_response(),
            {"source": "fallback"}
        )

    def _generate_script_response(
        self,
        match: ScriptMatchResult,
        context: ScriptContext,
    ) -> Optional[str]:
        """
        从脚本匹配生成响应

        Args:
            match: 匹配结果
            context: 上下文

        Returns:
            响应文本，失败时返回 None
        """
        response = self.script_matcher.generate_response(match, context)
        return response.text if response else None
    
    def _preprocess(self, text: str) -> str:
        """文本预处理"""
        return self.preprocessor.standardize_text(text)

    def _analyze_nlp(self, text: str) -> Any:
        """NLP 分析"""
        return self.nlp_pipeline.process(text)

    def _build_context(
        self,
        original: str,
        standardized: str,
        nlp_result: Any,
    ) -> ScriptContext:
        """
        构建 ScriptContext

        Args:
            original: 原始输入
            standardized: 标准化文本
            nlp_result: NLP 分析结果

        Returns:
            脚本上下文
        """
        # 提取实体
        entities = [
            (e.entity_type.value, e.text)
            for e in nlp_result.entities
        ] if hasattr(nlp_result, 'entities') else []

        # 提取句法信息
        syntax = nlp_result.syntax.to_dict() if hasattr(nlp_result, 'syntax') and nlp_result.syntax else None

        # 提取词性和依存关系
        pos_tags, dependencies = self._extract_syntax_info(nlp_result)

        # 时间上下文
        time_context = self.context_manager.get_time_context()

        # 用户画像
        user_profile_dict = self._build_user_profile()

        # 最近对话
        recent_turns = self._get_recent_turns(3)

        return ScriptContext(
            text=standardized,
            tokens=nlp_result.tokens if hasattr(nlp_result, 'tokens') else [],
            entities=entities,
            syntax=syntax,
            pos_tags=pos_tags,
            dependencies=dependencies,
            turn_count=self.context_manager.get_turn_count() + 1,
            recent_turns=recent_turns,
            time_context=time_context,
            user_profile=user_profile_dict,
        )

    def _extract_syntax_info(
        self,
        nlp_result: Any,
    ) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]]]:
        """
        提取句法信息

        Args:
            nlp_result: NLP 结果

        Returns:
            (词性标签列表，依存关系列表)
        """
        pos_tags = []
        dependencies = []

        if hasattr(nlp_result, 'syntax') and nlp_result.syntax:
            syntax = nlp_result.syntax
            words = getattr(syntax, 'words', [])
            poses = getattr(syntax, 'poses', [])
            pos_tags = list(zip(words, poses)) if words and poses else []

            if hasattr(syntax, 'dependencies'):
                dependencies = syntax.dependencies

        return pos_tags, dependencies

    def _build_user_profile(self) -> Dict[str, Any]:
        """
        构建用户画像字典

        Returns:
            用户画像字典
        """
        user_profile = self.context_manager.get_user_profile()
        if not user_profile:
            return {}

        return {
            'name': user_profile.name,
            'nickname': user_profile.nickname,
            'address_form': user_profile.address_form,
        }

    def _get_recent_turns(self, limit: int = 3) -> List[Dict[str, str]]:
        """
        获取最近对话轮次

        Args:
            limit: 最大轮次数

        Returns:
            对话轮次列表
        """
        turns = self.context_manager.get_recent_turns(limit)
        return [
            {'user_input': turn.user_input, 'bot_response': turn.bot_response}
            for turn in turns
        ]

    def _fallback_response(self) -> str:
        """回退响应"""
        return random.choice(self.FALLBACK_RESPONSES)
    
    def _update_context(
        self,
        user_input: str,
        response: str,
        context: ScriptContext,
    ) -> None:
        """
        更新上下文

        Args:
            user_input: 用户输入
            response: 机器人响应
            context: 脚本上下文
        """
        intent = self._last_match_result.intent_name if self._last_match_result else "general"
        self.context_manager.update(
            user_input=user_input,
            bot_response=response,
            entities=context.entities,
            intent=intent,
        )

    def get_last_rule_info(self) -> Dict[str, Any]:
        """获取最后规则信息"""
        return self._last_rule_info.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "initialized": self._initialized,
            "engines": self.script_matcher.get_stats(),
            "context": self.context_manager.get_stats(),
            "nlp": {
                "use_ltp": self.use_ltp,
                "enable_ner": self.enable_ner,
            },
        }

    def reset(self) -> None:
        """重置对话"""
        self.context_manager.clear()
        self._last_match_result = None
        self._last_rule_info = {}

        logger.info("对话引擎已重置")

    def cleanup(self) -> None:
        """清理资源"""
        self.script_matcher.cleanup()
        self._initialized = False

        logger.info("对话引擎已清理")

    # =========================================================================
    # 脚本管理方法
    # =========================================================================

    def get_opening_message(self, script_id: str = "default") -> Optional[str]:
        """
        获取开场白消息

        Args:
            script_id: 脚本 ID，默认为 "default"

        Returns:
            开场白消息，未加载时返回 None
        """
        if not self.yaml_engine:
            logger.warning("YAML 脚本引擎未初始化")
            return None

        return self.yaml_engine.get_opening_message(script_id)

    def reload_yaml_script(self) -> bool:
        """
        重载 YAML 脚本

        Returns:
            是否重载成功
        """
        if not self.yaml_engine or not self.yaml_script_file:
            logger.warning("YAML 脚本引擎未初始化或脚本文件未指定")
            return False

        script_path = Path(self.yaml_script_file)
        config = ScriptConfig(
            script_id=script_path.stem,
            name=script_path.stem,
            script_type="yaml",
            script_path=script_path,
        )
        return self.yaml_engine.reload_script(config.script_id)

    def reload_lua_script(self, script_id: str) -> bool:
        """
        重载 Lua 脚本

        Args:
            script_id: 脚本 ID

        Returns:
            是否重载成功
        """
        if not self.lua_engine:
            logger.warning("Lua 脚本引擎未初始化")
            return False

        return self.lua_engine.reload_script(script_id)

    def reload_all_scripts(self) -> bool:
        """
        重载所有脚本

        Returns:
            是否重载成功
        """
        success = True

        if self.enable_yaml:
            if not self.reload_yaml_script():
                success = False

        if self.enable_lua and self.lua_engine:
            for script_id in list(self.lua_engine.scripts.keys()):
                if not self.lua_engine.reload_script(script_id):
                    success = False

        return success

    def enable_script(self, engine_name: str, script_id: str) -> bool:
        """
        启用脚本

        Args:
            engine_name: 引擎名称
            script_id: 脚本 ID

        Returns:
            是否启用成功
        """
        return self.script_matcher.enable_script(engine_name, script_id)

    def disable_script(self, engine_name: str, script_id: str) -> bool:
        """
        禁用脚本

        Args:
            engine_name: 引擎名称
            script_id: 脚本 ID

        Returns:
            是否禁用成功
        """
        return self.script_matcher.disable_script(engine_name, script_id)

    def list_scripts(self) -> Dict[str, List[str]]:
        """
        列出所有脚本

        Returns:
            {引擎名：[脚本 ID 列表]}
        """
        return self.script_matcher.list_scripts()

    def get_script_info(self, engine_name: str, script_id: str) -> Optional[Dict[str, Any]]:
        """
        获取脚本信息

        Args:
            engine_name: 引擎名称
            script_id: 脚本 ID

        Returns:
            脚本信息字典，不存在时返回 None
        """
        engine = self.script_matcher.get_engine(engine_name)
        if not engine:
            return None

        config = engine.get_script_config(script_id)
        if not config:
            return None

        return config.to_dict()

    def get_loaded_scripts_count(self) -> int:
        """
        获取已加载脚本总数

        Returns:
            脚本总数
        """
        total = 0
        for engine in self.script_matcher.engines.values():
            total += len(engine.scripts)
        return total
