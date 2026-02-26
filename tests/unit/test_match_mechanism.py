#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
匹配机制测试脚本（简化版）

测试简化后的匹配机制功能：
1. 20% AI 对照组分配
2. 80% 真人 FIFO 匹配
3. 匹配结果暂存
"""

import asyncio
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = "F:/eliza-py"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import settings
from turing_test.backend.services.match_service import MatchService


async def test_ai_control_group():
    """测试 AI 对照组分配（20% 概率）"""
    print("\n" + "=" * 60)
    print("测试 1: AI 对照组分配（20% 概率）")
    print("=" * 60)

    service = MatchService()

    # 模拟 100 次匹配，统计 AI 分配比例
    ai_count = 0
    total = 100

    for i in range(total):
        # 模拟加入队列
        await service.add_to_queue(i, 1000 + i, 100)
        
        # 检查是否直接分配 AI
        if i in service.match_results:
            result = service.match_results[i]
            if result["opponent_type"] in ["ai", "honeypot"]:
                ai_count += 1

    rate = ai_count / total * 100
    print(f"\n100 次模拟结果:")
    print(f"  AI 对照组：{ai_count} 次 ({rate:.1f}%)")
    print(f"  期望值：~20%")
    print(f"  状态：{'✅' if 15 <= rate <= 25 else '⚠️'} 在合理范围内")

    print("\n✅ AI 对照组分配测试完成")


async def test_fifo_match():
    """测试 FIFO 真人匹配"""
    print("\n" + "=" * 60)
    print("测试 2: FIFO 真人匹配")
    print("=" * 60)

    service = MatchService()

    # 模拟用户 1 加入队列（80% 概率会加入等待队列）
    print("\n用户 1 加入队列...")
    await service.add_to_queue(101, 2001, 100)
    
    # 如果用户 1 被分配到 AI 对照组，则手动加入队列
    if 101 not in service.waiting_queue:
        service.waiting_queue[101] = {
            "timestamp": datetime.now().timestamp(),
            "websocket_ref": 2001,
            "user_score": 100,
        }
        print("  用户 1 手动加入等待队列")
    else:
        print("  用户 1 已在等待队列")

    # 模拟用户 2 加入队列（应该匹配用户 1）
    print("用户 2 加入队列...")
    await service.add_to_queue(102, 2002, 100)

    # 检查匹配结果
    print("\n匹配结果:")
    if 102 in service.match_results:
        result = service.match_results[102]
        print(f"  用户 2 匹配结果：session_id={result['session_id']}, type={result['opponent_type']}")
    
    if 101 in service.match_results:
        result = service.match_results[101]
        print(f"  用户 1 匹配结果：session_id={result['session_id']}, type={result['opponent_type']}")

    print("\n✅ FIFO 真人匹配测试完成")


async def test_result_storage():
    """测试匹配结果暂存"""
    print("\n" + "=" * 60)
    print("测试 3: 匹配结果暂存与获取")
    print("=" * 60)

    service = MatchService()

    # 模拟匹配结果
    service.match_results[201] = {
        "session_id": 999,
        "opponent_type": "human",
        "is_honeypot": False,
        "matched_at": datetime.now().isoformat(),
    }

    # 获取结果
    result = await service.get_result(201)
    print(f"\n获取用户 201 的结果:")
    print(f"  session_id: {result['session_id']}")
    print(f"  opponent_type: {result['opponent_type']}")
    print(f"  is_honeypot: {result['is_honeypot']}")

    # 清除结果
    await service.clear_result(201)
    result_after = await service.get_result(201)
    print(f"\n清除结果后：{result_after}")

    print("\n✅ 匹配结果暂存测试完成")


async def test_queue_operations():
    """测试队列操作"""
    print("\n" + "=" * 60)
    print("测试 4: 队列操作")
    print("=" * 60)

    service = MatchService()

    # 添加用户
    print("\n添加用户到队列:")
    await service.add_to_queue(301, 3001, 100)
    await service.add_to_queue(302, 3002, 100)
    await service.add_to_queue(303, 3003, 100)
    
    print(f"  队列大小：{service.get_queue_size()}")
    print(f"  用户 301 在队列：{service.is_user_waiting(301)}")
    print(f"  用户 304 在队列：{service.is_user_waiting(304)}")

    # 移除用户
    print("\n移除用户 302:")
    await service.remove_from_queue(302)
    print(f"  队列大小：{service.get_queue_size()}")
    print(f"  用户 302 在队列：{service.is_user_waiting(302)}")

    print("\n✅ 队列操作测试完成")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🧪 简化匹配机制测试")
    print("=" * 60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        await test_ai_control_group()
        await test_fifo_match()
        await test_result_storage()
        await test_queue_operations()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
