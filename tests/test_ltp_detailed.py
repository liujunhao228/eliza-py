#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 详细功能测试
用于调试和验证 LTP 集成的具体问题
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alice.utils.ltp_parser import LTPParser


def test_ltp_basic_functionality():
    """测试 LTP 基本功能"""
    print("=== LTP 基础功能测试 ===")
    
    # 创建解析器
    parser = LTPParser()
    print(f"LTP 可用状态: {parser.available}")
    
    # 测试简单句子
    test_sentences = [
        "我喜欢编程",
        "今天天气很好",
        "他正在学习Python",
        "我们一起去吃饭吧"
    ]
    
    for sentence in test_sentences:
        print(f"\n--- 分析句子: {sentence} ---")
        
        # 基础解析
        structure = parser.parse(sentence)
        if structure:
            print(f"词语: {structure.words}")
            print(f"词性: {structure.poses}")
            print(f"主语: {structure.subject}")
            print(f"谓语: {structure.predicate}")
            print(f"宾语: {structure.object}")
            
            # 依存关系
            if structure.deps:
                print("依存关系:")
                for dep in structure.deps[:5]:  # 显示前5个
                    print(f"  {dep.word}({dep.pos}) --{dep.dep}--> head:{dep.head}")
        else:
            print("解析失败")


def test_ltp_pipeline_directly():
    """直接测试 LTP pipeline 方法"""
    print("\n=== 直接测试 LTP Pipeline ===")
    
    try:
        from ltp import LTP
        ltp = LTP()
        print("LTP 对象创建成功")
        print(f"支持的任务: {ltp.supported_tasks}")
        
        # 测试不同任务组合
        test_text = ["我喜欢编程"]
        
        print("\n测试任务组合:")
        task_combinations = [
            ['cws'],
            ['cws', 'pos'],
            ['cws', 'pos', 'dep'],
            ['seg', 'pos', 'dep']  # 原始错误的任务
        ]
        
        for tasks in task_combinations:
            try:
                print(f"\n任务: {tasks}")
                result = ltp.pipeline(test_text, tasks=tasks)
                print(f"结果类型: {type(result)}")
                if isinstance(result, tuple):
                    print(f"元组长度: {len(result)}")
                    for i, item in enumerate(result):
                        print(f"  元素{i}: {type(item)}, 长度: {len(item) if hasattr(item, '__len__') else 'N/A'}")
                elif isinstance(result, dict):
                    print(f"字典键: {list(result.keys())}")
                    for key, value in result.items():
                        print(f"  {key}: {type(value)}, 长度: {len(value) if hasattr(value, '__len__') else 'N/A'}")
                else:
                    print(f"其他类型: {type(result)}")
            except Exception as e:
                print(f"  错误: {e}")
                
    except Exception as e:
        print(f"LTP 导入或初始化失败: {e}")


def test_parser_methods():
    """测试解析器的各种方法"""
    print("\n=== 解析器方法测试 ===")
    
    parser = LTPParser()
    
    test_sentence = "我觉得今天很开心"
    
    print(f"测试句子: {test_sentence}")
    
    # 测试主干结构提取
    main_struct = parser.get_main_structure(test_sentence)
    print(f"主干结构: {main_struct}")
    
    # 测试修饰语提取
    modifiers = parser.get_modifiers(test_sentence)
    print(f"修饰语: {modifiers}")
    
    # 测试依存树
    dep_tree = parser.get_dependency_tree(test_sentence)
    if dep_tree:
        print(f"依存树词语: {dep_tree['words']}")
        print("依存关系:")
        for dep in dep_tree.get('dependencies', [])[:3]:
            print(f"  {dep['word']} --{dep['dep']}--> {dep['head_word']}")
    else:
        print("依存树为空")


if __name__ == "__main__":
    print("开始 LTP 详细测试...")
    
    test_ltp_basic_functionality()
    test_ltp_pipeline_directly()
    test_parser_methods()
    
    print("\n测试完成!")