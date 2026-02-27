#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
登录尝试跟踪服务测试
"""

import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from turing_test.backend.services.login_attempt_service import (
    LoginAttemptService,
    MemoryLoginAttemptStore,
    config,
)


async def test_login_attempt_tracking():
    """测试登录尝试跟踪"""
    
    print("=" * 60)
    print("登录尝试跟踪服务测试")
    print("=" * 60)
    
    store = MemoryLoginAttemptStore()
    service = LoginAttemptService(store)
    
    test_nickname = "testuser"
    
    # 测试 1: 初始状态 - 无限制
    print("\n[测试 1] 初始状态检查")
    is_locked, remaining = await service.check_lockout(test_nickname)
    if not is_locked and remaining == 0:
        print("  ✅ 通过：新账户未被锁定")
    else:
        print(f"  ❌ 失败：新账户不应被锁定 (locked={is_locked}, remaining={remaining})")
    
    # 测试 2: 记录失败尝试
    print("\n[测试 2] 记录失败尝试")
    for i in range(1, config.max_attempts):
        attempts, is_locked = await service.record_failed_login(test_nickname)
        print(f"  第 {i} 次失败：尝试次数={attempts}, 锁定={is_locked}")
    
    # 测试 3: 达到最大失败次数后锁定
    print("\n[测试 3] 达到最大失败次数后锁定")
    attempts, is_locked = await service.record_failed_login(test_nickname)
    if is_locked and attempts >= config.max_attempts:
        print(f"  ✅ 通过：账户已锁定 (尝试次数={attempts})")
    else:
        print(f"  ❌ 失败：账户应该被锁定 (尝试次数={attempts}, 锁定={is_locked})")
    
    # 测试 4: 锁定状态下检查
    print("\n[测试 4] 锁定状态检查")
    is_locked, remaining = await service.check_lockout(test_nickname)
    if is_locked and remaining > 0:
        print(f"  ✅ 通过：账户仍处于锁定状态 (剩余 {remaining} 秒)")
    else:
        print(f"  ❌ 失败：账户应该被锁定 (locked={is_locked}, remaining={remaining})")
    
    # 测试 5: 成功登录后重置
    print("\n[测试 5] 成功登录重置计数")
    await service.record_successful_login(test_nickname)
    is_locked, remaining = await service.check_lockout(test_nickname)
    if not is_locked and remaining == 0:
        print("  ✅ 通过：成功登录后锁定已解除")
    else:
        print(f"  ❌ 失败：锁定应该被解除 (locked={is_locked}, remaining={remaining})")
    
    # 测试 6: 剩余尝试次数
    print("\n[测试 6] 剩余尝试次数检查")
    await service.record_failed_login("user2")
    await service.record_failed_login("user2")
    remaining = await service.get_remaining_attempts("user2")
    expected = config.max_attempts - 2
    if remaining == expected:
        print(f"  ✅ 通过：剩余尝试次数={remaining}")
    else:
        print(f"  ❌ 失败：剩余尝试次数应为 {expected}, 实际={remaining}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    # 显示配置
    print(f"\n当前配置:")
    print(f"  - 最大失败次数：{config.max_attempts}")
    print(f"  - 锁定时长：{config.lockout_duration_minutes} 分钟")


if __name__ == "__main__":
    asyncio.run(test_login_attempt_tracking())
