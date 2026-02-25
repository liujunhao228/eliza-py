#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话主引擎模块 - 统一脚本引擎版本

负责对话流程控制，整合统一脚本引擎架构完成对话任务。

核心特性:
- 统一 Lua 和 YAML 脚本引擎接口
- 基于 ScriptMatcher 的统一优先级调度
- 完整的上下文管理（ScriptContext）
- 插件系统支持

对话流程:
1. 文本预处理
2. NLP 分析（分词、实体、句法）
3. 构建 ScriptContext
4. ScriptMatcher 统一匹配
5. 插件处理
6. 响应生成
7. 上下文更新
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from alice.plugins import PluginManager, CuriosityPlugin, PluginResult
from alice.processors import TextPreprocessor
from alice.core.context_manager import ContextManager
from alice.scripting import (
    LuaScriptEngine,
    YAMLScriptEngine,
    ScriptMatcher,
    ScriptConfig,
    ScriptContext,
)
from alice.nlp.factory import NlpFactory, NlpPipeline
from alice.nlp.syntax_reassembly import SyntaxReassembly
from alice.exceptions import (
    DialogueError,
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
)
from alice.utils.sanitizer import sanitize_text
from config import settings, get_config_manager, ConfigManager

logger = logging.getLogger(__name__)


class DialogueEngine:
    """
    对话主引擎 - 统一脚本引擎版本
    
    职责:
    - 对话流程控制
    - 统一脚本引擎管理（Lua + YAML）
    - NLP 引擎调用
    - 插件管理
    - 上下文管理
    """
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
    ):
        """
        初始化对话引擎

        Args:
            config_manager: 配置管理器实例
        """
        # 使用配置管理器或创建默认实例
        self.config_manager = config_manager or get_config_manager()
        
        # 从配置管理器获取脚本配置
        scripting_config = self.config_manager.get_scripting_config()
        
        # 配置保存
        self.yaml_script_file = str(scripting_config.yaml.script_file) if scripting_config.yaml else None
        self.lua_script_dir = str(scripting_config.lua.script_dir) if scripting_config.lua else None
        self.lua_metadata_file = str(scripting_config.lua.metadata_file) if scripting_config.lua else None
        self.rules_file = str(scripting_config.rules_file) if scripting_config else None
        self.enable_lua = scripting_config.enable_lua if scripting_config else True
        self.enable_yaml = scripting_config.enable_yaml if scripting_config else True

        # NLP 配置
        self.use_ltp = settings.alice.enable_ltp
        self.enable_ner = settings.alice.enable_ner
        self.ner_use_ltp = settings.alice.ner_use_ltp

        # Lua 配置 (从配置管理器获取)
        if scripting_config and scripting_config.lua:
            self.lua_sandbox_mode = scripting_config.lua.sandbox_mode
            self.lua_max_execution_time = scripting_config.lua.max_execution_time
        else:
            self.lua_sandbox_mode = True
            self.lua_max_execution_time = 1.0

        # 核心组件
        self.preprocessor = TextPreprocessor()
        self.context_manager = ContextManager()
        
        # NLP 工厂和流水线
        self._init_nlp()
        
        # 统一脚本匹配器
        self.script_matcher = ScriptMatcher()
        
        # 脚本引擎
        self.lua_engine: Optional[LuaScriptEngine] = None
        self.yaml_engine: Optional[YAMLScriptEngine] = None
        
        # 重组引擎
        self.reassembly_engine: Optional[SyntaxReassembly] = None
        
        # 插件管理器
        self.plugin_manager = PluginManager()

        # 状态
        self._initialized = False
        self._last_match_result = None
        self._last_rule_info = {}
    
    def _init_nlp(self) -> None:
        """初始化 NLP 组件"""
        nlp_config = {'use_ltp': self.use_ltp}
        self.nlp_factory = NlpFactory(config=nlp_config)
        
        components = []
        use_advanced = self.use_ltp or (self.enable_ner and self.ner_use_ltp)
        
        if use_advanced:
            if self.use_ltp:
                components.append('ltp')
            elif self.enable_ner:
                components.append('ner')
        else:
            components.append('jieba')
            if self.enable_ner:
                components.append('ner')
        
        ltp_kwargs = {}
        if 'ltp' in components:
            ltp_kwargs = {'enable_srl': True, 'enable_sdp': True}
        
        self.nlp_pipeline = self.nlp_factory.create_pipeline(components, **ltp_kwargs)
        logger.info(f"NLP 流水线已初始化：{components}")
    
    def initialize(self) -> bool:
        """
        初始化引擎
        
        Returns:
            是否初始化成功
        """
        try:
            # 1. 初始化 YAML 脚本引擎
            if self.enable_yaml and self.yaml_script_file:
                self._init_yaml_engine()
            
            # 2. 初始化 Lua 脚本引擎
            if self.enable_lua and self.lua_script_dir:
                self._init_lua_engine()
            
            # 3. 初始化重组引擎
            if self.rules_file:
                self.reassembly_engine = SyntaxReassembly(rules_file=self.rules_file)
                logger.info("重组引擎已加载")
            
            # 4. 初始化插件
            if self.enable_plugins:
                self._initialize_plugins()
                self.plugin_manager.initialize_all()

            self._initialized = True
            logger.info("对话引擎初始化成功")
            logger.info(f"已注册脚本引擎：{list(self.script_matcher.engines.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"对话引擎初始化失败：{e}", exc_info=True)
            return False
    
    def _init_yaml_engine(self) -> None:
        """初始化 YAML 脚本引擎"""
        script_path = Path(self.yaml_script_file)
        if not script_path.exists():
            logger.warning(f"YAML 脚本文件不存在：{script_path}")
            return
        
        self.yaml_engine = YAMLScriptEngine(default_script_file=script_path)
        self.script_matcher.register_engine('yaml', self.yaml_engine)
        logger.info(f"YAML 脚本引擎已加载：{self.yaml_script_file}")
    
    def _init_lua_engine(self) -> None:
        """初始化 Lua 脚本引擎"""
        try:
            self.lua_engine = LuaScriptEngine(
                sandbox_mode=self.lua_sandbox_mode,
                max_execution_time=self.lua_max_execution_time,
            )
            
            # 从目录加载 Lua 脚本
            lua_dir = Path(self.lua_script_dir)
            if lua_dir.exists():
                count = self.lua_engine.load_scripts_from_directory(lua_dir)
                logger.info(f"从目录加载 {count} 个 Lua 脚本：{self.lua_script_dir}")
            
            # 加载元数据配置
            if self.lua_metadata_file:
                self._load_lua_metadata()
            
            self.script_matcher.register_engine('lua', self.lua_engine)
            
        except ImportError as e:
            logger.warning(f"Lua 引擎不可用：{e}")
            self.enable_lua = False
        except Exception as e:
            logger.error(f"Lua 引擎初始化失败：{e}")
            self.enable_lua = False
    
    def _load_lua_metadata(self) -> None:
        """加载 Lua 脚本元数据"""
        try:
            import yaml
            metadata_path = Path(self.lua_metadata_file)
            
            if not metadata_path.exists():
                logger.warning(f"Lua 元数据文件不存在：{metadata_path}")
                return
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or 'scripts' not in data:
                return
            
            for script_data in data['scripts']:
                script_id = script_data.get('name', '')
                if script_id and script_id in self.lua_engine.scripts:
                    config = self.lua_engine.scripts[script_id]
                    config.priority = script_data.get('priority', config.priority)
                    config.description = script_data.get('description', config.description)
                    config.variables.update(script_data.get('variables', {}))
                    config.metadata = script_data
            
            logger.info(f"Lua 脚本元数据已加载：{self.lua_metadata_file}")
            
        except Exception as e:
            logger.warning(f"加载 Lua 元数据失败：{e}")
    
    def _initialize_plugins(self) -> None:
        """初始化插件系统"""
        curiosity_config = {
            "script_file": self.yaml_script_file,
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
        standardized_text = self._preprocess(user_input)
        
        # 2. NLP 分析
        nlp_result = self._analyze_nlp(standardized_text)
        
        # 3. 构建 ScriptContext
        context = self._build_context(user_input, standardized_text, nlp_result)
        
        # 4. 脚本匹配
        match_result = self.script_matcher.match(context)
        self._last_match_result = match_result
        
        # 5. 插件处理（高优先级）
        response = None
        rule_info = {}
        
        if self.enable_plugins:
            plugin_response = self._process_plugins(standardized_text, context)
            if plugin_response and plugin_response.success and plugin_response.response:
                response = plugin_response.response
                rule_info = {
                    "source": "plugin",
                    "plugin_name": "curiosity",
                }
        
        # 6. 响应生成
        if response is None and match_result:
            response = self._generate_response(match_result, context, standardized_text)
            rule_info = {
                "source": "script",
                "script_id": match_result.script_id,
                "script_type": match_result.script_type,
                "priority": match_result.priority,
                "confidence": match_result.confidence,
            }
        
        # 7. 回退响应
        if response is None:
            response = self._fallback_response(context)
            rule_info = {"source": "fallback"}
        
        # 8. 更新上下文
        self._update_context(user_input, response, context)
        
        # 记录耗时
        duration = time.time() - start_time
        logger.debug(f"响应生成耗时：{duration*1000:.2f}ms")
        
        self._last_rule_info = rule_info
        return response
    
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
        """构建 ScriptContext"""
        # 提取实体
        entities = [
            (e.entity_type.value, e.text) 
            for e in nlp_result.entities
        ]
        
        # 提取句法信息
        syntax = nlp_result.syntax.to_dict() if nlp_result.syntax else None
        
        # 提取词性
        pos_tags = []
        dependencies = []
        if nlp_result.syntax:
            words = nlp_result.syntax.words
            poses = nlp_result.syntax.poses
            pos_tags = list(zip(words, poses))
            
            if hasattr(nlp_result.syntax, 'dependencies'):
                dependencies = nlp_result.syntax.dependencies
        
        # 时间上下文
        time_context = self.context_manager.get_time_context()
        
        # 用户画像
        user_profile = self.context_manager.get_user_profile()
        user_profile_dict = {}
        if user_profile:
            user_profile_dict = {
                'name': user_profile.name,
                'nickname': user_profile.nickname,
                'address_form': user_profile.address_form,
            }
        
        # 最近对话
        recent_turns = [
            {'user_input': turn.user_input, 'bot_response': turn.bot_response}
            for turn in self.context_manager.get_recent_turns(3)
        ]
        
        return ScriptContext(
            text=standardized,
            tokens=nlp_result.tokens,
            entities=entities,
            syntax=syntax,
            pos_tags=pos_tags,
            dependencies=dependencies,
            turn_count=self.context_manager.get_turn_count() + 1,
            recent_turns=recent_turns,
            time_context=time_context,
            user_profile=user_profile_dict,
        )
    
    def _process_plugins(
        self,
        text: str,
        context: ScriptContext,
    ) -> Optional[PluginResult]:
        """插件处理"""
        plugin_context = {
            "semantic_info": context.to_dict(),
            "recent_turns": context.recent_turns,
            "match_result": self._last_match_result,
        }
        
        results = self.plugin_manager.process_input(text, plugin_context)
        
        for result in results:
            if result.success and result.response:
                return result
        
        return None
    
    def _generate_response(
        self,
        match: Any,
        context: ScriptContext,
        user_input: str,
    ) -> str:
        """生成响应"""
        response = self.script_matcher.generate_response(match, context)
        
        if response:
            return response.text
        
        # 回退：直接返回
        return self._fallback_response(context)
    
    def _fallback_response(self, context: ScriptContext) -> str:
        """回退响应"""
        fallbacks = [
            "我还在思考这个问题，我们可以聊聊别的吗？",
            "这个角度很有意思，能再多说一些吗？",
            "我记下了，稍后给您详细回复。",
        ]
        import random
        return random.choice(fallbacks)
    
    def _update_context(
        self,
        user_input: str,
        response: str,
        context: ScriptContext,
    ) -> None:
        """更新上下文"""
        self.context_manager.update(
            user_input=user_input,
            bot_response=response,
            entities=context.entities,
            intent=self._last_match_result.intent_name if self._last_match_result else "general",
        )
    
    def get_last_rule_info(self) -> Dict[str, Any]:
        """获取最后规则信息"""
        return self._last_rule_info
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "initialized": self._initialized,
            "engines": self.script_matcher.get_stats(),
            "context": self.context_manager.get_stats(),
            "nlp": {
                "use_ltp": self.use_ltp,
                "enable_ner": self.enable_ner,
            },
            "plugins_enabled": self.enable_plugins,
        }
    
    def reset(self) -> None:
        """重置对话"""
        self.context_manager.clear()
        self._last_match_result = None
        self._last_rule_info = {}
        
        if self.enable_plugins:
            plugin = self.plugin_manager.get_plugin("curiosity")
            if plugin and hasattr(plugin, "reset"):
                plugin.reset()
        
        logger.info("对话引擎已重置")
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.enable_plugins:
            self.plugin_manager.cleanup_all()

        self.script_matcher.cleanup()
        self._initialized = False

        logger.info("对话引擎已清理")
    
    # =========================================================================
    # 脚本管理方法
    # =========================================================================
    
    def reload_yaml_script(self) -> bool:
        """重载 YAML 脚本"""
        if self.yaml_engine and self.yaml_script_file:
            config = ScriptConfig(
                script_id=Path(self.yaml_script_file).stem,
                name=Path(self.yaml_script_file).stem,
                script_type="yaml",
                script_path=Path(self.yaml_script_file),
            )
            return self.yaml_engine.reload_script(config.script_id)
        return False
    
    def reload_lua_script(self, script_id: str) -> bool:
        """重载 Lua 脚本"""
        if self.lua_engine:
            return self.lua_engine.reload_script(script_id)
        return False
    
    def enable_script(self, engine_name: str, script_id: str) -> bool:
        """启用脚本"""
        return self.script_matcher.enable_script(engine_name, script_id)
    
    def disable_script(self, engine_name: str, script_id: str) -> bool:
        """禁用脚本"""
        return self.script_matcher.disable_script(engine_name, script_id)
    
    def list_scripts(self) -> Dict[str, List[str]]:
        """列出所有脚本"""
        return self.script_matcher.list_scripts()
