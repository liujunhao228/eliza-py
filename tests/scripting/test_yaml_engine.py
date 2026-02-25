#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMLScriptEngine 单元测试
"""

import unittest
import tempfile
import os
from pathlib import Path

from alice.scripting.yaml.engine import YAMLScriptEngine, ScriptIntent
from alice.scripting.context import ScriptContext
from alice.scripting.base import ScriptConfig


class TestYAMLScriptEngine(unittest.TestCase):
    """YAMLScriptEngine 测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时 YAML 脚本文件
        self.test_yaml_content = """
- intent: greeting
  priority: 90
  condition:
    keywords: ["你好", "您好", "嗨"]
  templates:
    - "你好！很高兴见到你。"
    - "您好！有什么可以帮您的吗？"
  
- intent: farewell
  priority: 85
  condition:
    keywords: ["再见", "拜拜", "告辞"]
  templates:
    - "再见！祝你有个美好的一天。"
    - "拜拜！期待下次聊天。"
  
- intent: thanks
  priority: 80
  condition:
    keywords: ["谢谢", "感谢", "多谢"]
  templates:
    - "不客气！"
    - "这是我应该做的。"
  keyword_only: true
"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False,
            encoding='utf-8'
        )
        self.temp_file.write(self.test_yaml_content)
        self.temp_file.close()
        self.script_path = Path(self.temp_file.name)
        
        # 创建引擎
        self.engine = YAMLScriptEngine()
    
    def tearDown(self):
        """测试后清理"""
        try:
            os.unlink(self.script_path)
        except:
            pass
    
    def test_load_script(self):
        """测试加载脚本"""
        config = ScriptConfig(
            script_id="test_script",
            name="Test Script",
            script_type="yaml",
            script_path=self.script_path,
        )
        
        success = self.engine.load_script(config)
        self.assertTrue(success)
        
        # 检查脚本是否已加载
        self.assertIn("test_script", self.engine.scripts)
    
    def test_match_greeting(self):
        """测试问候匹配"""
        # 加载脚本
        config = ScriptConfig(
            script_id="test",
            name="Test",
            script_type="yaml",
            script_path=self.script_path,
        )
        self.engine.load_script(config)
        
        # 测试问候匹配
        context = ScriptContext(
            text="你好，很高兴见到你",
            tokens=["你好", "，", "很", "高兴", "见到", "你"],
        )
        
        match = self.engine.match(context)
        
        self.assertIsNotNone(match)
        self.assertEqual(match.script_type, 'yaml')
        self.assertIn('greeting', match.intent_name)
        self.assertGreater(match.priority, 0)
    
    def test_match_no_keywords(self):
        """测试无关键词匹配"""
        config = ScriptConfig(
            script_id="test",
            name="Test",
            script_type="yaml",
            script_path=self.script_path,
        )
        self.engine.load_script(config)
        
        # 测试无匹配关键词
        context = ScriptContext(
            text="天气怎么样",
            tokens=["天气", "怎么样"],
        )
        
        match = self.engine.match(context)
        
        # 应该没有匹配（因为没有天气相关意图）
        self.assertIsNone(match)
    
    def test_generate_response(self):
        """测试生成响应"""
        config = ScriptConfig(
            script_id="test",
            name="Test",
            script_type="yaml",
            script_path=self.script_path,
        )
        self.engine.load_script(config)
        
        # 先匹配
        context = ScriptContext(
            text="谢谢你的帮助",
            tokens=["谢谢", "你", "的", "帮助"],
        )
        
        match = self.engine.match(context)
        self.assertIsNotNone(match)
        
        # 生成响应
        response = self.engine.generate_response(match.script_id, context)
        
        self.assertIsNotNone(response)
        self.assertIn("test_thanks", response.script_id)
        self.assertTrue(len(response.text) > 0)
    
    def test_fill_placeholders(self):
        """测试占位符填充"""
        config = ScriptConfig(
            script_id="test",
            name="Test",
            script_type="yaml",
            script_path=self.script_path,
        )
        self.engine.load_script(config)
        
        # 创建带实体的上下文
        context = ScriptContext(
            text="你好，我叫小明",
            tokens=["你好", "，", "我", "叫", "小明"],
            entities=[("PERSON", "小明")],
            turn_count=5,
        )
        context.time_context = {"hour": 10}
        context.user_profile = {"name": "张三"}
        
        # 测试实体占位符
        template = "你好，{entity_PERSON}！"
        result = self.engine._fill_placeholders(template, context)
        self.assertEqual(result, "你好，小明！")
        
        # 测试时间占位符
        template = "现在是{time_hour}点"
        result = self.engine._fill_placeholders(template, context)
        self.assertIn("10", result)  # 占位符被替换为值
        
        # 测试用户占位符
        template = "欢迎你，{user_name}"
        result = self.engine._fill_placeholders(template, context)
        self.assertEqual(result, "欢迎你，张三")
        
        # 测试轮数占位符
        template = "这是第{turn_count}轮对话"
        result = self.engine._fill_placeholders(template, context)
        self.assertIn("5", result)  # 占位符被替换为值
    
    def test_condition_entities(self):
        """测试实体条件"""
        yaml_content = """
