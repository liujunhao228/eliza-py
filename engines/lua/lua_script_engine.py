"""
Lua脚本引擎 - 支持使用Lua脚本配置Bot，实现灵活的逻辑判断和动态响应

作者: Claude Code
创建时间: 2026-02-24
"""

import asyncio
import hashlib
import logging
import time
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from lupa import LuaRuntime, LuaError
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins
import loguru

from alice.scripts.yaml_script_engine import YAMLScriptEngine, ScriptIntent
from alice.nlp.base import NlpResult
from alice.core.context import Context


@dataclass
class LuaScriptConfig:
    """Lua脚本配置"""
    script_path: Path  # Lua脚本文件路径
    name: str          # 脚本名称
    description: str   # 脚本描述
    priority: int = 50  # 优先级（0-100）
    enabled: bool = True  # 是否启用
    cache_size: int = 100  # 缓存大小
    max_execution_time: float = 1.0  # 最大执行时间（秒）
    sandbox_mode: bool = True  # 是否启用沙箱模式
    variables: Dict[str, Any] = field(default_factory=dict)  # 全局变量


@dataclass
class LuaScriptMatch:
    """Lua脚本匹配结果"""
    script_id: str
    confidence: float
    response: Optional[str]
    variables: Dict[str, Any]
    execution_time: float


