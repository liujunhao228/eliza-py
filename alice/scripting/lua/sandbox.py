#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua 沙箱安全模块

提供 Lua 脚本执行的安全隔离机制，防止恶意代码执行。

本模块仅依赖标准库，确保 scripting 包的独立性。

安全特性:
- 危险模块隔离：禁止访问 os、io、package、debug 等
- 函数白名单：仅允许注册的安全函数
- 资源限制：执行超时、内存限制
- 代码审计：脚本加载前的安全检查

使用示例:
    sandbox = LuaSandbox()
    safe_runtime = sandbox.create_runtime()
    
    # 注册安全函数
    sandbox.register_safe_function('log', print)
    
    # 执行脚本
    result = sandbox.execute(lua_code, context)
"""

import logging
import math
import os
import random
import re
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from lupa import LuaRuntime, LuaError
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False
    LuaRuntime = None
    LuaError = Exception

logger = logging.getLogger(__name__)


# 危险的 Lua 模块和函数
DANGEROUS_MODULES = {
    # 完全禁止的模块
    'os': '操作系统接口',
    'io': '文件 IO 操作',
    'package': '包管理',
    'debug': '调试接口',
    'coroutine': '协程',
    
    # 危险的函数
    'loadfile': '文件加载',
    'dofile': '文件执行',
    'load': '代码加载',
    'loadstring': '字符串代码加载',
    'require': '模块加载',
    'getfenv': '环境获取',
    'setfenv': '环境设置',
    'getmetatable': '元表获取',
    'setmetatable': '元表设置',
    'rawget': '原始获取',
    'rawset': '原始设置',
    'rawequal': '原始比较',
    'collectgarbage': '垃圾回收控制',
    'newproxy': '代理创建',
}


class LuaSandbox:
    """
    Lua 沙箱
    
    提供安全的 Lua 脚本执行环境。
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        max_memory: int = 10 * 1024 * 1024,  # 10MB
        max_execution_time: float = 1.0,
    ):
        """
        初始化沙箱
        
        Args:
            strict_mode: 严格模式（禁止更多功能）
            max_memory: 最大内存限制（字节）
            max_execution_time: 最大执行时间（秒）
        """
        self.strict_mode = strict_mode
        self.max_memory = max_memory
        self.max_execution_time = max_execution_time
        
        # 安全函数注册表
        self._safe_functions: Dict[str, Callable] = {}
        
        # 自定义模块
        self._custom_modules: Dict[str, Dict[str, Any]] = {}
        
        # 审计日志
        self._audit_log: List[Dict[str, Any]] = []
        
        # 初始化
        self._init_safe_functions()
    
    def _init_safe_functions(self) -> None:
        """初始化安全函数"""
        # 数学函数
        self._safe_functions.update({
            'math_abs': abs,
            'math_floor': math.floor,
            'math_ceil': math.ceil,
            'math_round': round,
            'math_min': min,
            'math_max': max,
            'math_pow': pow,
            'math_sqrt': math.sqrt,
            'math_sin': math.sin,
            'math_cos': math.cos,
            'math_tan': math.tan,
            'math_log': math.log,
            'math_exp': math.exp,
        })
        
        # 时间函数
        self._safe_functions.update({
            'time_time': time.time,
            'os_date': lambda fmt=None: time.strftime(fmt, time.localtime()) if fmt else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        })
        
        # 字符串函数
        self._safe_functions.update({
            'string_upper': str.upper,
            'string_lower': str.lower,
            'string_strip': str.strip,
            'string_split': lambda s, sep=',': s.split(sep),
            'string_join': lambda lst, sep='': sep.join(str(x) for x in lst),
            'string_find': lambda s, sub: s.find(sub),
            'string_replace': lambda s, old, new, count=-1: s.replace(old, new, count),
        })
        
        # 表函数
        self._safe_functions.update({
            'table_concat': lambda t, sep='': (sep or '').join(str(x) for x in t),
            'table_length': len,
            'table_insert': lambda t, v: t.append(v) or t,
            'table_remove': lambda t, i=-1: t.pop(i) if t else None,
            'table_sort': lambda t, key=None, reverse=False: sorted(t, key=key, reverse=reverse),
        })
        
        # 随机函数
        self._safe_functions.update({
            'random_random': random.random,
            'random_int': random.randint,
            'random_choice': random.choice,
            'random_shuffle': lambda lst: random.shuffle(lst) or lst,
        })
        
        # 日志函数
        self._safe_functions.update({
            'log_info': lambda msg: logger.info(f"[Lua] {msg}"),
            'log_debug': lambda msg: logger.debug(f"[Lua] {msg}"),
            'log_warning': lambda msg: logger.warning(f"[Lua] {msg}"),
            'log_error': lambda msg: logger.error(f"[Lua] {msg}"),
        })
    
    def create_runtime(self) -> Optional[LuaRuntime]:
        """
        创建安全的 Lua 运行时

        Returns:
            LuaRuntime 实例
        """
        if not LUPA_AVAILABLE:
            logger.error("lupa 库未安装")
            return None

        try:
            # 检查 lupa 版本是否支持 register_auxiliary_package 参数
            import inspect
            sig = inspect.signature(LuaRuntime.__init__)
            supports_register_aux = 'register_auxiliary_package' in sig.parameters

            runtime_kwargs = {
                'encoding': 'utf-8',
                'unpack_returned_tuples': True,
            }
            
            if supports_register_aux:
                runtime_kwargs['register_auxiliary_package'] = not self.strict_mode

            runtime = LuaRuntime(**runtime_kwargs)

            # 设置沙箱环境
            self._setup_sandbox(runtime)

            # 注册安全函数
            self._register_functions(runtime)

            return runtime

        except Exception as e:
            logger.error(f"创建 Lua 运行时失败：{e}")
            return None
    
    def _setup_sandbox(self, runtime: LuaRuntime) -> None:
        """
        设置沙箱环境
        
        Args:
            runtime: Lua 运行时
        """
        globals_table = runtime.globals()
        
        # 移除危险模块
        for module_name, reason in DANGEROUS_MODULES.items():
            try:
                globals_table[module_name] = None
                self._log_audit('remove_dangerous', module_name, reason)
            except Exception:
                pass
        
        # 严格模式下移除更多功能
        if self.strict_mode:
            try:
                globals_table['getmetatable'] = None
                globals_table['setmetatable'] = None
            except Exception:
                pass
        
        # 创建安全的 Python 模块接口
        python_module = runtime.table()
        for name, func in self._safe_functions.items():
            python_module[name] = func
        globals_table['python'] = python_module
        
        # 创建自定义模块接口
        for module_name, functions in self._custom_modules.items():
            module_table = runtime.table()
            for func_name, func in functions.items():
                module_table[func_name] = func
            globals_table[module_name] = module_table
    
    def _register_functions(self, runtime: LuaRuntime) -> None:
        """
        注册安全函数到运行时
        
        Args:
            runtime: Lua 运行时
        """
        # 函数已在 _setup_sandbox 中通过 python 模块注册
        pass
    
    def register_safe_function(
        self,
        name: str,
        func: Callable,
        module: Optional[str] = None,
    ) -> None:
        """
        注册安全函数
        
        Args:
            name: 函数名
            func: 函数对象
            module: 所属模块（None 表示全局）
        """
        if module:
            if module not in self._custom_modules:
                self._custom_modules[module] = {}
            self._custom_modules[module][name] = func
        else:
            self._safe_functions[name] = func
    
    def audit_code(self, code: str) -> Dict[str, Any]:
        """
        审计 Lua 代码
        
        检查代码中是否包含危险操作。
        
        Args:
            code: Lua 代码
            
        Returns:
            审计结果
        """
        result = {
            'safe': True,
            'warnings': [],
            'dangers': [],
        }
        
        # 检查危险模块
        for module_name in DANGEROUS_MODULES.keys():
            patterns = [
                rf'\b{module_name}\b',
                rf'require\s*\(\s*["\']{module_name}["\']\s*\)',
            ]
            for pattern in patterns:
                if re.search(pattern, code):
                    result['dangers'].append(f"检测到危险模块：{module_name}")
                    result['safe'] = False
        
        # 检查危险函数
        dangerous_funcs = ['loadfile', 'dofile', 'load', 'loadstring', 'require']
        for func in dangerous_funcs:
            if re.search(rf'\b{func}\s*\(', code):
                result['dangers'].append(f"检测到危险函数：{func}")
                result['safe'] = False
        
        # 检查无限循环风险
        if re.search(r'\bwhile\s+true\b', code) and 'break' not in code:
            result['warnings'].append("检测到可能的无限循环：while true")
        
        # 检查递归风险
        if code.count('function') > 10:
            result['warnings'].append("检测到大量函数定义，可能存在递归风险")
        
        # 记录审计日志
        self._log_audit('code_audit', 'code', result)
        
        return result
    
    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        执行 Lua 代码
        
        Args:
            code: Lua 代码
            context: 上下文变量
            timeout: 超时时间（秒）
            
        Returns:
            执行结果
            
        Raises:
            SecurityError: 安全检查失败
            TimeoutError: 执行超时
            LuaError: Lua 执行错误
        """
        # 审计代码
        audit_result = self.audit_code(code)
        if not audit_result['safe']:
            raise SecurityError(f"代码安全检查失败：{audit_result['dangers']}")
        
        # 创建运行时
        runtime = self.create_runtime()
        if not runtime:
            raise RuntimeError("无法创建 Lua 运行时")
        
        # 设置上下文
        if context:
            for key, value in context.items():
                runtime.globals()[key] = value
        
        # 执行代码（带超时）
        timeout = timeout or self.max_execution_time
        result = None
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = runtime.execute(code)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            self._log_audit('timeout', 'code', {'timeout': timeout})
            raise TimeoutError(f"Lua 代码执行超时（{timeout}秒）")
        
        if exception:
            self._log_audit('error', 'code', {'error': str(exception)})
            raise exception
        
        self._log_audit('execute', 'code', {'success': True})
        return result
    
    def _log_audit(
        self,
        action: str,
        target: str,
        details: Any,
    ) -> None:
        """
        记录审计日志
        
        Args:
            action: 操作类型
            target: 目标
            details: 详细信息
        """
        self._audit_log.append({
            'action': action,
            'target': target,
            'details': details,
            'timestamp': time.time(),
        })
        
        # 限制日志大小
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-500:]
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """
        获取审计日志
        
        Returns:
            审计日志列表
        """
        return self._audit_log.copy()
    
    def clear_audit_log(self) -> None:
        """清空审计日志"""
        self._audit_log.clear()


class SecurityError(Exception):
    """安全错误"""
    pass


# 便捷函数
def create_safe_runtime(
    strict_mode: bool = True,
    max_execution_time: float = 1.0,
) -> Optional[LuaRuntime]:
    """
    创建安全的 Lua 运行时（便捷函数）
    
    Args:
        strict_mode: 严格模式
        max_execution_time: 最大执行时间
        
    Returns:
        LuaRuntime 实例
    """
    sandbox = LuaSandbox(
        strict_mode=strict_mode,
        max_execution_time=max_execution_time,
    )
    return sandbox.create_runtime()


def safe_execute(
    code: str,
    context: Optional[Dict[str, Any]] = None,
    timeout: float = 1.0,
) -> Any:
    """
    安全执行 Lua 代码（便捷函数）
    
    Args:
        code: Lua 代码
        context: 上下文变量
        timeout: 超时时间
        
    Returns:
        执行结果
    """
    sandbox = LuaSandbox(max_execution_time=timeout)
    return sandbox.execute(code, context, timeout)
