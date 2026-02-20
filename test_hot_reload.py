#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热重载功能测试脚本

使用方法:
    python test_hot_reload.py

测试内容:
1. 手动重载测试
2. 自动重载测试 (需要修改 YAML 文件)
"""

import time
import threading
from pathlib import Path

from alice.alice_v2 import AliceBot
from alice.config import ENABLE_HOT_RELOAD_BY_DEFAULT, HOT_RELOAD_MODE


def test_manual_reload():
    """测试手动重载功能"""
    print("=" * 60)
    print("测试 1: 手动重载功能")
    print("=" * 60)

    # 创建启用热重载的 Alice 实例
    alice = AliceBot(
        enable_hot_reload=True,
        hot_reload_mode="manual",  # 手动模式
    )

    # 检查热重载状态
    status = alice.get_hot_reload_status()
    print(f"热重载状态：{status}")

    # 测试手动重载
    print("\n执行手动重载...")
    result = alice.reload_all()
    print(f"重载结果：成功={result.success}")
    print(f"  - 脚本重载：{result.script_reloaded}")
    print(f"  - 规则重载：{result.rules_reloaded}")
    if result.error:
        print(f"  - 错误：{result.error}")

    # 测试对话
    print("\n测试对话:")
    response = alice.respond("你好")
    print(f"  输入：你好")
    print(f"  响应：{response}")

    alice.cleanup()
    print("\n✅ 手动重载测试完成\n")


def test_auto_reload():
    """测试自动重载功能"""
    print("=" * 60)
    print("测试 2: 自动重载功能")
    print("=" * 60)

    # 创建启用热重载的 Alice 实例
    alice = AliceBot(
        enable_hot_reload=True,
        hot_reload_mode="auto",  # 自动模式
    )

    status = alice.get_hot_reload_status()
    print(f"热重载状态：{status}")
    print(f"热重载器运行中：{alice.dialogue_engine.hot_reloader.is_running() if alice.dialogue_engine.hot_reloader else False}")

    # 测试对话
    print("\n测试对话:")
    response = alice.respond("你好")
    print(f"  输入：你好")
    print(f"  响应：{response}")

    # 等待一段时间，让文件监控运行
    print("\n等待 5 秒让监控运行...")
    time.sleep(5)

    alice.cleanup()
    print("\n✅ 自动重载测试完成\n")


def test_reload_callback():
    """测试重载回调功能"""
    print("=" * 60)
    print("测试 3: 重载回调功能")
    print("=" * 60)

    reload_count = [0]

    def on_reload(result):
        reload_count[0] += 1
        print(f"  [回调] 第 {reload_count[0]} 次重载 - 成功：{result.success}")

    alice = AliceBot(
        enable_hot_reload=True,
        hot_reload_mode="manual",
    )

    # 添加回调
    if alice.dialogue_engine.hot_reloader:
        alice.dialogue_engine.hot_reloader.add_reload_callback(on_reload)
        print("已添加重载回调")

    # 执行重载
    print("执行重载...")
    result = alice.reload_all()

    alice.cleanup()
    print("\n✅ 重载回调测试完成\n")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Alice 热重载功能测试")
    print("=" * 60 + "\n")

    try:
        # 测试 1: 手动重载
        test_manual_reload()

        # 测试 2: 自动重载
        test_auto_reload()

        # 测试 3: 重载回调
        test_reload_callback()

        print("=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
