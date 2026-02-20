#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP 重构测试脚本

在激活 conda 环境后运行：
    conda activate <your-env>
    python test_nlp_refactor.py
"""

import sys


def test_imports():
    """测试导入"""
    print("=" * 50)
    print("测试 1: 导入模块")
    print("=" * 50)
    
    try:
        from alice.nlp import (
            NlpFactory, DictionaryManager,
            JiebaEngine, LtpEngine, NerEngine, SentimentEngine,
            EntityType, Entity, SyntaxStructure, NlpResult,
        )
        from alice.processors import TextPreprocessor
        from alice.nlp.syntax_reassembly import SyntaxReassembly
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败：{e}")
        return False


def test_jieba():
    """测试 jieba 分词"""
    print("\n" + "=" * 50)
    print("测试 2: Jieba 分词")
    print("=" * 50)
    
    try:
        from alice.nlp import JiebaEngine
        
        engine = JiebaEngine()
        result = engine.segment("今天天气真好，我和朋友去了北京")
        print(f"✓ 分词结果：{result}")
        return True
    except Exception as e:
        print(f"✗ 分词失败：{e}")
        return False


def test_sentiment():
    """测试情感分析"""
    print("\n" + "=" * 50)
    print("测试 3: 情感分析")
    print("=" * 50)
    
    try:
        from alice.nlp import SentimentEngine
        
        engine = SentimentEngine()
        
        # 测试正面情感
        score1, label1 = engine.analyze_with_label("今天我很开心")
        print(f"✓ '今天我很开心' -> 分数：{score1:.2f}, 标签：{label1}")
        
        # 测试负面情感
        score2, label2 = engine.analyze_with_label("我感到很难过")
        print(f"✓ '我感到很难过' -> 分数：{score2:.2f}, 标签：{label2}")
        
        # 测试中性
        score3, label3 = engine.analyze_with_label("我去了一趟超市")
        print(f"✓ '我去了一趟超市' -> 分数：{score3:.2f}, 标签：{label3}")
        
        return True
    except Exception as e:
        print(f"✗ 情感分析失败：{e}")
        return False


def test_ner():
    """测试实体识别"""
    print("\n" + "=" * 50)
    print("测试 4: 实体识别")
    print("=" * 50)
    
    try:
        from alice.nlp import NerEngine
        
        engine = NerEngine()
        
        text = "今天我和朋友去了北京，见到了李老师"
        entities = engine.recognize(text)
        
        print(f"✓ 文本：{text}")
        print(f"✓ 识别实体：")
        for entity in entities:
            print(f"   - {entity.text} ({entity.entity_type.value})")
        
        return True
    except Exception as e:
        print(f"✗ 实体识别失败：{e}")
        return False


def test_dictionary_manager():
    """测试词典管理器"""
    print("\n" + "=" * 50)
    print("测试 5: 词典管理器")
    print("=" * 50)
    
    try:
        from alice.nlp import DictionaryManager
        
        manager = DictionaryManager()
        
        # 加载情感词典
        emotion_words = manager.load('emotion_words')
        print(f"✓ 情感词典：正面={len(emotion_words.get('positive', []))} 词，负面={len(emotion_words.get('negative', []))} 词")
        
        # 加载实体模式词典
        entity_patterns = manager.load('entity_patterns')
        print(f"✓ 实体模式词典：代词={len(entity_patterns.get('pronouns', []))} 词")
        
        # 加载意图关键词
        intent_keywords = manager.load('intent_keywords')
        print(f"✓ 意图关键词：{len(intent_keywords)} 类意图")
        
        return True
    except Exception as e:
        print(f"✗ 词典管理失败：{e}")
        return False


def test_text_preprocessor():
    """测试文本预处理器"""
    print("\n" + "=" * 50)
    print("测试 6: 文本预处理器")
    print("=" * 50)
    
    try:
        from alice.processors import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        # 测试标准化
        text1 = "你好，世界！"
        result1 = preprocessor.standardize_text(text1)
        print(f"✓ 标准化：'{text1}' -> '{result1}'")
        
        # 测试清洗
        text2 = "你好@#$世界!!!"
        result2 = preprocessor.clean_text(text2)
        print(f"✓ 清洗：'{text2}' -> '{result2}'")
        
        return True
    except Exception as e:
        print(f"✗ 预处理失败：{e}")
        return False


def test_nlp_factory():
    """测试 NLP 工厂"""
    print("\n" + "=" * 50)
    print("测试 7: NLP 工厂")
    print("=" * 50)
    
    try:
        from alice.nlp import NlpFactory
        
        factory = NlpFactory({'use_ltp': False})
        
        # 创建分词器
        segmenter = factory.create_segmenter()
        print(f"✓ 创建分词器：{type(segmenter).__name__}")
        
        # 创建情感分析器
        sentiment = factory.create_sentiment_analyzer()
        print(f"✓ 创建情感分析器：{type(sentiment).__name__}")
        
        # 创建实体识别器
        ner = factory.create_entity_recognizer()
        print(f"✓ 创建实体识别器：{type(ner).__name__}")
        
        # 创建流水线
        pipeline = factory.create_pipeline(['jieba', 'ner', 'sentiment'])
        result = pipeline.process("今天我很开心，和朋友一起去了公园")
        print(f"✓ 流水线处理：tokens={len(result.tokens)}, entities={len(result.entities)}, sentiment={result.sentiment:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ 工厂测试失败：{e}")
        return False


def test_semantic_analyzer():
    """测试语义分析器"""
    print("\n" + "=" * 50)
    print("测试 8: 语义分析器")
    print("=" * 50)
    
    try:
        from alice.nlp.semantic_analyzer import SemanticAnalyzer
        
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze("今天我和朋友去了北京，感到非常开心")
        
        print(f"✓ 分析结果:")
        print(f"   - tokens: {len(result['tokens'])} 个")
        print(f"   - 情感分数：{result['sentiment']:.2f}")
        print(f"   - 情感标签：{result['sentiment_label']}")
        print(f"   - 实体：{result['entities']}")
        print(f"   - 意图：{result['intent']}")
        
        return True
    except Exception as e:
        print(f"✗ 语义分析失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Alice NLP 重构测试")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_imports),
        ("Jieba 分词", test_jieba),
        ("情感分析", test_sentiment),
        ("实体识别", test_ner),
        ("词典管理", test_dictionary_manager),
        ("文本预处理", test_text_preprocessor),
        ("NLP 工厂", test_nlp_factory),
        ("语义分析器", test_semantic_analyzer),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 异常：{e}")
            results.append((name, False))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
