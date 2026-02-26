#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编译后的 Lua 脚本模块

封装单个 Lua 脚本的编译和执行。
"""

import logging
from typing import Any, Callable, Dict, Optional

try:
    from lupa import LuaRuntime
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False
    LuaRuntime = None

from alice.scripting.base import ScriptConfig

logger = logging.getLogger(__name__)


class CompiledScript:
    """
    编译后的 Lua 脚本

    封装单个 Lua 脚本的编译和执行。

    Attributes:
        script_id: 脚本 ID
        source: 脚本源代码
        config: 脚本配置
        runtime: Lua 运行时
    """

    def __init__(
        self,
        script_id: str,
        source: str,
        config: ScriptConfig,
        runtime: LuaRuntime,
    ):
        """
        初始化编译后的脚本

        Args:
            script_id: 脚本 ID
            source: 脚本源代码
            config: 脚本配置
            runtime: Lua 运行时
        """
        self.script_id = script_id
        self.source = source
        self.config = config
        self.runtime = runtime
        self._compiled = None
        self._functions: Dict[str, Callable] = {}
        self._compile()

    def _compile(self) -> bool:
        """
        编译脚本

        Returns:
            是否编译成功
        """
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
            except Exception:
                pass
            try:
                gen_func = self.runtime.globals().get('generate_response')
                if gen_func:
                    self._functions['generate_response'] = gen_func
            except Exception:
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
        """
        检查函数是否存在

        Args:
            func_name: 函数名

        Returns:
            函数是否存在
        """
        return func_name in self._functions

    def get_function_names(self) -> list[str]:
        """
        获取所有可用函数名称

        Returns:
            函数名称列表
        """
        return list(self._functions.keys())
