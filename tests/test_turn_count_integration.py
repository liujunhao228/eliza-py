#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试在实际对话过程中 {turn_count} 变量是否正确被维护
"""

import os
import sys

# 确保使用项目根目录的 alice 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alice.core.dialogue_engine import DialogueEngine


def test_turn_count_in_real_dialogue():
    """测试实际对话中 turn_count 的维护"""
    
    # 创建对话引擎实例
    script_file = os.path.join(os.path.dirname(__file__), "alice", "scripts", "demo.yaml")
    
    engine = DialogueEngine(
        script_file=script_file,
        enable_plugins=False,
        use_ltp=False,  # 不使用 LTP，加快测试速度
        enable_ner=False,
    )
    
    # 初始化引擎
    if not engine.initialize():
        print("❌ 引擎初始化失败")
        return False
    
    print("=" * 60)
    print("测试：在实际对话中 {turn_count} 变量的维护")
    print("=" * 60)
    
    # 测试对话
    test_inputs = [
        "你好",
        "今天天气不错",
        "你喜欢什么音乐",
        "我最近在看书",
        "你有什么推荐的吗",
        "好的，谢谢",
    ]
    
    expected_turn_counts = []
    
    for i, user_input in enumerate(test_inputs):
        # 获取当前轮数（对话前）
        turn_count_before = engine.context_manager.get_turn_count()
        
        # 生成响应
        response = engine.respond(user_input)
        
        # 获取当前轮数（对话后）
        turn_count_after = engine.context_manager.get_turn_count()
        
        expected_turn_counts.append(turn_count_after)
        
        print(f"\n第 {turn_count_after} 轮:")
        print(f"  用户：{user_input}")
        print(f"  响应：{response}")
        print(f"  turn_count: {turn_count_after}")
        
        # 检查响应中是否包含正确的 turn_count（如果响应模板使用了 turn_count）
        if "我们已经聊了" in response:
            # 检查响应中是否包含正确的轮数
            if str(turn_count_after) in response:
                print(f"  ✓ 响应中正确显示了 turn_count")
            else:
                print(f"  ❌ 响应中 turn_count 显示错误")
                return False
    
    print("\n" + "=" * 60)
    print("对话轮数统计:")
    print("=" * 60)
    
    for i, count in enumerate(expected_turn_counts):
        expected = i + 1
        status = "✓" if count == expected else "❌"
        print(f"  第 {i+1} 轮对话：turn_count = {count} {status}")
    
    # 验证最终轮数
    final_turn_count = engine.context_manager.get_turn_count()
    expected_final = len(test_inputs)
    
    print(f"\n最终轮数：{final_turn_count} (期望：{expected_final})")
    
    if final_turn_count == expected_final:
        print("✓ turn_count 正确维护")
        return True
    else:
        print("❌ turn_count 维护错误")
        return False


def test_turn_count_placeholder_in_template():
    """测试模板中 {turn_count} 占位符的替换"""
    
    print("\n" + "=" * 60)
    print("测试：模板中 {turn_count} 占位符的替换")
    print("=" * 60)
    
    from alice.scripts.yaml_script_engine import YAMLScriptEngine
    
    script_file = os.path.join(os.path.dirname(__file__), "alice", "scripts", "demo.yaml")
    engine = YAMLScriptEngine(script_file=script_file)
    
    # 找到 ongoing_chat 意图
    intent = engine.intents.get("ongoing_chat")
    if not intent:
        print("❌ 找不到 ongoing_chat 意图")
        return False
    
    print(f"\n意图：{intent.name}")
    print(f"模板：{intent.templates}")
    
    # 测试不同轮数的上下文
    for turn_count in [1, 5, 10]:
        context = {"turn_count": turn_count}
        
        # 生成响应
        response = engine.generate_response(intent, context)
        
        print(f"\n  turn_count={turn_count}:")
        print(f"    响应：{response}")
        
        # 检查响应中是否包含正确的轮数
        if str(turn_count) in response:
            print(f"    ✓ 占位符正确替换")
        else:
            print(f"    ❌ 占位符替换错误")
            return False
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("开始测试 {turn_count} 变量")
    print("=" * 60)
    
    # 测试 1：模板占位符替换
    result1 = test_turn_count_placeholder_in_template()
    
    # 测试 2：实际对话中的维护
    result2 = test_turn_count_in_real_dialogue()
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"模板占位符替换：{'✓ 通过' if result1 else '❌ 失败'}")
    print(f"实际对话维护：{'✓ 通过' if result2 else '❌ 失败'}")
    
    if result1 and result2:
        print("\n✓ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)
