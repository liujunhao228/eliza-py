#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构模块测试

测试重构后的核心模块：
1. YAML 脚本引擎
2. 意图匹配器（基于 YAML 驱动）
3. 响应生成器（基于 YAML 驱动）
4. 对话引擎（正确调用 NLP）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def test_yaml_script_engine():
    """测试 YAML 脚本引擎"""
    print("=" * 60)
    print("测试 1: YAML 脚本引擎")
    print("=" * 60)

    from alice.scripts.yaml_script_engine import YAMLScriptEngine

    engine = YAMLScriptEngine(script_file='alice/scripts/curiosity_scripts.yaml')
    print(f"✓ 加载了 {len(engine.intents)} 个脚本意图")

    # 验证意图优先级
    intents_by_priority = sorted(engine.intents.values(), key=lambda x: x.priority, reverse=True)
    print(f"✓ 最高优先级意图：{intents_by_priority[0].name} (priority={intents_by_priority[0].priority})")
    print(f"✓ 最低优先级意图：{intents_by_priority[-1].name} (priority={intents_by_priority[-1].priority})")

    # 验证 keyword_only 标志
    keyword_only_intents = [i for i in engine.intents.values() if i.keyword_only]
    print(f"✓ keyword_only 意图：{[i.name for i in keyword_only_intents]}")

    return engine


def test_intent_matcher(script_engine):
    """测试意图匹配器"""
    print("\n" + "=" * 60)
    print("测试 2: 意图匹配器 (基于 YAML 驱动)")
    print("=" * 60)

    from alice.core.intent_matcher import IntentMatcher

    # 创建匹配器并绑定脚本引擎
    matcher = IntentMatcher()
    matcher.set_script_engine(script_engine)
    print(f"✓ 意图匹配器已绑定脚本引擎，支持 {len(matcher.get_supported_intents())} 个意图")

    # 测试用例
    test_cases = [
        # (输入文本，上下文，期望意图)
        ("你好", {"entities": [], "sentiment": 0.0}, "greeting"),
        ("再见", {"entities": [], "sentiment": 0.0}, "farewell"),
        ("谢谢", {"entities": [], "sentiment": 0.0}, "thanks"),
        ("我遇到了小明", {"entities": [("person", "小明")], "sentiment": 0.0}, "person_interest"),
        ("我很伤心", {"entities": [], "sentiment": -0.6, "sentiment_label": "negative"}, "emotion_mirror_negative"),
        ("我很开心", {"entities": [], "sentiment": 0.6, "sentiment_label": "positive"}, "emotion_mirror_positive"),
        ("我觉得很焦虑", {"entities": [], "sentiment": -0.4}, "belief_exploration"),
        ("你是谁", {"entities": [], "sentiment": 0.0}, "who_are_you"),
        ("后来呢", {"entities": [], "sentiment": 0.0}, "fallback"),
    ]

    passed = 0
    failed = 0

    for text, context, expected in test_cases:
        result = matcher.match(text, context)
        if result:
            status = "✓" if result.intent == expected or expected in result.intent else "✗"
            if status == "✓":
                passed += 1
            else:
                failed += 1
            print(f"  {status} 输入：{text!r:15} -> 意图：{result.intent:25} (confidence={result.confidence:.2f}, priority={result.priority})")
        else:
            failed += 1
            print(f"  ✗ 输入：{text!r:15} -> 无匹配 (期望：{expected})")

    print(f"\n结果：{passed} 通过，{failed} 失败")
    return matcher


