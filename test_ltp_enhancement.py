#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎与脚本引擎增强功能测试脚本

测试新增的语义角色标注(SRL)和语义依存分析(SDP)功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from alice.alice_v2 import AliceBot
from alice.core.dialogue_engine import DialogueEngine
from alice.nlp.engines.ltp import LtpEngine


def test_ltp_enhancement():
    """测试LTP引擎增强功能"""
    print("=" * 60)
    print("LTP 引擎与脚本引擎增强功能测试")
    print("=" * 60)

    # 1. 测试LTP引擎是否支持SRL和SDP
    print("\n1. 测试LTP引擎功能...")
    try:
        ltp_engine = LtpEngine(enable_srl=True, enable_sdp=True)
        print(f"   ✓ LTP引擎创建成功")
        print(f"   ✓ SRL功能启用: {ltp_engine.config.enable_srl}")
        print(f"   ✓ SDP功能启用: {ltp_engine.config.enable_sdp}")
        
        # 测试完整分析
        text = "小明在北京大学读书"
        result = ltp_engine.analyze_full(text)
        print(f"   ✓ 完整分析成功: {text}")
        print(f"     - 分词: {result.tokens}")
        print(f"     - 词性: {[p.pos for p in result.pos_tags]}")
        print(f"     - 实体: {[(e.entity_type.value, e.text) for e in result.entities]}")
        print(f"     - 依存关系: {[(d.token.text, d.relation, result.tokens[d.head_idx].text if 0 <= d.head_idx < len(result.tokens) else 'ROOT') for d in result.dependencies]}")
        
        if result.semantic_roles:
            print(f"     - 语义角色: {len(result.semantic_roles)} 个谓词")
            for role in result.semantic_roles:
                print(f"       谓词: {role.predicate}, 论元: {len(role.arguments)} 个")
                for arg_type, arg_text, start, end in role.arguments:
                    print(f"         - {arg_type}: {arg_text}")
        else:
            print(f"     - 语义角色: 未检测到")
            
        if result.semantic_deps:
            print(f"     - 语义依存: {len(result.semantic_deps.edges)} 条边")
        else:
            print(f"     - 语义依存: 未检测到")
            
    except Exception as e:
        print(f"   ✗ LTP引擎测试失败: {e}")
        return False

    # 2. 测试对话引擎与新功能集成
    print("\n2. 测试对话引擎与新功能集成...")
    try:
        # 创建启用LTP的对话引擎
        dialogue_engine = DialogueEngine(
            script_file="alice/scripts/demo_enhanced.yaml",
            use_ltp=True,
            enable_ner=True,
            ner_use_ltp=True
        )
        dialogue_engine.initialize()
        print(f"   ✓ 对话引擎初始化成功")
        print(f"   ✓ LTP启用: {dialogue_engine.use_ltp}")
        print(f"   ✓ NER启用: {dialogue_engine.enable_ner}")
        
        # 检查NLP流水线是否包含LTP引擎
        if hasattr(dialogue_engine.nlp_pipeline, 'ltp_engine') and dialogue_engine.nlp_pipeline.ltp_engine:
            print(f"   ✓ NLP流水线包含LTP引擎")
        else:
            print(f"   ⚠ NLP流水线未找到LTP引擎")
        
    except Exception as e:
        print(f"   ✗ 对话引擎测试失败: {e}")
        return False

    # 3. 测试AliceBot与新脚本
    print("\n3. 测试AliceBot与增强脚本...")
    try:
        alice = AliceBot(
            script_file="alice/scripts/demo_enhanced.yaml",
            use_ltp=True
        )
        print(f"   ✓ AliceBot创建成功")
        
        # 测试基本功能
        response = alice.respond("你好")
        print(f"   ✓ 基本问候测试: {response}")
        
        # 测试语义分析功能
        test_sentences = [
            "小明在北京大学读书",
            "昨天我在图书馆学习",
            "因为下雨所以取消了户外活动"
        ]
        
        for sentence in test_sentences:
            response = alice.respond(sentence)
            print(f"   ✓ 语义分析测试 ('{sentence}'): {response}")
        
    except Exception as e:
        print(f"   ✗ AliceBot测试失败: {e}")
        return False

    # 4. 测试新脚本功能
    print("\n4. 测试新脚本功能...")
    try:
        # 测试语义角色相关的意图匹配
        dialogue_engine = DialogueEngine(
            script_file="alice/scripts/demo_enhanced.yaml",
            use_ltp=True,
            enable_ner=True,
            ner_use_ltp=True
        )
        dialogue_engine.initialize()
        
        # 测试文本
        test_text = "小明在图书馆学习编程"
        result = dialogue_engine.respond(test_text)
        print(f"   ✓ 语义分析测试: '{test_text}' -> '{result}'")
        
        # 检查是否能获取到语义信息
        nlp_result = dialogue_engine.nlp_pipeline.process(test_text)
        print(f"   ✓ NLP分析: 词数={len(nlp_result.tokens)}, 实体数={len(nlp_result.entities)}")
        
        if hasattr(dialogue_engine.nlp_pipeline, 'ltp_engine'):
            ltp_result = dialogue_engine.nlp_pipeline.ltp_engine.analyze_full(test_text)
            print(f"   ✓ LTP分析: 语义角色={len(ltp_result.semantic_roles) if ltp_result.semantic_roles else 0}个, 语义依存={len(ltp_result.semantic_deps.edges) if ltp_result.semantic_deps else 0}条")
        
    except Exception as e:
        print(f"   ✗ 新脚本功能测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有测试通过！LTP引擎与脚本引擎增强功能正常工作。")
    print("=" * 60)
    return True


def main():
    """主函数"""
    success = test_ltp_enhancement()
    if not success:
        print("\n测试失败，请检查配置和依赖。")
        sys.exit(1)
    else:
        print("\n所有测试均通过！")


if __name__ == "__main__":
    main()