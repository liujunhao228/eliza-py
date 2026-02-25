#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScriptMatcher 单元测试
"""

import unittest
from alice.scripting.matcher import ScriptMatcher
from alice.scripting.context import ScriptContext
from alice.scripting.base import (
    BaseScriptEngine,
    ScriptConfig,
    ScriptMatchResult,
    ScriptResponse,
)


class MockScriptEngine(BaseScriptEngine):
    """模拟脚本引擎用于测试"""
    
    def __init__(self, engine_type="mock"):
        super().__init__(engine_type=engine_type)
        self._match_result = None
    
    def set_match_result(self, result: ScriptMatchResult):
        """设置匹配结果"""
        self._match_result = result
    
    def load_script(self, config: ScriptConfig) -> bool:
        self.scripts[config.script_id] = config
        return True
    
    def unload_script(self, script_id: str) -> bool:
        if script_id in self.scripts:
            del self.scripts[script_id]
            return True
        return False
    
    def match(self, context: ScriptContext):
        return self._match_result
    
    def generate_response(self, script_id: str, context: ScriptContext):
        return ScriptResponse(
            text=f"Mock response for {script_id}",
            script_id=script_id,
            intent_name=script_id,
        )
    
    def reload_script(self, script_id: str) -> bool:
        return True
    
    def get_stats(self):
        return {'engine_type': self.engine_type}
    
    def _get_extension(self) -> str:
        return "mock"
    
    def _create_config_from_file(self, file_path):
        return None


class TestScriptMatcher(unittest.TestCase):
    """ScriptMatcher 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.matcher = ScriptMatcher()
        self.context = ScriptContext(text="测试文本", tokens=["测试", "文本"])
        
        # 创建模拟引擎
        self.lua_engine = MockScriptEngine(engine_type="lua")
        self.yaml_engine = MockScriptEngine(engine_type="yaml")
    
    def test_register_engine(self):
        """测试注册引擎"""
        success = self.matcher.register_engine('lua', self.lua_engine)
        self.assertTrue(success)
        
        # 重复注册应该失败
        success2 = self.matcher.register_engine('lua', self.lua_engine)
        self.assertFalse(success2)
        
        # 获取引擎
        engine = self.matcher.get_engine('lua')
        self.assertEqual(engine, self.lua_engine)
    
    def test_unregister_engine(self):
        """测试注销引擎"""
        self.matcher.register_engine('lua', self.lua_engine)
        success = self.matcher.unregister_engine('lua')
        self.assertTrue(success)
        
        # 注销后应该获取不到
        engine = self.matcher.get_engine('lua')
        self.assertIsNone(engine)
    
    def test_match_single_engine(self):
        """测试单引擎匹配"""
        self.matcher.register_engine('lua', self.lua_engine)
        
        # 设置匹配结果
        self.lua_engine.set_match_result(ScriptMatchResult(
            script_id="test_script",
            script_type='lua',
            intent_name="test",
            priority=80,
            confidence=0.9,
        ))
        
        match = self.matcher.match(self.context)
        
        self.assertIsNotNone(match)
        self.assertEqual(match.script_id, "test_script")
        self.assertEqual(match.script_type, 'lua')
        self.assertEqual(match.priority, 80)
    
    def test_match_multiple_engines_priority(self):
        """测试多引擎优先级匹配"""
        self.matcher.register_engine('lua', self.lua_engine)
        self.matcher.register_engine('yaml', self.yaml_engine)
        
        # Lua 引擎返回低优先级匹配
        self.lua_engine.set_match_result(ScriptMatchResult(
            script_id="lua_script",
            script_type='lua',
            intent_name="lua_test",
            priority=50,
            confidence=0.8,
        ))
        
        # YAML 引擎返回高优先级匹配
        self.yaml_engine.set_match_result(ScriptMatchResult(
            script_id="yaml_script",
            script_type='yaml',
            intent_name="yaml_test",
            priority=90,
            confidence=0.7,
        ))
        
        match = self.matcher.match(self.context)
        
        # 应该返回高优先级的 YAML 脚本
        self.assertIsNotNone(match)
        self.assertEqual(match.script_type, 'yaml')
        self.assertEqual(match.priority, 90)
    
    def test_match_no_result(self):
        """测试无匹配结果"""
        self.matcher.register_engine('lua', self.lua_engine)
        # 不设置匹配结果
        
        match = self.matcher.match(self.context)
        
        self.assertIsNone(match)
    
    def test_generate_response(self):
        """测试生成响应"""
        self.matcher.register_engine('lua', self.lua_engine)
        
        match = ScriptMatchResult(
            script_id="test",
            script_type='lua',
            intent_name="test",
            priority=50,
            confidence=0.5,
        )
        
        response = self.matcher.generate_response(match, self.context)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.script_id, "test")
        self.assertIn("Mock response", response.text)
    
    def test_list_scripts(self):
        """测试列出脚本"""
        self.matcher.register_engine('lua', self.lua_engine)
        
        # 加载脚本
        self.lua_engine.load_script(ScriptConfig(
            script_id="script1",
            name="Script 1",
            script_type="lua",
        ))
        self.lua_engine.load_script(ScriptConfig(
            script_id="script2",
            name="Script 2",
            script_type="lua",
        ))
        
        scripts = self.matcher.list_scripts()
        
        self.assertIn('lua', scripts)
        self.assertEqual(len(scripts['lua']), 2)
    
    def test_get_stats(self):
        """测试统计信息"""
        self.matcher.register_engine('lua', self.lua_engine)
        
        stats = self.matcher.get_stats()
        
        self.assertIn('registered_engines', stats)
        self.assertIn('lua', stats['registered_engines'])
        self.assertIn('engines', stats)


if __name__ == '__main__':
    unittest.main()