def test_response_generator(script_engine):
    """测试响应生成器"""
    print("\n" + "=" * 60)
    print("测试 3: 响应生成器 (基于 YAML 驱动)")
    print("=" * 60)

    from alice.core.response_generator import ResponseGenerator
    from alice.nlp.syntax_reassembly import SyntaxReassembly

    # 创建响应生成器
    reassembly_engine = SyntaxReassembly(rules_file='alice/scripts/mapping.yaml')
    generator = ResponseGenerator(
        script_engine=script_engine,
        reassembly_engine=reassembly_engine,
    )
    print("✓ 响应生成器已初始化")

    # 测试用例
    test_cases = [
        # (输入文本，语义信息，期望意图)
        ("你好", {"entities": [], "sentiment": 0.0, "tokens": ["你", "好"]}, "greeting"),
        ("我遇到了小明", {"entities": [("person", "小明")], "sentiment": 0.0, "tokens": ["我", "遇到", "了", "小明"]}, "person_interest"),
        ("我很伤心", {"entities": [], "sentiment": -0.6, "sentiment_label": "negative", "tokens": ["我", "很", "伤心"]}, "emotion_mirror_negative"),
        ("我觉得很焦虑", {"entities": [], "sentiment": -0.4, "tokens": ["我", "觉得", "很", "焦虑"]}, "belief_exploration"),
    ]

    from alice.core.intent_matcher import IntentMatcher
    matcher = IntentMatcher(script_engine=script_engine)

    for text, semantic_info, expected_intent in test_cases:
        # 先匹配意图
        intent_match = matcher.match(text, semantic_info)
        # 再生成响应
        response = generator.generate(
            user_input=text,
            semantic_info=semantic_info,
            intent=intent_match.intent,
            intent_match=intent_match,
        )
        print(f"  输入：{text!r:15} -> 意图：{intent_match.intent:25} -> 响应：{response[:40]}...")

    return generator


def test_dialogue_engine():
    """测试对话引擎（整合测试）"""
    print("\n" + "=" * 60)
    print("测试 4: 对话引擎 (整合测试)")
    print("=" * 60)

    from alice.core.dialogue_engine import DialogueEngine

    # 创建对话引擎
    engine = DialogueEngine(
        script_file='alice/scripts/curiosity_scripts.yaml',
        rules_file='alice/scripts/mapping.yaml',
        enable_plugins=True,
        use_ltp=False,  # 禁用 LTP 以加快测试
    )

    # 初始化
    success = engine.initialize()
    if not success:
        print("✗ 对话引擎初始化失败")
        return None

    print("✓ 对话引擎初始化成功")
    print(f"✓ 脚本引擎：{engine.script_engine is not None}")
    print(f"✓ 重组引擎：{engine.reassembly_engine is not None}")
    print(f"✓ 插件系统：{engine.enable_plugins}")
    print(f"✓ LTP 引擎：{engine.use_ltp}")

    # 测试对话
    test_inputs = [
        "你好",
        "我最近很焦虑",
        "我和小明吵架了",
        "我觉得没人理解我",
        "你是谁",
        "再见",
    ]

    print("\n对话测试:")
    for user_input in test_inputs:
        response = engine.respond(user_input)
        rule_info = engine.get_last_rule_info()
        print(f"  用户：{user_input:15} -> Alice: {response[:35]}... [来源：{rule_info.get('source', 'unknown')}]")

    return engine


def test_nlp_integration():
    """测试 NLP 集成"""
    print("\n" + "=" * 60)
    print("测试 5: NLP 集成")
    print("=" * 60)

    from alice.nlp.ltp_engine import LtpEngine

    # 测试 LTP 引擎
    ltp = LtpEngine(lazy_load=True)
    print(f"✓ LTP 引擎已初始化 (lazy_load=True)")
    print(f"✓ LTP 可用性：{ltp.is_available}")

    if ltp.is_available:
        # 测试分析
        text = "我觉得今天很开心"
        result = ltp.analyze(text)
        print(f"✓ 分析文本：{text!r}")
        print(f"  - Tokens: {result.tokens}")
        print(f"  - 实体：{[(e.entity_type.value, e.text) for e in result.entities]}")
        if result.syntax:
            print(f"  - 主语：{result.syntax.subject}, 谓语：{result.syntax.predicate}, 宾语：{result.syntax.object}")
    else:
        print("⚠ LTP 不可用，跳过详细测试")

    return ltp


def main():
    """运行所有测试"""
    print("Alice 重构模块测试")
    print("测试目标:")
    print("  1. 验证 YAML 脚本引擎正确加载")
    print("  2. 验证意图匹配器基于 YAML 驱动（移除硬编码）")
    print("  3. 验证响应生成器基于 YAML 驱动（移除硬编码）")
    print("  4. 验证对话引擎正确调用 NLP 和脚本引擎")
    print("  5. 验证 NLP 引擎集成")
    print()

    try:
        # 测试 1: YAML 脚本引擎
        script_engine = test_yaml_script_engine()

        # 测试 2: 意图匹配器
        test_intent_matcher(script_engine)

        # 测试 3: 响应生成器
        test_response_generator(script_engine)

        # 测试 4: 对话引擎
        test_dialogue_engine()

        # 测试 5: NLP 集成
        test_nlp_integration()

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
