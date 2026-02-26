#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua 脚本引擎

基于 Lupa 的 Lua 脚本执行引擎，支持：
- 高性能脚本执行
- 沙箱安全隔离
- 热重载支持
- 与 Python 代码无缝交互

使用示例:
    engine = LuaScriptEngine()
    config = ScriptConfig(...)
    engine.load_script(config)
    match = engine.match(context)
"""

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from lupa import LuaRuntime
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False
    LuaRuntime = None

from alice.scripting.base import (
    BaseScriptEngine,
    ScriptConfig,
    ScriptMatchResult,
    ScriptResponse,
)
from alice.scripting.context import ScriptContext
from alice.scripting.config import ScriptConfigLoader
from alice.scripting.lua.sandbox import LuaSandbox
from alice.scripting.lua.compiled_script import CompiledScript

logger = logging.getLogger(__name__)


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
        """获取合适的运行时"""
        if self._runtime:
            return self._runtime

        self._initialize_lua_runtime()
        return self._runtime

    def load_script(self, config: ScriptConfig) -> bool:
        """加载 Lua 脚本"""
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
            content = config.script_path.read_text(encoding='utf-8')
            script_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            if config.script_id in self._scripts:
                if self._script_hashes.get(config.script_id) == script_hash:
                    logger.info(f"Lua 脚本未变更，跳过加载：{config.script_id}")
                    return True

            runtime = self._get_runtime(config)

            script = CompiledScript(
                script_id=config.script_id,
                source=content,
                config=config,
                runtime=runtime,
            )

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
        """匹配 Lua 脚本"""
        self._increment_stat('match_count')

        enabled_scripts = [
            (sid, cfg) for sid, cfg in self.scripts.items()
            if cfg.enabled
        ]
        enabled_scripts.sort(key=lambda x: x[1].priority, reverse=True)

        best_match = None
        best_score = 0.0

        for script_id, config in enabled_scripts:
            script = self._scripts.get(script_id)
            if not script or not script.has_function('match'):
                continue

            try:
                result = self._execute_with_timeout(
                    lambda: script.call('match', context.to_dict()),
                    config.max_execution_time
                )

                if result:
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
        """生成响应"""
        script = self._scripts.get(script_id)
        if not script:
            logger.error(f"脚本不存在：{script_id}")
            return None

        config = self.scripts.get(script_id)
        if not config:
            logger.error(f"脚本配置不存在：{script_id}")
            return None

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

        if script_id in self._scripts:
            del self._scripts[script_id]
        if script_id in self._script_hashes:
            del self._script_hashes[script_id]

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

    def load_from_directory(
        self,
        directory: Path,
        metadata_file: Optional[str] = "metadata.yaml",
    ) -> int:
        """从目录加载脚本"""
        configs = []

        metadata_path = directory / metadata_file if metadata_file else None
        if metadata_path and metadata_path.exists():
            configs.extend(self.config_loader.load_lua_metadata(metadata_path))

        discovered = self.config_loader.scan_directory(directory, script_type='lua')

        config_map = {c.script_id: c for c in configs}
        for script in discovered:
            if script.script_id not in config_map:
                config_map[script.script_id] = script
            else:
                config_map[script.script_id].script_path = script.script_path

        count = 0
        for config in config_map.values():
            if self.load_script(config):
                count += 1

        logger.info(f"从目录加载 {count} 个 Lua 脚本：{directory}")
        return count

    def get_script(self, script_id: str) -> Optional[CompiledScript]:
        """获取编译后的脚本实例"""
        return self._scripts.get(script_id)

    def _execute_with_timeout(self, func: Callable, timeout: float) -> Any:
        """带超时保护地执行函数"""
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
