#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 turn_count 变量处理
"""

from alice.scripts.yaml_script_engine import YAMLScriptEngine


def test_turn_count_placeholder():
    """测试 turn_count 占位符填充"""
    engine = YAMLScriptEngine.__new__(YAMLScriptEngine)
    
    # 测试基本替换
    template = '这是第 {turn_count} 轮对话'
    context = {'turn_count': 5}
    result = engine._fill_placeholders(template, context)
    assert result == '这是第 5 轮对话', f'Expected "这是第 5 轮对话", got "{result}"'
    print(f"✓ 基本替换测试通过：{result}")
    
    # 测试默认值（context 中没有 turn_count）
    template = '这是第 {turn_count} 轮对话'
    context = {}
    result = engine._fill_placeholders(template, context)
    assert result == '这是第 0 轮对话', f'Expected "这是第 0 轮对话", got "{result}"'
    print(f"✓ 默认值测试通过：{result}")
    
    # 测试与其他占位符混合使用
    template = '你好 {user_name}，这是第 {turn_count} 轮对话'
    context = {
        'turn_count': 10,
        'user_profile': {'name': 'Alice'}
    }
    result = engine._fill_placeholders(template, context)
    assert result == '你好 Alice，这是第 10 轮对话', f'Expected "你好 Alice，这是第 10 轮对话", got "{result}"'
    print(f"✓ 混合占位符测试通过：{result}")
    
    print("\n所有测试通过！")


if __name__ == '__main__':
    test_turn_count_placeholder()
