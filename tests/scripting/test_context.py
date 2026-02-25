#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScriptContext 单元测试
"""

import unittest
from alice.scripting.context import ScriptContext


class TestScriptContext(unittest.TestCase):
    """ScriptContext 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.context = ScriptContext(
            text="你好，我叫小明",
            tokens=["你好", "，", "我", "叫", "小明"],
            entities=[("PERSON", "小明")],
            turn_count=5,
        )
    
    def test_basic_attributes(self):
        """测试基本属性"""
        self.assertEqual(self.context.text, "你好，我叫小明")
        self.assertEqual(len(self.context.tokens), 5)
        self.assertEqual(len(self.context.entities), 1)
        self.assertEqual(self.context.turn_count, 5)
    
    def test_to_dict(self):
        """测试转换为字典"""
        data = self.context.to_dict()
        
        self.assertIn('text', data)
        self.assertIn('tokens', data)
        self.assertIn('entities', data)
        self.assertEqual(data['text'], "你好，我叫小明")
        self.assertEqual(len(data['tokens']), 5)
    
    def test_get_method(self):
        """测试 get 方法"""
        self.assertEqual(self.context.get('text'), "你好，我叫小明")
        self.assertEqual(self.context.get('turn_count'), 5)
        self.assertEqual(self.context.get('nonexistent', 'default'), 'default')
    
    def test_has_method(self):
        """测试 has 方法"""
        self.assertTrue(self.context.has('text'))
        self.assertFalse(self.context.has('nonexistent'))
    
    def test_variable_management(self):
        """测试变量管理"""
        # 设置变量
        self.context.set_variable('mood', 'happy')
        self.assertEqual(self.context.get_variable('mood'), 'happy')
        
        # 检查变量存在
        self.assertTrue(self.context.has_variable('mood'))
        
        # 移除变量
        self.context.remove_variable('mood')
        self.assertFalse(self.context.has_variable('mood'))
    
    def test_freeze_readonly(self):
        """测试只读冻结"""
        frozen = self.context.freeze()
        
        self.assertTrue(frozen.is_readonly())
        
        # 只读模式下无法设置变量
        with self.assertRaises(RuntimeError):
            frozen.set_variable('test', 'value')
    
    def test_entity_queries(self):
        """测试实体查询"""
        # 获取特定类型实体
        persons = self.context.get_entity_by_type('PERSON')
        self.assertEqual(persons, ['小明'])
        
        # 获取第一个实体
        first = self.context.get_first_entity('PERSON')
        self.assertEqual(first, '小明')
        
        # 检查实体存在
        self.assertTrue(self.context.has_entity('PERSON'))
        self.assertFalse(self.context.has_entity('LOCATION'))
    
    def test_syntax_access(self):
        """测试句法访问"""
        # 设置句法信息
        self.context.syntax = {
            'subject': '我',
            'predicate': '叫',
            'object': '小明',
        }
        
        self.assertEqual(self.context.get_subject(), '我')
        self.assertEqual(self.context.get_predicate(), '叫')
        self.assertEqual(self.context.get_object(), '小明')
    
    def test_time_context(self):
        """测试时间上下文"""
        self.context.time_context = {
            'hour': 10,
            'weekday': 2,
            'category_time': '早晨',
        }
        
        self.assertEqual(self.context.get_time('hour'), 10)
        self.assertEqual(self.context.get_time('nonexistent', 'default'), 'default')
    
    def test_user_profile(self):
        """测试用户画像"""
        self.context.user_profile = {
            'name': '张三',
            'nickname': '小张',
        }
        
        self.assertEqual(self.context.get_user_info('name'), '张三')
        self.assertEqual(self.context.get_user_info('nickname'), '小张')
    
    def test_merge(self):
        """测试上下文合并"""
        other = ScriptContext(
            text="新消息",
            tokens=["新", "消息"],
            turn_count=6,
        )
        
        merged = self.context.merge(other)
        
        # 新值覆盖旧值
        self.assertEqual(merged.text, "新消息")
        self.assertEqual(merged.turn_count, 6)
    
    def test_summary(self):
        """测试摘要"""
        summary = self.context.summary()
        
        self.assertIn('text_length', summary)
        self.assertIn('token_count', summary)
        self.assertIn('entity_count', summary)
        self.assertEqual(summary['text_length'], 7)
        self.assertEqual(summary['token_count'], 5)
        self.assertEqual(summary['entity_count'], 1)


if __name__ == '__main__':
    unittest.main()