class LuaScriptEngine:
    """Lua脚本引擎"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or loguru.logger
        self.lua_runtime: Optional[LuaRuntime] = None
        self.sandbox_runtime: Optional[LuaRuntime] = None
        self.script_cache: Dict[str, Any] = {}
        self.config_cache: Dict[str, LuaScriptConfig] = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_executions': 0,
            'avg_execution_time': 0.0
        }
        self._initialize_lua_runtime()

    def _initialize_lua_runtime(self):
        """初始化Lua运行时"""
        try:
            # 创建标准Lua运行时
            self.lua_runtime = LuaRuntime(
                encoding='utf-8',
                unpack_returned_tuples=True
            )

            # 创建沙箱模式运行时
            self.sandbox_runtime = LuaRuntime(
                encoding='utf-8',
                unpack_returned_tuples=True,
                register_auxiliary_package=False
            )
            self._setup_sandbox_environment()

            # 注册Python函数到Lua
            self._register_python_functions()

            self.logger.info("Lua脚本引擎初始化成功")

        except Exception as e:
            self.logger.error(f"Lua脚本引擎初始化失败: {e}")
            raise

    def _setup_sandbox_environment(self):
        """设置沙箱环境"""
        if not self.sandbox_runtime:
            return

        # 清理危险的全局变量
        dangerous_globals = [
            'os', 'io', 'package', 'debug', 'coroutine',
            'loadfile', 'dofile', 'require'
        ]

        for dangerous in dangerous_globals:
            try:
                self.sandbox_runtime.execute(f"{dangerous} = nil")
            except:
                pass

    def _register_python_functions(self):
        """注册Python函数到Lua环境"""
        if not self.lua_runtime:
            return

        # 注册NLP相关函数
        self.lua_runtime.globals()['nlp'] = {
            'tokenize': self._safe_tokenize,
            'pos_tag': self._safe_pos_tag,
            'ner': self._safe_ner,
            'parse': self._safe_parse
        }

        # 注册上下文相关函数
        self.lua_runtime.globals()['context'] = {
            'get': self._safe_context_get,
            'set': self._safe_context_set,
            'has': self._safe_context_has
        }

        # 注册变量相关函数
        self.lua_runtime.globals()['vars'] = {
            'get': self._safe_vars_get,
            'set': self._safe_vars_set,
            'exists': self._safe_vars_exists
        }

        # 注册数学和时间函数
        self.lua_runtime.globals()['math'] = {
            'random': self._safe_random,
            'time': self._safe_time
        }

    def load_script(self, config: LuaScriptConfig) -> bool:
        """加载Lua脚本"""
        try:
            # 检查脚本文件是否存在
            if not config.script_path.exists():
                self.logger.error(f"脚本文件不存在: {config.script_path}")
                return False

            # 读取脚本内容
            with open(config.script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()

            # 计算脚本哈希用于缓存
            script_hash = hashlib.md5(script_content.encode()).hexdigest()

            # 检查缓存
            if script_hash in self.script_cache:
                self.logger.info(f"脚本已缓存: {config.name}")
                return True

            # 编译脚本
            if config.sandbox_mode and self.sandbox_runtime:
                # 沙箱模式 - 使用RestrictedPython
                compiled_code = compile_restricted(
                    script_content,
                    str(config.script_path),
                    'exec'
                )

                if compiled_code is None:
                    self.logger.error(f"脚本编译失败: {config.name}")
                    return False

                # 创建安全的执行环境
                safe_globals = {
                    '__builtins__': safe_builtins,
                    'print': print,
                }

                exec(compiled_code, safe_globals)
                lua_func = safe_globals.get('match')
            else:
                # 非沙箱模式
                lua_func = self.lua_runtime.execute(script_content)

            if lua_func is None:
                self.logger.error(f"脚本编译失败: {config.name}")
                return False

            # 缓存脚本
            self.script_cache[script_hash] = {
                'func': lua_func,
                'content': script_content,
                'config': config,
                'loaded_at': time.time()
            }
            self.config_cache[config.script_path.stem] = config

            self.logger.info(f"脚本加载成功: {config.name}")
            return True

        except Exception as e:
            self.logger.error(f"加载脚本失败 {config.name}: {e}")
            return False

    def match_script(
        self,
        text: str,
        nlp_result: NLPPipelineResult,
        context: Context,
        script_configs: List[LuaScriptConfig]
    ) -> Optional[LuaScriptMatch]:
        """匹配Lua脚本"""
        if not script_configs:
            return None

        # 按优先级排序
        sorted_scripts = sorted(
            [c for c in script_configs if c.enabled],
            key=lambda x: x.priority,
            reverse=True
        )

        best_match = None
        best_confidence = 0.0

        for config in sorted_scripts:
            try:
                # 执行匹配函数
                match_result = self._execute_match_function(
                    config, text, nlp_result, context
                )

                if match_result and match_result.get('confidence', 0) > best_confidence:
                    best_confidence = match_result['confidence']
                    best_match = LuaScriptMatch(
                        script_id=config.script_path.stem,
                        confidence=best_confidence,
                        response=match_result.get('response'),
                        variables=match_result.get('variables', {}),
                        execution_time=match_result.get('execution_time', 0)
                    )

                    # 如果置信度很高，提前返回
                    if best_confidence >= 0.9:
                        break

            except Exception as e:
                self.logger.warning(f"执行匹配函数失败 {config.name}: {e}")
                continue

        return best_match

    def _execute_match_function(
        self,
        config: LuaScriptConfig,
        text: str,
        nlp_result: NLPPipelineResult,
        context: Context
    ) -> Optional[Dict[str, Any]]:
        """执行匹配函数"""
        start_time = time.time()

        try:
            # 从缓存获取脚本
            script_hash = hashlib.md5(
                open(config.script_path, 'r', encoding='utf-8').read().encode()
            ).hexdigest()

            script_data = self.script_cache.get(script_hash)
            if not script_data:
                # 加载脚本
                if not self.load_script(config):
                    return None
                script_data = self.script_cache.get(script_hash)

            lua_func = script_data['func']

            # 准备Lua环境
            lua_env = {
                'text': text,
                'nlp': nlp_result.to_dict() if nlp_result else {},
                'context': context.to_dict(),
                'config': {
                    'name': config.name,
                    'priority': config.priority,
                    'variables': config.variables
                }
            }

            # 设置执行超时
            def timeout_handler(signum, frame):
                raise TimeoutError(f"脚本执行超时: {config.name}")

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(config.max_execution_time))

            try:
                # 执行匹配函数
                result = lua_func(lua_env)

                # 更新缓存统计
                execution_time = time.time() - start_time
                self.cache_stats['total_executions'] += 1

                return {
                    'confidence': float(result.get('confidence', 0.0)),
                    'response': str(result.get('response', '')) if result.get('response') else None,
                    'variables': result.get('variables', {}),
                    'execution_time': execution_time
                }

            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        except TimeoutError as e:
            self.logger.warning(str(e))
            return None
        except Exception as e:
            self.logger.error(f"执行匹配函数失败 {config.name}: {e}")
            return None

    def generate_response(
        self,
        script_id: str,
        text: str,
        nlp_result: NLPPipelineResult,
        context: Context
    ) -> Optional[str]:
        """生成响应"""
        try:
            config = self.config_cache.get(script_id)
            if not config:
                return None

            # 执行响应函数
            result = self._execute_response_function(
                config, text, nlp_result, context
            )

            return result

        except Exception as e:
            self.logger.error(f"生成响应失败 {script_id}: {e}")
            return None

    def _execute_response_function(
        self,
        config: LuaScriptConfig,
        text: str,
        nlp_result: NLPPipelineResult,
        context: Context
    ) -> Optional[str]:
        """执行响应函数"""
        try:
            # 获取脚本
            script_hash = hashlib.md5(
                open(config.script_path, 'r', encoding='utf-8').read().encode()
            ).hexdigest()

            script_data = self.script_cache.get(script_hash)
            if not script_data:
                return None

            # 检查是否有响应生成函数
            if 'generate_response' not in script_data['func'].__code__.co_names:
                return None

            lua_env = {
                'text': text,
                'nlp': nlp_result.to_dict() if nlp_result else {},
                'context': context.to_dict(),
                'config': {
                    'name': config.name,
                    'priority': config.priority,
                    'variables': config.variables
                }
            }

            # 执行响应函数
            result = script_data['func'].generate_response(lua_env)

            if result and isinstance(result, dict):
                return str(result.get('response', ''))
            elif result:
                return str(result)
            else:
                return None

        except Exception as e:
            self.logger.error(f"执行响应函数失败 {config.name}: {e}")
            return None

    def clear_cache(self):
        """清除缓存"""
        self.script_cache.clear()
        self.config_cache.clear()
        self.logger.info("Lua脚本缓存已清除")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache_stats.copy()

    def _safe_tokenize(self, text: str) -> List[str]:
        """安全的分词函数"""
        try:
            # 这里应该使用实际的分词引擎
            # 为了示例，返回简单的分词
            return text.split()
        except:
            return []

    def _safe_pos_tag(self, tokens: List[str]) -> List[str]:
        """安全的词性标注函数"""
        return ['unknown'] * len(tokens)

    def _safe_ner(self, text: str) -> Dict[str, List[str]]:
        """安全的命名实体识别函数"""
        return {'entities': []}

    def _safe_parse(self, text: str) -> Dict[str, Any]:
        """安全的句法分析函数"""
        return {'tokens': text.split()}

    def _safe_context_get(self, key: str, default=None):
        """安全的上下文获取函数"""
        # 这里应该实际的上下文实现
        return default

    def _safe_context_set(self, key: str, value: Any):
        """安全的上下文设置函数"""
        pass

    def _safe_context_has(self, key: str) -> bool:
        """安全的上下文检查函数"""
        return False

    def _safe_vars_get(self, key: str, default=None):
        """安全的变量获取函数"""
        return default

    def _safe_vars_set(self, key: str, value: Any):
        """安全的变量设置函数"""
        pass

    def _safe_vars_exists(self, key: str) -> bool:
        """安全的变量检查函数"""
        return False

    def _safe_random(self) -> float:
        """安全的随机数函数"""
        import random
        return random.random()

    def _safe_time(self) -> int:
        """安全的获取时间函数"""
        import time
        return int(time.time())


class HybridScriptEngine:
    """混合脚本引擎 - 同时支持YAML和Lua脚本"""

    def __init__(
        self,
        yaml_engine: YAMLScriptEngine,
        lua_engine: LuaScriptEngine,
        logger: Optional[logging.Logger] = None
    ):
        self.yaml_engine = yaml_engine
        self.lua_engine = lua_engine
        self.logger = logger or loguru.logger
        self.script_configs: Dict[str, LuaScriptConfig] = {}

    def add_lua_script(self, config: LuaScriptConfig):
        """添加Lua脚本配置"""
        self.script_configs[config.script_path.stem] = config
        self.lua_engine.load_script(config)

    def load_scripts_from_directory(self, directory: Path):
        """从目录加载所有Lua脚本"""
        if not directory.exists():
            self.logger.warning(f"脚本目录不存在: {directory}")
            return

        for script_file in directory.glob("*.lua"):
            config = LuaScriptConfig(
                script_path=script_file,
                name=script_file.stem,
                description=f"Lua脚本: {script_file.stem}",
                priority=50,
                enabled=True,
                cache_size=100,
                max_execution_time=1.0,
                sandbox_mode=True
            )

            if self.lua_engine.load_script(config):
                self.script_configs[script_file.stem] = config
                self.logger.info(f"加载Lua脚本: {script_file.name}")

    def match(
        self,
        text: str,
        nlp_result: NLPPipelineResult,
        context: Context
    ) -> tuple[Optional[ScriptIntent], Optional[LuaScriptMatch]]:
        """同时匹配YAML和Lua脚本"""
        # 先匹配YAML脚本
        yaml_match = self.yaml_engine.match(text, nlp_result, context)

        # 再匹配Lua脚本
        lua_configs = list(self.script_configs.values())
        lua_match = self.lua_engine.match_script(
            text, nlp_result, context, lua_configs
        )

        # 根据优先级选择最佳匹配
        if yaml_match and lua_match:
            if yaml_match.priority >= lua_match.script_id:
                return yaml_match, None
            else:
                return None, lua_match
        elif yaml_match:
            return yaml_match, None
        elif lua_match:
            return None, lua_match
        else:
            return None, None

    def generate_response(
        self,
        script_id: str,
        text: str,
        nlp_result: NLPPipelineResult,
        context: Context,
        is_lua: bool = False
    ) -> Optional[str]:
        """生成响应"""
        if is_lua:
            return self.lua_engine.generate_response(
                script_id, text, nlp_result, context
            )
        else:
            return self.yaml_engine.generate_response(script_id, text, context)