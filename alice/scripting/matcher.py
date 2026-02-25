#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本匹配器模块

统一协调多个脚本引擎（Lua、YAML），实现统一的优先级调度。

本模块仅依赖 scripting 包内的模块，确保 scripting 包的独立性。

设计目标:
- 统一接口：所有脚本引擎使用相同的匹配接口
- 优先级调度：不同引擎的脚本在同一优先级体系下竞争
- 性能优化：支持并行匹配和缓存
- 无外部依赖：仅依赖 scripting.base 和 scripting.context

使用示例:
    matcher = ScriptMatcher()
    
    # 注册引擎
    matcher.register_engine('lua', LuaScriptEngine())
    matcher.register_engine('yaml', YAMLScriptEngine())
    
    # 加载脚本
    lua_engine.load_script(lua_config)
    yaml_engine.load_script(yaml_config)
    
    # 匹配
    context = ScriptContext(text="你好")
    match = matcher.match(context)
    
    if match:
        # 根据 script_type 获取对应的引擎
        engine = matcher.get_engine_by_type(match.script_type)
        response = engine.generate_response(match.script_id, context)
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from alice.scripting.base import (
    BaseScriptEngine,
    ScriptMatchResult,
    ScriptResponse,
)
from alice.scripting.context import ScriptContext

logger = logging.getLogger(__name__)


@dataclass
class MatchRecord:
    """
    匹配记录
    
    Attributes:
        match: 原始匹配结果
        engine: 匹配的引擎
        duration_ms: 匹配耗时（毫秒）
    """
    match: ScriptMatchResult
    engine: BaseScriptEngine
    duration_ms: float = 0.0


