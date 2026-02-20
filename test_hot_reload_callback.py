#!/usr/bin/env python3
"""测试热重载器回调"""

import time
from pathlib import Path

from alice.alice_v2 import AliceBot

# 记录回调调用
reload_events = []

def on_reload(result):
    reload_events.append({
        'time': time.time(),
        'success': result.success,
        'script_reloaded': result.script_reloaded,
        'rules_reloaded': result.rules_reloaded,
        'error': result.error,
    })
    print(f"\n[重载回调] 成功={result.success}, 脚本={result.script_reloaded}, 规则={result.rules_reloaded}")
    if result.error:
        print(f"  错误：{result.error}")

# 创建 Alice 实例
print("创建 Alice 实例（启用热重载）...")
alice = AliceBot(enable_hot_reload=True, hot_reload_mode="auto")

# 添加回调
if alice.dialogue_engine.hot_reloader:
    alice.dialogue_engine.hot_reloader.add_reload_callback(on_reload)
    print("✅ 已添加重载回调")
else:
    print("❌ 热重载器未启用")

print(f"\n热重载状态：{alice.get_hot_reload_status()}")
print("\n请在 30 秒内修改 demo.yaml 文件...")
print("修改后等待 3 秒查看回调结果\n")

time.sleep(30)

print(f"\n\n捕获到的重载事件：{len(reload_events)}")
for i, event in enumerate(reload_events, 1):
    print(f"{i}. 时间={event['time']:.2f}, 成功={event['success']}, 脚本={event['script_reloaded']}, 规则={event['rules_reloaded']}")
    if event['error']:
        print(f"   错误：{event['error']}")

alice.cleanup()
