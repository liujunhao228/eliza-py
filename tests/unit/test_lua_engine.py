"""
Lua脚本引擎集成测试
测试Lua脚本引擎的基本功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from engines.lua.lua_script_engine import LuaScriptEngine, LuaScriptConfig
from alice.core.context import Context
from alice.core.nlp_pipeline import NLPPipelineResult


def test_lua_script_engine():
    """测试Lua脚本引擎"""
    print("=== 测试Lua脚本引擎 ===")

    # 创建引擎实例
    lua_engine = LuaScriptEngine()

    # 创建脚本配置
    config = LuaScriptConfig(
        script_path=project_root / "scripts" / "lua" / "greeting.lua",
        name="greeting_test",
        description="问候脚本测试",
        priority=90,
        enabled=True,
        cache_size=100,
        max_execution_time=1.0,
        sandbox_mode=True
    )

    # 加载脚本
    print(f"加载脚本: {config.name}")
    if lua_engine.load_script(config):
        print("脚本加载成功！")

        # 测试匹配
        print("\n=== 测试匹配 ===")
        text = "你好"
        nlp_result = NLPPipelineResult(text)
        context = Context()
        context.update("text", text)

        match_result = lua_engine.match_script(text, nlp_result, context, [config])

        if match_result:
            print(f"匹配成功！脚本ID: {match_result.script_id}")
            print(f"置信度: {match_result.confidence}")
            print(f"执行时间: {match_result.execution_time:.3f}秒")

            # 测试响应生成
            print("\n=== 测试响应生成 ===")
            response = lua_engine.generate_response(
                match_result.script_id,
                text,
                nlp_result,
                context
            )

            if response:
                print(f"响应: {response}")
            else:
                print("响应生成失败")
        else:
            print("匹配失败")
    else:
        print("脚本加载失败")

    # 显示缓存统计
    print("\n=== 缓存统计 ===")
    stats = lua_engine.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


def test_conversation_flow_script():
    """测试对话流程脚本"""
    print("\n=== 测试对话流程脚本 ===")

    lua_engine = LuaScriptEngine()

    config = LuaScriptConfig(
        script_path=project_root / "scripts" / "lua" / "conversation_flow.lua",
        name="conversation_flow_test",
        description="对话流程测试",
        priority=75,
        enabled=True,
        cache_size=100,
        max_execution_time=1.5,
        sandbox_mode=True
    )

    if lua_engine.load_script(config):
        print("对话流程脚本加载成功！")

        # 测试不同状态的对话
        test_cases = [
            ("你好", "initial"),
            ("你叫什么名字", "greeting"),
            ("我是程序员", "information_gathering"),
            ("好的，谢谢", "response_providing"),
            ("再见", "closing")
        ]

        for text, expected_state in test_cases:
            print(f"\n输入: {text}")
            nlp_result = NLPPipelineResult(text)
            context = Context()
            context.update("text", text)
            context.update("turn_count", 1)
            context.update("conversation_state", expected_state)

            match_result = lua_engine.match_script(text, nlp_result, context, [config])

            if match_result:
                response = lua_engine.generate_response(
                    match_result.script_id,
                    text,
                    nlp_result,
                    context
                )
                print(f"响应: {response}")
                print(f"下一个状态: {context.get('conversation_state')}")
            else:
                print("未匹配到规则")


def test_entity_analysis_script():
    """测试实体分析脚本"""
    print("\n=== 测试实体分析脚本 ===")

    lua_engine = LuaScriptEngine()

    config = LuaScriptConfig(
        script_path=project_root / "scripts" / "lua" / "entity_analysis.lua",
        name="entity_analysis_test",
        description="实体分析测试",
        priority=85,
        enabled=True,
        cache_size=100,
        max_execution_time=2.0,
        sandbox_mode=True
    )

    if lua_engine.load_script(config):
        print("实体分析脚本加载成功！")

        # 测试包含实体的输入
        text = "张三在北京工作"
        nlp_result = NLPPipelineResult(text)

        # 模拟实体识别结果
        nlp_result.entities = [
            {"text": "张三", "type": "PERSON", "start": 0, "end": 2},
            {"text": "北京", "type": "LOCATION", "start": 3, "end": 5}
        ]

        context = Context()
        context.update("text", text)

        match_result = lua_engine.match_script(text, nlp_result, context, [config])

        if match_result:
            print(f"匹配成功！优先级: {match_result.script_id}")
            print(f"元数据: {match_result.variables}")

            response = lua_engine.generate_response(
                match_result.script_id,
                text,
                nlp_result,
                context
            )

            if response:
                print(f"响应: {response}")
            else:
                print("响应生成失败")
        else:
            print("匹配失败")


def main():
    """主测试函数"""
    print("开始测试Lua脚本引擎...")

    try:
        test_lua_script_engine()
        test_conversation_flow_script()
        test_entity_analysis_script()

        print("\n=== 所有测试完成 ===")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()