class ScriptMatcher:
    """
    脚本匹配器
    
    协调多个脚本引擎，实现统一的优先级调度。
    
    特性:
    - 多引擎支持：同时管理 Lua 和 YAML 引擎
    - 优先级调度：所有脚本在同一优先级体系下竞争
    - 性能统计：记录每个引擎的匹配性能
    - 无外部依赖：仅依赖 scripting 包内模块
    """
    
    def __init__(self, default_timeout: float = 1.0):
        """
        初始化脚本匹配器
        
        Args:
            default_timeout: 默认超时时间（秒）
        """
        self.engines: Dict[str, BaseScriptEngine] = {}
        self.default_timeout = default_timeout
        
        # 统计信息
        self._stats = {
            'total_matches': 0,
            'engine_matches': {},
            'avg_duration_ms': 0.0,
        }
    
    def register_engine(self, name: str, engine: BaseScriptEngine) -> bool:
        """
        注册脚本引擎
        
        Args:
            name: 引擎名称（如 "lua", "yaml"）
            engine: 脚本引擎实例
            
        Returns:
            是否注册成功
        """
        if name in self.engines:
            logger.warning(f"引擎已存在：{name}")
            return False
        
        self.engines[name] = engine
        self._stats['engine_matches'][name] = {
            'matches': 0,
            'hits': 0,
            'total_duration_ms': 0.0,
        }
        
        logger.info(f"脚本引擎已注册：{name} ({engine.engine_type})")
        return True
    
    def unregister_engine(self, name: str) -> bool:
        """
        注销脚本引擎
        
        Args:
            name: 引擎名称
            
        Returns:
            是否注销成功
        """
        if name in self.engines:
            del self.engines[name]
            if name in self._stats['engine_matches']:
                del self._stats['engine_matches'][name]
            logger.info(f"脚本引擎已注销：{name}")
            return True
        return False
    
    def get_engine(self, name: str) -> Optional[BaseScriptEngine]:
        """
        获取脚本引擎
        
        Args:
            name: 引擎名称
            
        Returns:
            脚本引擎实例，不存在时返回 None
        """
        return self.engines.get(name)
    
    def get_engine_by_type(self, script_type: str) -> Optional[BaseScriptEngine]:
        """
        根据脚本类型获取引擎
        
        Args:
            script_type: 脚本类型 ("lua" | "yaml")
            
        Returns:
            脚本引擎实例
        """
        for name, engine in self.engines.items():
            if engine.engine_type == script_type:
                return engine
        return None
    
    def match(
        self,
        context: ScriptContext,
    ) -> Optional[ScriptMatchResult]:
        """
        匹配所有注册的脚本引擎
        
        返回优先级最高的匹配结果。
        
        Args:
            context: 脚本上下文
            
        Returns:
            最佳匹配结果，无匹配时返回 None
        """
        if not self.engines:
            logger.warning("没有注册的脚本引擎")
            return None
        
        start_time = time.time()
        all_matches: List[MatchRecord] = []
        
        # 串行匹配所有引擎
        for engine_name, engine in self.engines.items():
            try:
                match_start = time.time()
                
                # 执行匹配
                match = engine.match(context)
                
                duration_ms = (time.time() - match_start) * 1000
                
                # 更新统计
                self._update_engine_stats(engine_name, match is not None, duration_ms)
                
                if match:
                    all_matches.append(MatchRecord(
                        match=match,
                        engine=engine,
                        duration_ms=duration_ms,
                    ))
                    
                    # 高置信度提前返回
                    if match.confidence >= 0.95:
                        logger.debug(f"高置信度匹配，提前返回：{match.script_id}")
                        break
                        
            except Exception as e:
                logger.error(f"引擎匹配失败 [{engine_name}]: {e}")
        
        total_duration_ms = (time.time() - start_time) * 1000
        self._stats['total_matches'] += 1
        self._update_avg_duration(total_duration_ms)
        
        if not all_matches:
            return None
        
        # 选择最佳匹配（按优先级和置信度）
        best = max(all_matches, key=lambda r: (r.match.priority, r.match.confidence))
        
        logger.debug(
            f"最佳匹配：{best.match.script_id} "
            f"(priority={best.match.priority}, confidence={best.match.confidence:.2f})"
        )
        
        # 记录已匹配脚本
        context.matched_scripts.append(best.match.script_id)
        
        return best.match
    
    def match_all(
        self,
        context: ScriptContext,
    ) -> List[ScriptMatchResult]:
        """
        匹配所有引擎并返回所有匹配结果
        
        Args:
            context: 脚本上下文
            
        Returns:
            所有匹配结果列表，按优先级排序
        """
        if not self.engines:
            return []
        
        all_matches: List[ScriptMatchResult] = []
        
        for engine_name, engine in self.engines.items():
            try:
                match = engine.match(context)
                if match:
                    all_matches.append(match)
            except Exception as e:
                logger.error(f"引擎匹配失败 [{engine_name}]: {e}")
        
        # 按优先级排序
        all_matches.sort(key=lambda m: (m.priority, m.confidence), reverse=True)
        
        return all_matches
    
    def generate_response(
        self,
        match: ScriptMatchResult,
        context: ScriptContext,
    ) -> Optional[ScriptResponse]:
        """
        生成响应
        
        Args:
            match: 匹配结果
            context: 脚本上下文
            
        Returns:
            响应结果
        """
        # 根据 script_type 获取引擎
        engine = self.get_engine_by_type(match.script_type)
        
        if not engine:
            logger.error(f"找不到脚本类型对应的引擎：{match.script_type}")
            return None
        
        return engine.generate_response(match.script_id, context)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        engine_stats = {}
        for name, engine in self.engines.items():
            engine_stats[name] = {
                **engine.get_stats(),
                **self._stats['engine_matches'].get(name, {}),
            }
        
        return {
            'registered_engines': list(self.engines.keys()),
            'total_matches': self._stats['total_matches'],
            'avg_duration_ms': self._stats['avg_duration_ms'],
            'engines': engine_stats,
        }
    
    def clear_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_matches': 0,
            'engine_matches': {
                name: {'matches': 0, 'hits': 0, 'total_duration_ms': 0.0}
                for name in self.engines
            },
            'avg_duration_ms': 0.0,
        }
    
    def list_scripts(self) -> Dict[str, List[str]]:
        """
        列出所有已加载的脚本
        
        Returns:
            {引擎名：[脚本 ID 列表]}
        """
        result = {}
        for name, engine in self.engines.items():
            result[name] = engine.get_script_ids()
        return result
    
    def enable_script(self, engine_name: str, script_id: str) -> bool:
        """启用脚本"""
        engine = self.engines.get(engine_name)
        if engine:
            return engine.enable_script(script_id)
        return False
    
    def disable_script(self, engine_name: str, script_id: str) -> bool:
        """禁用脚本"""
        engine = self.engines.get(engine_name)
        if engine:
            return engine.disable_script(script_id)
        return False
    
    def reload_script(self, engine_name: str, script_id: str) -> bool:
        """热重载脚本"""
        engine = self.engines.get(engine_name)
        if engine:
            return engine.reload_script(script_id)
        return False
    
    def cleanup(self) -> None:
        """清理资源"""
        for engine in self.engines.values():
            if hasattr(engine, 'cleanup'):
                engine.cleanup()
        self.engines.clear()
        logger.info("脚本匹配器已清理")
    
    def _update_engine_stats(
        self,
        engine_name: str,
        hit: bool,
        duration_ms: float,
    ) -> None:
        """更新引擎统计"""
        if engine_name not in self._stats['engine_matches']:
            self._stats['engine_matches'][engine_name] = {
                'matches': 0,
                'hits': 0,
                'total_duration_ms': 0.0,
            }
        
        stats = self._stats['engine_matches'][engine_name]
        stats['matches'] += 1
        if hit:
            stats['hits'] += 1
        stats['total_duration_ms'] += duration_ms
    
    def _update_avg_duration(self, duration_ms: float) -> None:
        """更新平均耗时"""
        total = self._stats['total_matches']
        old_avg = self._stats['avg_duration_ms']
        self._stats['avg_duration_ms'] = (old_avg * (total - 1) + duration_ms) / total
