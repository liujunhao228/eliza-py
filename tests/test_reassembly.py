#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 重组规则功能测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alice.core import AliceBot
from alice.utils.reassembly import ReassemblyEngine, ReassemblyRuleSelector


def test_reassembly_engine():
    """测试重组引擎"""
    print("=" * 50)
    print("测试重组引擎")
    print("=" * 50)
    
    engine = ReassemblyEngine()
    
    # 测试 1: 基本重组
    components = ["", "难过"]
    rule = "你为什么感到{2}呢？"
    result = engine.reassemble(components, rule)
    assert result == "你为什么感到难过呢？", f"期望'你为什么感到难过呢？', 得到'{result}'"
    print(f"[OK] 测试 1 通过：{result}")
    
    # 测试 2: 多组件重组
    components = ["工作", "压力很大"]
    rule = "为什么{1}{2}呢？"
    result = engine.reassemble(components, rule)
    assert result == "为什么工作压力很大呢？", f"期望'为什么工作压力很大呢？', 得到'{result}'"
    print(f"[OK] 测试 2 通过：{result}")
    
    # 测试 3: 代词转换
    components = ["我", "很烦"]
    rule = "为什么{1}{2}呢？"
    result = engine.reassemble(components, rule, apply_pronoun_mapping=True)
    # 代词转换应该将"我"转为"你"
    assert "你" in result, f"期望包含'你', 得到'{result}'"
    print(f"[OK] 测试 3 通过（代词转换）：{result}")
    
    print()


def test_rule_selector():
    """测试重组规则选择器"""
    print("=" * 50)
    print("测试重组规则选择器")
    print("=" * 50)
    
    rules = [
        "规则 1: {1}",
        "规则 2: {1}",
        "规则 3: {1}",
    ]
    selector = ReassemblyRuleSelector(rules)
    
    # 测试避免重复
    selected = set()
    for _ in range(6):
        rule = selector.select(avoid_repeats=True)
        selected.add(rule)
    
    # 应该选择了所有规则
    assert len(selected) == 3, f"期望选择 3 条不同规则，实际{len(selected)}"
    print(f"[OK] 测试通过：成功轮换使用 {len(selected)} 条规则")
    print()


def test_alice_dialogue():
    """测试 Alice 对话功能"""
    print("=" * 50)
    print("测试 Alice 对话")
    print("=" * 50)
    
    alice = AliceBot()
    
    test_cases = [
        ("你好", "问候"),
        ("我感到很焦虑", "情感表达"),
        ("我昨天去了一个新开的餐厅", "叙事延续"),
        ("我觉得我的工作很有压力", "自我反思"),
        ("我和朋友吵架了", "人物关注/关系讨论"),
        ("为什么总是这样？", "观点询问"),
    ]
    
    for user_input, category in test_cases:
        response = alice.respond(user_input)
        print(f"[{category}]")
        print(f"  你：{user_input}")
        print(f"  Alice: {response}")
        print()
    
    print("[OK] 对话测试完成")
    print()


def test_reassembly_integration():
    """测试重组规则集成"""
    print("=" * 50)
    print("测试重组规则集成")
    print("=" * 50)
    
    alice = AliceBot()
    
    # 这些输入应该触发重组规则
    reassembly_tests = [
        "我感到很疲惫",  # 应该触发 emotional_expression 的重组规则
        "我去了北京",     # 应该触发 narrative_continuation 的重组规则
        "我觉得他很奇怪", # 应该触发 self_reflection 的重组规则
    ]
    
    for user_input in reassembly_tests:
        response = alice.respond(user_input)
        print(f"输入：{user_input}")
        print(f"响应：{response}")
        
        # 检查响应是否包含用户输入的关键内容（重组规则的特征）
        has_reassembly = any(
            keyword in response 
            for keyword in ["疲惫", "去", "觉得"]
        )
        if has_reassembly:
            print("[OK] 检测到重组规则使用")
        print()


def main():
    """运行所有测试"""
    print("\n")
    print("=" * 50)
    print(" " * 10 + "Alice 重组规则功能测试" + " " * 10)
    print("=" * 50)
    print()
    
    try:
        test_reassembly_engine()
        test_rule_selector()
        test_alice_dialogue()
        test_reassembly_integration()
        
        print("=" * 50)
        print("所有测试通过！")
        print("=" * 50)
        return 0
        
    except AssertionError as e:
        print(f"[FAIL] 测试失败：{e}")
        return 1
    except Exception as e:
        print(f"[ERROR] 测试出错：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