- intent: person_query
  priority: 75
  condition:
    entities: ["PERSON", "LOCATION"]
  templates:
    - "你在问关于{entity_PERSON}的事情吗？"
"""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(yaml_content)
        temp_file.close()
        
        try:
            config = ScriptConfig(
                script_id="test_entity",
                name="Test Entity",
                script_type="yaml",
                script_path=Path(temp_file.name),
            )
            self.engine.load_script(config)
            
            # 有实体时应该匹配
            context_with_entity = ScriptContext(
                text="小明是谁",
                entities=[("PERSON", "小明")],
            )
            match = self.engine.match(context_with_entity)
            self.assertIsNotNone(match)
            
            # 无实体时不应该匹配
            context_no_entity = ScriptContext(
                text="天气怎么样",
                entities=[],
            )
            match = self.engine.match(context_no_entity)
            self.assertIsNone(match)
            
        finally:
            os.unlink(temp_file.name)
    
    def test_reload_script(self):
        """测试重载脚本"""
        config = ScriptConfig(
            script_id="test",
            name="Test",
            script_type="yaml",
            script_path=self.script_path,
        )
        
        # 首次加载
        self.engine.load_script(config)
        
        # 重载
        success = self.engine.reload_script("test")
        self.assertTrue(success)
    
    def test_get_stats(self):
        """测试统计信息"""
        config = ScriptConfig(
            script_id="test",
            name="Test",
            script_type="yaml",
            script_path=self.script_path,
        )
        self.engine.load_script(config)
        
        stats = self.engine.get_stats()
        
        self.assertEqual(stats['engine_type'], 'yaml')
        self.assertGreater(stats['total_intents'], 0)
        self.assertIn('intents', stats)
    
    def test_priority_sorting(self):
        """测试优先级排序"""
        yaml_content = """
- intent: low_priority
  priority: 30
  condition:
    keywords: ["随便"]
  templates:
    - "随便回复"

- intent: high_priority
  priority: 95
  condition:
    keywords: ["随便", "紧急"]
  templates:
    - "紧急回复"
"""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(yaml_content)
        temp_file.close()
        
        try:
            config = ScriptConfig(
                script_id="priority_test",
                name="Priority Test",
                script_type="yaml",
                script_path=Path(temp_file.name),
            )
            self.engine.load_script(config)
            
            context = ScriptContext(
                text="随便，紧急",
                tokens=["随便", "，", "紧急"],
            )
            
            match = self.engine.match(context)
            
            # 应该匹配高优先级意图
            self.assertIsNotNone(match)
            self.assertEqual(match.priority, 95)
            
        finally:
            os.unlink(temp_file.name)


if __name__ == '__main__':
    unittest.main()
