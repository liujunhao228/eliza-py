#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理器增强功能测试
测试用户画像和时间感知上下文变量
"""

import sys
from datetime import datetime


def test_time_context():
    """测试时间上下文变量"""
    from alice.managers import ContextManager

    print("=" * 60)
    print("测试 1: 时间上下文变量")
    print("=" * 60)

    cm = ContextManager()
    time_ctx = cm.get_time_context()

    print(f"✓ year: {time_ctx['year']}")
    print(f"✓ month: {time_ctx['month']}")
    print(f"✓ day: {time_ctx['day']}")
    print(f"✓ weekday: {time_ctx['weekday']} (0=周一，6=周日)")
    print(f"✓ weekday_name: {time_ctx['weekday_name']}")
    print(f"✓ hour: {time_ctx['hour']}")
    print(f"✓ minute: {time_ctx['minute']}")
    print(f"✓ second: {time_ctx['second']}")
    print(f"✓ category_time: {time_ctx['category_time']}")

    # 验证所有必需字段存在
    required_fields = [
        "year", "month", "day", "weekday", "weekday_name",
        "hour", "minute", "second", "category_time"
    ]
    for field in required_fields:
        assert field in time_ctx, f"缺少必需字段：{field}"

    print("✓ 所有时间字段都存在\n")
    return True


def test_formatted_time_variables():
    """测试格式化时间变量"""
    from alice.managers import ContextManager

    print("=" * 60)
    print("测试 2: 格式化时间变量")
    print("=" * 60)

    cm = ContextManager()
    time_vars = cm.get_formatted_time_variables()

    print("支持的变量:")
    for key, value in time_vars.items():
        print(f"  {{{key}}}: {value}")

    # 验证所有必需字段存在
    required_fields = [
        "year", "month", "day", "weekday", "weekday_name",
        "hour", "minute", "second", "category_time"
    ]
    for field in required_fields:
        assert field in time_vars, f"缺少必需字段：{field}"

    print("✓ 所有格式化变量都存在\n")
    return True


def test_user_profile():
    """测试用户画像功能"""
    from alice.managers import ContextManager

    print("=" * 60)
    print("测试 3: 用户画像功能")
    print("=" * 60)

    cm = ContextManager()

    # 初始状态
    assert cm.get_user_profile() is None, "初始状态用户画像应为 None"
    print("✓ 初始状态：用户画像为 None")

    # 设置用户画像
    cm.set_user_profile(name="张三", nickname="小张", address_form="您")

    profile = cm.get_user_profile()
    assert profile is not None, "设置后用户画像不应为 None"
    assert profile.name == "张三", f"姓名应为'张三'，实际为'{profile.name}'"
    assert profile.nickname == "小张", f"昵称应为'小张'，实际为'{profile.nickname}'"
    assert profile.address_form == "您", f"称呼偏好应为'您'，实际为'{profile.address_form}'"

    print(f"✓ 用户姓名：{cm.get_user_name()}")
    print(f"✓ 用户昵称：{cm.get_user_nickname()}")
    print(f"✓ 称呼偏好：{cm.get_address_form()}")

    # 测试用户偏好
    cm.set_user_preference("favorite_color", "蓝色")
    assert cm.get_user_preference("favorite_color") == "蓝色"
    assert cm.get_user_preference("unknown_pref", "默认值") == "默认值"
    print("✓ 用户偏好设置和获取正常")

    print()
    return True


def test_turn_count():
    """测试对话轮数追踪"""
    from alice.managers import ContextManager

    print("=" * 60)
    print("测试 4: 对话轮数追踪")
    print("=" * 60)

    cm = ContextManager()

    # 初始轮数为 0
    assert cm.get_turn_count() == 0, f"初始轮数应为 0，实际为{cm.get_turn_count()}"
    print(f"✓ 初始轮数：{cm.get_turn_count()}")

    # 更新对话
    cm.update("你好", "你好！有什么可以帮你的？")
    assert cm.get_turn_count() == 1, f"第 1 轮后轮数应为 1，实际为{cm.get_turn_count()}"
    print(f"✓ 第 1 轮后：{cm.get_turn_count()}")

    cm.update("今天天气不错", "是的，阳光明媚")
    assert cm.get_turn_count() == 2, f"第 2 轮后轮数应为 2，实际为{cm.get_turn_count()}"
    print(f"✓ 第 2 轮后：{cm.get_turn_count()}")

    cm.update("你喜欢什么颜色", "我喜欢蓝色")
    assert cm.get_turn_count() == 3, f"第 3 轮后轮数应为 3，实际为{cm.get_turn_count()}"
    print(f"✓ 第 3 轮后：{cm.get_turn_count()}")

    print()
    return True


def test_context_summary():
    """测试上下文摘要"""
    from alice.managers import ContextManager

    print("=" * 60)
    print("测试 5: 上下文摘要")
    print("=" * 60)

    cm = ContextManager()

    # 设置用户画像
    cm.set_user_profile(name="李四", nickname="小李", address_form="你")

    # 添加几轮对话
    cm.update("你好", "你好！")
    cm.update("再见", "再见！")

    summary = cm.get_context_summary()

    print(f"✓ 总轮数：{summary['total_turns']}")
    print(f"✓ 当前话题：{summary['current_topic']}")
    print(f"✓ 用户画像：{summary['user_profile']}")
    print(f"✓ 时间上下文：{summary['time_context']}")

    # 验证摘要包含新字段
    assert "user_profile" in summary, "摘要应包含 user_profile"
    assert "time_context" in summary, "摘要应包含 time_context"
    assert summary["user_profile"]["name"] == "李四"
    assert summary["time_context"]["turn_count"] == 2

    print()
    return True


def test_yaml_script_placeholders():
    """测试 YAML 脚本引擎中的占位符替换"""
    from alice.scripts.yaml_script_engine import YAMLScriptEngine
    import tempfile
    import os

    print("=" * 60)
    print("测试 6: YAML 脚本引擎占位符替换")
    print("=" * 60)

    # 创建临时脚本文件（正确的 YAML 列表格式）
    script_content = '''- intent: greeting
  patterns:
  - 你好
  templates:
  - "现在是{year}年{month}月{day}日，{category_time}好！"
  - "今天是{weekday_name}，{hour}点{minute}分，{user_name}你好！"
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write(script_content)
        temp_file = f.name

    try:
        engine = YAMLScriptEngine(script_file=temp_file)

        # 测试上下文
        context = {
            "time_context": {
                "year": 2026,
                "month": 2,
                "day": 20,
                "weekday": 4,
                "weekday_name": "星期五",
                "hour": 14,
                "minute": 30,
                "second": 0,
                "category_time": "下午",
            },
            "user_profile": {
                "name": "王先生",
                "nickname": "小王",
                "address_form": "您",
            },
            "address_form": "您",
        }

        # 获取意图
        intent = engine.intents.get("greeting")
        assert intent is not None, "应找到 greeting 意图"

        # 测试模板填充
        template = intent.templates[0]
        print(f"原始模板：{template}")

        filled = engine._fill_placeholders(template, context)
        print(f"填充后：{filled}")

        # 验证时间变量被替换
        assert "2026" in filled, "年份应被替换"
        assert "2" in filled, "月份应被替换"
        assert "20" in filled, "日期应被替换"
        assert "下午" in filled, "时间段应被替换"

        # 测试第二个模板
        template2 = intent.templates[1]
        print(f"\n原始模板 2: {template2}")
        filled2 = engine._fill_placeholders(template2, context)
        print(f"填充后 2: {filled2}")

        assert "星期五" in filled2, "星期名称应被替换"
        assert "王先生" in filled2, "用户姓名应被替换"

        print("✓ 占位符替换正常")
        print()
        return True

    finally:
        os.unlink(temp_file)


def test_clear_resets_all():
    """测试 clear 方法重置所有状态"""
    from alice.managers import ContextManager

    print("=" * 60)
    print("测试 7: clear 方法重置所有状态")
    print("=" * 60)

    cm = ContextManager()

    # 设置状态
    cm.set_user_profile(name="测试用户")
    cm.update("你好", "你好")
    cm.update("再见", "再见")

    # 验证状态已设置
    assert cm.get_user_profile() is not None
    assert cm.get_turn_count() == 2

    # 清空
    cm.clear()

    # 验证状态已重置
    assert cm.get_user_profile() is None, "clear 后用户画像应为 None"
    assert cm.get_turn_count() == 0, f"clear 后轮数应为 0，实际为{cm.get_turn_count()}"

    print("✓ clear 方法正确重置所有状态")
    print()
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("上下文管理器增强功能测试")
    print("=" * 60 + "\n")

    tests = [
        ("时间上下文变量", test_time_context),
        ("格式化时间变量", test_formatted_time_variables),
        ("用户画像功能", test_user_profile),
        ("对话轮数追踪", test_turn_count),
        ("上下文摘要", test_context_summary),
        ("YAML 脚本占位符替换", test_yaml_script_placeholders),
        ("clear 方法重置", test_clear_resets_all),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} 测试失败：{e}\n")
            failed += 1
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
