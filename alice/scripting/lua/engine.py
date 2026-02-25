#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua 脚本引擎

基于 Lupa 的 Lua 脚本执行引擎，支持：
- 高性能脚本执行
- 沙箱安全隔离
- 热重载支持
- 与 Python 代码无缝交互

本模块依赖:
- lupa (外部库)
- scripting.base, scripting.context, scripting.config (内部模块)

使用示例:
    engine = LuaScriptEngine()
    config = ScriptConfig(
        script_id="greeting",
        name="问候脚本",
        script_type="lua",
        priority=90,
        script_path=Path("scripts/lua/greeting.lua"),
    )
    engine.load_script(config)
    
    context = ScriptContext(text="你好", tokens=["你好"])
    match = engine.match(context)
    if match:
        response = engine.generate_response(match.script_id, context)
"""

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from lupa import LuaRuntime, LuaError
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False
    LuaRuntime = None
    LuaError = Exception

from alice.scripting.base import (
    BaseScriptEngine,
    ScriptConfig,
    ScriptMatchResult,
    ScriptResponse,
)
from alice.scripting.context import ScriptContext
from alice.scripting.config import ScriptConfigLoader
from alice.scripting.lua.sandbox import LuaSandbox

logger = logging.getLogger(__name__)


class CompiledScript:
    """
    编译后的 Lua 脚本
    
    封装单个 Lua 脚本的编译和执行。
    """
    
    def __init__(
        self,
        script_id: str,
        source: str,
        config: ScriptConfig,
        runtime: LuaRuntime,
    ):
        self.script_id = script_id
        self.source = source
        self.config = config
        self.runtime = runtime
        self._compiled = None
        self._functions: Dict[str, Callable] = {}
        self._compile()
    
    def _compile(self) -> bool:
        """编译脚本"""
        try:
            self._compiled = self.runtime.execute(self.source)
            self._extract_functions()
            return True
        except Exception as e:
            logger.error(f"Lua 脚本编译失败 [{self.script_id}]: {e}")
            return False
    
    def _extract_functions(self) -> None:
        """从编译结果中提取函数"""
        if self._compiled is None:
            return
        
        # 检查是否返回了表（包含 match 和 generate_response 函数）
        if isinstance(self._compiled, dict):
            if 'match' in self._compiled:
                self._functions['match'] = self._compiled['match']
            if 'generate_response' in self._compiled:
                self._functions['generate_response'] = self._compiled['generate_response']
        # 或者函数可能在全局作用域
        else:
            try:
                match_func = self.runtime.globals().get('match')
                if match_func:
                    self._functions['match'] = match_func
            except:
                pass
            try:
                gen_func = self.runtime.globals().get('generate_response')
                if gen_func:
                    self._functions['generate_response'] = gen_func
            except:
                pass
    
    def call(self, func_name: str, *args) -> Any:
        """
        调用脚本函数
        
        Args:
            func_name: 函数名
            *args: 函数参数
            
        Returns:
            函数返回值
        """
        if func_name not in self._functions:
            logger.warning(f"Lua 脚本 [{self.script_id}] 中不存在函数：{func_name}")
            return None
        
        func = self._functions[func_name]
        try:
            return func(*args)
        except Exception as e:
            logger.error(f"Lua 脚本函数调用失败 [{self.script_id}.{func_name}]: {e}")
            return None
    
    def has_function(self, func_name: str) -> bool:
        """检查函数是否存在"""
        return func_name in self._functions


class LuaScriptEngine(BaseScriptEngine):
    """
    Lua 脚本引擎
    
    特性:
    - 基于 Lupa 的高性能 Lua 执行
    - 沙箱模式隔离危险操作
    - 支持热重载
    - 与 Python 无缝集成
    """
    
    def __init__(
        self,
        sandbox_mode: bool = True,
        max_execution_time: float = 1.0,
        config_loader: Optional[ScriptConfigLoader] = None,
    ):
        """
        初始化 Lua 脚本引擎
        
        Args:
            sandbox_mode: 是否启用沙箱模式
            max_execution_time: 默认最大执行时间（秒）
            config_loader: 配置加载器
        """
        super().__init__(engine_type="lua")
        
        if not LUPA_AVAILABLE:
            raise ImportError(
                "lupa 库未安装，请运行：pip install lupa\n"
                "注意：lupa 需要 LuaJIT 或 Lua 5.1/5.2"
            )
        
        self.sandbox_mode = sandbox_mode
        self.default_max_execution_time = max_execution_time
        self.config_loader = config_loader or ScriptConfigLoader()
        
        # 脚本缓存
        self._scripts: Dict[str, CompiledScript] = {}
        self._script_hashes: Dict[str, str] = {}
        
        # Lua 运行时
        self._runtime: Optional[LuaRuntime] = None
        self._sandbox: Optional[LuaSandbox] = None
        
        # 初始化
        self._initialize_lua_runtime()
    
    def _initialize_lua_runtime(self) -> None:
        """初始化 Lua 运行时"""
        try:
            self._sandbox = LuaSandbox(
                strict_mode=self.sandbox_mode,
                max_execution_time=self.default_max_execution_time,
            )
            self._runtime = self._sandbox.create_runtime()
            
            if self._runtime:
                logger.info("Lua 运行时初始化成功")
            else:
                logger.error("Lua 运行时初始化失败")
                
        except Exception as e:
            logger.error(f"Lua 运行时初始化失败：{e}")
            raise
    
    def _get_runtime(self, script_config: ScriptConfig) -> LuaRuntime:
        """
        获取合适的运行时
        
        Args:
            script_config: 脚本配置
            
        Returns:
            Lua 运行时实例
        """
        if self._runtime:
            return self._runtime
        
        # 如果运行时不存在，重新创建
        self._initialize_lua_runtime()
        return self._runtime
    
    # =========================================================================
    # BaseScriptEngine 接口实现
    # =========================================================================
    
    def load_script(self, config: ScriptConfig) -> bool:
        """
        加载 Lua 脚本
        
        Args:
            config: 脚本配置
            
        Returns:
            是否加载成功
        """
        if config.script_type != "lua":
            logger.error(f"脚本类型不匹配：期望 'lua'，实际 '{config.script_type}'")
            return False
        
        if not config.script_path:
            logger.error(f"脚本路径未指定：{config.script_id}")
            return False
        
        if not config.script_path.exists():
            logger.error(f"脚本文件不存在：{config.script_path}")
            return False
        
        try:
            # 读取脚本内容
            content = config.script_path.read_text(encoding='utf-8')
            
            # 计算哈希用于缓存和热重载
            script_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            # 检查是否需要重新加载
            if config.script_id in self._scripts:
                if self._script_hashes.get(config.script_id) == script_hash:
                    logger.info(f"Lua 脚本未变更，跳过加载：{config.script_id}")
                    return True
            
            # 获取运行时
            runtime = self._get_runtime(config)
            
            # 创建编译后的脚本实例
            script = CompiledScript(
                script_id=config.script_id,
                source=content,
                config=config,
                runtime=runtime,
            )
            
            # 缓存脚本
            self._scripts[config.script_id] = script
            self._script_hashes[config.script_id] = script_hash
            self.scripts[config.script_id] = config
            
            self._increment_stat('load_count')
            logger.info(f"Lua 脚本加载成功：{config.script_id}")
            return True
            
        except Exception as e:
            logger.error(f"Lua 脚本加载失败 [{config.script_id}]: {e}")
            self._increment_stat('error_count')
            return False
    
    def unload_script(self, script_id: str) -> bool:
        """卸载脚本"""
        if script_id in self._scripts:
            del self._scripts[script_id]
            del self._script_hashes[script_id]
            if script_id in self.scripts:
                del self.scripts[script_id]
            logger.info(f"Lua 脚本已卸载：{script_id}")
            return True
        return False
    
    def match(self, context: ScriptContext) -> Optional[ScriptMatchResult]:
        """
        匹配 Lua 脚本
        
        Args:
            context: 脚本上下文
            
        Returns:
            匹配结果
        """
        self._increment_stat('match_count')
        
        # 获取所有启用的脚本，按优先级排序
        enabled_scripts = [
            (sid, cfg) for sid, cfg in self.scripts.items()
            if cfg.enabled
        ]
        enabled_scripts.sort(key=lambda x: x[1].priority, reverse=True)
        
        best_match = None
        best_score = 0.0
        
        for script_id, config in enabled_scripts:
            script = self._scripts.get(script_id)
            if not script:
                continue
            
            if not script.has_function('match'):
                continue
            
            try:
                # 执行匹配函数
                result = self._execute_with_timeout(
                    lambda: script.call('match', context.to_dict()),
                    config.max_execution_time
                )
                
                if result:
                    # 处理不同的返回格式
                    if isinstance(result, bool):
                        matched = result
                        confidence = 0.5
                        priority = config.priority
                    elif isinstance(result, dict):
                        matched = result.get('matched', result.get('confidence', 0) > 0)
                        confidence = float(result.get('confidence', 0.5))
                        priority = int(result.get('priority', config.priority))
                    elif isinstance(result, (int, float)):
                        matched = result > 0
                        confidence = float(result) / 100.0 if result > 1 else float(result)
                        priority = config.priority
                    else:
                        matched = bool(result)
                        confidence = 0.5
                        priority = config.priority
                    
                    if matched:
                        score = priority * 0.7 + confidence * 100 * 0.3
                        if score > best_score:
                            best_score = score
                            best_match = ScriptMatchResult(
                                script_id=script_id,
                                script_type='lua',
                                intent_name=config.name or script_id,
                                priority=priority,
                                confidence=min(confidence, 1.0),
                                metadata={
                                    'raw_result': result,
                                    'config': config.name,
                                }
                            )
                        
                        # 高置信度直接返回
                        if confidence >= 0.9:
                            break
                            
            except Exception as e:
                logger.warning(f"Lua 脚本匹配失败 [{script_id}]: {e}")
                self._increment_stat('error_count')
        
        return best_match
    
    def generate_response(
        self,
        script_id: str,
        context: ScriptContext,
    ) -> Optional[ScriptResponse]:
        """
        生成响应
        
        Args:
            script_id: 脚本 ID
            context: 脚本上下文
            
        Returns:
            响应结果
        """
        script = self._scripts.get(script_id)
        if not script:
            logger.error(f"脚本不存在：{script_id}")
            return None
        
        config = self.scripts.get(script_id)
        if not config:
            logger.error(f"脚本配置不存在：{script_id}")
            return None
        
        # 尝试 generate_response 函数
        if script.has_function('generate_response'):
            try:
                result = self._execute_with_timeout(
                    lambda: script.call('generate_response', context.to_dict()),
                    config.max_execution_time
                )
                
                if result:
                    return ScriptResponse(
                        text=str(result),
                        script_id=script_id,
                        intent_name=config.name or script_id,
                        metadata={'source': 'generate_response'}
                    )
            except Exception as e:
                logger.warning(f"generate_response 执行失败 [{script_id}]: {e}")
        
        # 回退：使用响应模板
        templates = config.metadata.get('templates', [])
        if templates:
            import random
            return ScriptResponse(
                text=random.choice(templates),
                script_id=script_id,
                intent_name=config.name or script_id,
                metadata={'source': 'template'}
            )
        
        return None
    
    def reload_script(self, script_id: str) -> bool:
        """热重载脚本"""
        config = self.scripts.get(script_id)
        if not config:
            logger.error(f"脚本不存在，无法重载：{script_id}")
            return False
        
        # 清除缓存
        if script_id in self._scripts:
            del self._scripts[script_id]
        if script_id in self._script_hashes:
            del self._script_hashes[script_id]
        
        # 重新加载
        return self.load_script(config)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'engine_type': 'lua',
            'loaded_scripts': len(self._scripts),
            'sandbox_mode': self.sandbox_mode,
            **self._stats,
            'scripts': [
                {
                    'id': sid,
                    'name': cfg.name,
                    'priority': cfg.priority,
                    'enabled': cfg.enabled,
                }
                for sid, cfg in self.scripts.items()
            ]
        }
    
    def _get_extension(self) -> str:
        """获取文件扩展名"""
        return "lua"
    
    def _create_config_from_file(self, file_path: Path) -> Optional[ScriptConfig]:
        """从文件创建配置"""
        try:
            script_id = file_path.stem
            
            return ScriptConfig(
                script_id=script_id,
                name=script_id,
                script_type="lua",
                priority=50,
                script_path=file_path,
                description=f"Lua 脚本：{script_id}",
            )
        except Exception as e:
            logger.error(f"创建脚本配置失败 [{file_path}]: {e}")
            return None
    
    # =========================================================================
    # 额外方法
    # =========================================================================
    
    def _execute_with_timeout(self, func: Callable, timeout: float) -> Any:
        """
        带超时保护地执行函数
        
        Args:
            func: 要执行的函数
            timeout: 超时时间（秒）
            
        Returns:
            函数返回值
        """
        result = None
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = func()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"脚本执行超时（{timeout}秒）")
        
        if exception:
            raise exception
        
        return result
    
    def load_from_directory(
        self,
        directory: Path,
        metadata_file: Optional[str] = "metadata.yaml",
    ) -> int:
        """
        从目录加载脚本
        
        Args:
            directory: 脚本目录
            metadata_file: 元数据文件名
            
        Returns:
            成功加载的脚本数量
        """
        configs = []
        
        # 先加载元数据配置
        metadata_path = directory / metadata_file if metadata_file else None
        if metadata_path and metadata_path.exists():
            configs.extend(self.config_loader.load_lua_metadata(metadata_path))
        
        # 扫描目录发现脚本
        discovered = self.config_loader.scan_directory(directory, script_type='lua')
        
        # 合并配置（元数据优先）
        config_map = {c.script_id: c for c in configs}
        for script in discovered:
            if script.script_id not in config_map:
                config_map[script.script_id] = script
            else:
                # 补充路径信息
                config_map[script.script_id].script_path = script.script_path
        
        # 加载所有脚本
        count = 0
        for config in config_map.values():
            if self.load_script(config):
                count += 1
        
        logger.info(f"从目录加载 {count} 个 Lua 脚本：{directory}")
        return count
    
    def get_script(self, script_id: str) -> Optional[CompiledScript]:
        """获取编译后的脚本实例"""
        return self._scripts.get(script_id)
