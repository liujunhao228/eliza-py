#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 NER 和实体追踪功能
"""

import sys
sys.path.insert(0, '.')

from alice.core import AliceBot
from alice.utils.ner import extract_entities, extract_entities_as_dict


def test_ner_extraction():
    """测试 NER 实体提取"""
    print("=" * 60)
    print("测试 1: NER 实体提取")
    print("=" * 60)

    test_cases = [
        "我昨天和我朋友小明去了北京",
        "我妈妈今天很高兴，因为我要回家了",
        "他和同事在咖啡厅聊了一个下午",
        "最近工作压力很大，经常熬夜到凌晨 2 点",
        "我觉得很开心，因为见到了好久不见的朋友",
        "小张和他的团队在上海公司开会",
        "我打算下周去日本旅游",
    ]

    for text in test_cases:
        print(f"\n原文：{text}")
        entities = extract_entities(text)
        entities_dict = extract_entities_as_dict(text)

        print("  识别的实体:")
        for entity in entities:
            print(f"    [{entity.entity_type.value:12}] {entity.text}")

        print("  按类型分组:")
        for etype, texts in entities_dict.items():
            print(f"    {etype}: {texts}")


def test_entity_tracking():
    """测试上下文实体追踪"""
    print("\n" + "=" * 60)
    print("测试 2: 上下文实体追踪")
    print("=" * 60)

    # 创建机器人实例（启用 NER）
    bot = AliceBot(enable_ner=True, enable_ltp=False)

    test_dialogue = [
        "我昨天和我朋友小明去了北京",
        "他是个很有趣的人",
        "我们在王府井逛街",
        "然后去吃了烤鸭",
        "今天我要去公司上班",
        "小明说他下周要来找我",
    ]

    print("\n对话流程:")
    print("-" * 60)

    for i, user_input in enumerate(test_dialogue, 1):
        print(f"\n第 {i} 轮:")
        print(f"  用户：{user_input}")

        # 分析输入
        standardized_text = bot.preprocessor.standardize_text(user_input)
        semantic_info = bot.analyzer.analyze(standardized_text)

        # 显示识别的实体
        entities = semantic_info.get('entities', [])
        if entities:
            print(f"  识别实体：{[(t, v) for v, t in entities]}")

        # 更新上下文
        bot.context_manager.update_context(semantic_info, user_input)

        # 显示当前实体追踪状态
        person_chain = bot.context_manager.get_person_chain(limit=3)
        if person_chain:
            print(f"  人物链：{[p['text'] for p in person_chain]}")

    # 显示最终上下文状态
    print("\n" + "-" * 60)
    print("最终上下文状态:")
    context_state = bot.get_conversation_summary()

    print(f"  当前话题：{context_state.get('current_topic', 'N/A')}")
    print(f"  提及人物：{context_state.get('recent_entities', [])}")
    print(f"  情感趋势：{context_state.get('emotion_trend', 'neutral')}")

    # 显示实体提及统计
    entity_mentions = bot.context_manager.entity_mentions
    if entity_mentions:
        print("\n  实体提及统计:")
        for key, mention in entity_mentions.items():
            print(f"    [{mention.entity_type:10}] {mention.text:8} - 提及{mention.frequency}次")


def test_bot_with_ner():
    """测试机器人生成回复（带 NER）"""
    print("\n" + "=" * 60)
    print("测试 3: 机器人生成回复（带 NER）")
    print("=" * 60)

    # 创建机器人实例
    bot = AliceBot(enable_ner=True, enable_ltp=False)

    test_inputs = [
        "我朋友最近工作压力很大",
        "我昨天去了北京",
        "我觉得很开心",
    ]

    print("\n对话测试:")
    print("-" * 60)

    for user_input in test_inputs:
        print(f"\n用户：{user_input}")

        # 分析输入
        standardized_text = bot.preprocessor.standardize_text(user_input)
        semantic_info = bot.analyzer.analyze(standardized_text)

        # 显示实体
        entities = semantic_info.get('entities', [])
        if entities:
            entity_types = {}
            for etype, text in entities:
                if etype not in entity_types:
                    entity_types[etype] = []
                entity_types[etype].append(text)
            print(f"实体：{entity_types}")

        # 生成回复
        try:
            response = bot.respond(user_input)
            print(f"Alice: {response}")
        except Exception as e:
            print(f"错误：{e}")


def main():
    """运行所有测试"""
    print("NER 和实体追踪功能测试")
    print("=" * 60)

    test_ner_extraction()
    test_entity_tracking()
    test_bot_with_ner()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
