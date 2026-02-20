#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试否定词处理修复效果"""

from alice.nlp.sentiment import create_sentiment_engine

def test_negation_fix():
    """测试否定词处理修复"""
    print("=== 否定词处理修复测试 ===\n")
    
    # 创建规则引擎
    engine = create_sentiment_engine(mode='rule')
    
    # 测试用例
    test_cases = [
        "我很开心",           # 正面基准
        "我不开心",           # 带否定词的负面
        "我今天很不开心",     # 程度副词+否定词
        "我没有生气",         # 否定词+负面词
        "不太好",             # 否定词+正面词
        "不是不好的体验",     # 双重否定
    ]
    
    print("测试结果:")
    print("-" * 50)
    
    for text in test_cases:
        result = engine.analyze(text)
        print(f"文本: '{text}'")
        print(f"  分数: {result.score:.2f}")
        print(f"  标签: {result.label.value}")
        print(f"  关键词: {result.keywords}")
        print(f"  置信度: {result.confidence:.2f}")
        print("-" * 30)

if __name__ == "__main__":
    test_negation_fix()
