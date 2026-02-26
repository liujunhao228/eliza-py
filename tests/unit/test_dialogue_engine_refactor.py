#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重构后的 DialogueEngine
"""

import sys
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent))

from alice.core.dialogue_engine import DialogueEngine
from config import get_config_manager

# 使用 ASCII 兼容的符号
CHECK = "[OK]"
CROSS = "[FAIL]"


def test_instantiation():
    """测试实例化"""
    print("=" * 60)
    print("测试 1: 实例化 DialogueEngine")
    print("=" * 60)
    
    config_mgr = get_config_manager()
    engine = DialogueEngine(config_manager=config_mgr)
    
    assert engine is not None, "实例化失败"
    assert engine.config_manager is config_mgr, "配置管理器未正确设置"
    
    print(f"{CHECK} DialogueEngine 实例化成功")
    return engine


def test_config_loading(engine):
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("测试 2: 配置加载")
    print("=" * 60)

    # 打印配置信息
    print(f"YAML 脚本文件：{engine.yaml_script_file}")
    print(f"Lua 脚本目录：{engine.lua_script_dir}")
    print(f"Lua 元数据文件：{engine.lua_metadata_file}")
    print(f"规则文件：{engine.rules_file}")
    print(f"Enable LTP: {engine.use_ltp}")
    print(f"Enable NER: {engine.enable_ner}")
    print(f"Enable Lua: {engine.enable_lua}")
    print(f"Enable YAML: {engine.enable_yaml}")
    print(f"Lua 沙箱模式：{engine.lua_sandbox_mode}")
    print(f"Lua 最大执行时间：{engine.lua_max_execution_time}s")

    # 验证配置已加载
    assert hasattr(engine, 'yaml_script_file'), "缺少 yaml_script_file 属性"
    assert hasattr(engine, 'lua_script_dir'), "缺少 lua_script_dir 属性"

    print(f"{CHECK} 配置加载成功")


def test_initialization(engine):
    """测试初始化"""
    print("\n" + "=" * 60)
    print("测试 3: 引擎初始化")
    print("=" * 60)
    
    success = engine.initialize()
    
    print(f"初始化结果：{'成功' if success else '失败'}")
    print(f"已注册引擎：{list(engine.script_matcher.engines.keys())}")
    print(f"NLP 流水线：{engine.nlp_pipeline}")
    
    assert success, "初始化失败"
    assert engine._initialized, "初始化状态未设置"
    
    print(f"{CHECK} 引擎初始化成功")


def test_respond(engine):
    """测试响应生成"""
    print("\n" + "=" * 60)
    print("测试 4: 响应生成")
    print("=" * 60)
    
    test_inputs = [
        "你好",
        "你是谁？",
        "今天天气怎么样？",
    ]
    
    for user_input in test_inputs:
        response = engine.respond(user_input)
        rule_info = engine.get_last_rule_info()
        
        print(f"输入：{user_input}")
        print(f"响应：{response}")
        print(f"来源：{rule_info.get('source', 'unknown')}")
        print("-" * 40)
        
        assert response is not None, "响应为空"
        assert isinstance(response, str), "响应不是字符串"
        assert len(response) > 0, "响应为空字符串"
    
    print(f"{CHECK} 响应生成测试通过")


def test_stats(engine):
    """测试统计信息"""
    print("\n" + "=" * 60)
    print("测试 5: 统计信息")
    print("=" * 60)
    
    stats = engine.get_stats()

    print(f"已初始化：{stats.get('initialized')}")
    print(f"引擎统计：{stats.get('engines')}")
    print(f"上下文统计：{stats.get('context')}")
    print(f"NLP 配置：{stats.get('nlp')}")

    assert 'initialized' in stats, "缺少 initialized 字段"
    assert 'engines' in stats, "缺少 engines 字段"
    assert 'context' in stats, "缺少 context 字段"
    
    print(f"{CHECK} 统计信息获取成功")


def test_script_management(engine):
    """测试脚本管理"""
    print("\n" + "=" * 60)
    print("测试 6: 脚本管理")
    print("=" * 60)
    
    # 列出脚本
    scripts = engine.list_scripts()
    print(f"已加载脚本：{scripts}")
    
    # 获取脚本数量
    count = engine.get_loaded_scripts_count()
    print(f"脚本总数：{count}")
    
    print(f"{CHECK} 脚本管理测试通过")


def test_reset(engine):
    """测试重置"""
    print("\n" + "=" * 60)
    print("测试 7: 重置对话")
    print("=" * 60)
    
    engine.reset()
    print("对话已重置")
    
    # 重置后仍然可以响应
    response = engine.respond("测试")
    print(f"重置后响应：{response}")
    
    assert response is not None, "重置后无法生成响应"
    
    print(f"{CHECK} 重置测试通过")


def test_cleanup(engine):
    """测试清理"""
    print("\n" + "=" * 60)
    print("测试 8: 清理资源")
    print("=" * 60)
    
    engine.cleanup()
    print("资源已清理")
    
    assert not engine._initialized, "清理后初始化状态未重置"
    
    print(f"{CHECK} 清理测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DialogueEngine 重构测试")
    print("=" * 60)
    
    try:
        # 1. 实例化
        engine = test_instantiation()
        
        # 2. 配置加载
        test_config_loading(engine)
        
        # 3. 初始化
        test_initialization(engine)
        
        # 4. 响应生成
        test_respond(engine)
        
        # 5. 统计信息
        test_stats(engine)
        
        # 6. 脚本管理
        test_script_management(engine)
        
        # 7. 重置
        test_reset(engine)
        
        # 8. 清理
        test_cleanup(engine)
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
