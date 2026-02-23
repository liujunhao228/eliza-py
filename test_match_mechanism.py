#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
匹配机制测试脚本

测试完善后的匹配机制功能：
1. 优先级匹配算法
2. 钓鱼机器人行为拟真度
3. 匹配统计功能
4. AI 响应时间分布
"""

import asyncio
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = "F:/eliza-py"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import settings
from turing_test.backend.services.match_service import MatchService, MatchPriority, MatchStatistics
from turing_test.backend.services.honeypot_service import HoneypotService, get_honeypot_service


async def test_match_priority():
    """测试匹配优先级功能"""
    print("\n" + "=" * 60)
    print("测试 1: 匹配优先级功能")
    print("=" * 60)
    
    service = MatchService()
    
    # 测试优先级计算
    test_cases = [
        (30, MatchPriority.RETURNING, "低积分用户（回流）"),
        (100, MatchPriority.NORMAL, "普通积分用户"),
        (250, MatchPriority.VIP, "高积分用户（VIP）"),
    ]
    
    print("\n优先级计算测试:")
    for score, expected, description in test_cases:
        result = service._calculate_priority(score)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {description} ({score}分) -> {result.value}")
    
    # 测试队列添加
    print("\n队列添加测试:")
    await service.add_to_queue(1, 1001, 30)   # 回流用户
    await service.add_to_queue(2, 1002, 100)  # 普通用户
    await service.add_to_queue(3, 1003, 250)  # VIP 用户
    await service.add_to_queue(4, 1004, 50)   # 回流用户
    
    print(f"  队列大小：{service.get_queue_size()}")
    
    # 测试匹配算法（优先级 + FIFO）
    print("\n匹配算法测试:")
    match1 = await service.find_match(1)  # 回流用户，应该匹配另一个回流用户（用户 4）
    print(f"  用户 1（回流）匹配到：用户 {match1} (期望：4)")
    
    # 清理
    await service.remove_from_queue(1)
    await service.remove_from_queue(2)
    await service.remove_from_queue(3)
    await service.remove_from_queue(4)
    
    print("\n✅ 优先级匹配功能测试完成")


async def test_honeypot_behavior():
    """测试钓鱼机器人行为拟真度"""
    print("\n" + "=" * 60)
    print("测试 2: 钓鱼机器人行为拟真度")
    print("=" * 60)
    
    service = get_honeypot_service()
    
    # 测试行为模式选择
    print("\n行为模式选择测试:")
    for i in range(5):
        profile = service.select_behavior_profile(100 + i, user_meta_count=i)
        print(f"  会话 {100+i} (元对话{i}次) -> {profile}")
    
    # 测试打字延迟模拟
    print("\n打字延迟模拟测试:")
    session_id = 200
    service.select_behavior_profile(session_id)
    
    for length in [10, 30, 50, 80]:
        delay = service.simulate_typing_delay(length, session_id)
        print(f"  响应长度 {length} -> 延迟 {delay:.2f}秒")
    
    # 测试人类特征添加
    print("\n人类特征添加测试:")
    base_texts = [
        "我是真人",
        "正在参加这个实验",
        "你觉得呢",
    ]
    
    for text in base_texts:
        humanized = service.add_human_like_variations(text, session_id)
        print(f"  原始：{text}")
        print(f"  拟人：{humanized}")
        print()
    
    # 测试元对话响应
    print("元对话响应测试:")
    meta_questions = [
        "你是真人吗？",
        "我怀疑你的身份",
        "你是不是机器人？",
    ]
    
    for question in meta_questions:
        response = service.generate_meta_response(session_id, question)
        if response:
            print(f"  问：{question}")
            print(f"  答：{response}")
            print()
    
    print("\n✅ 钓鱼机器人行为拟真度测试完成")


async def test_ai_typing_delay():
    """测试 AI 响应时间分布"""
    print("\n" + "=" * 60)
    print("测试 3: AI 响应时间分布")
    print("=" * 60)
    
    service = MatchService()
    
    # 模拟 100 次延迟计算
    print("\nAI 打字延迟分布测试 (100 次采样):")
    delays = [service._calculate_ai_typing_delay() for _ in range(100)]
    
    # 统计分布
    fast_count = sum(1 for d in delays if d <= 3)
    normal_count = sum(1 for d in delays if 3 < d <= 8)
    slow_count = sum(1 for d in delays if 8 < d <= 15)
    very_slow_count = sum(1 for d in delays if d > 15)
    
    print(f"  快速 (0-3 秒):   {fast_count:3d} 次 ({fast_count:.1f}%)")
    print(f"  正常 (3-8 秒):   {normal_count:3d} 次 ({normal_count:.1f}%)")
    print(f"  慢速 (8-15 秒):  {slow_count:3d} 次 ({slow_count:.1f}%)")
    print(f"  极慢 (15-30 秒): {very_slow_count:3d} 次 ({very_slow_count:.1f}%)")
    
    # 计算统计
    avg_delay = sum(delays) / len(delays)
    min_delay = min(delays)
    max_delay = max(delays)
    
    print(f"\n  平均延迟：{avg_delay:.2f}秒")
    print(f"  最小延迟：{min_delay:.2f}秒")
    print(f"  最大延迟：{max_delay:.2f}秒")
    
    print("\n✅ AI 响应时间分布测试完成")


async def test_match_statistics():
    """测试匹配统计功能"""
    print("\n" + "=" * 60)
    print("测试 4: 匹配统计功能")
    print("=" * 60)
    
    service = MatchService()
    
    # 模拟匹配记录
    print("\n模拟匹配记录:")
    test_matches = [
        (1, 2, "human", 5.2),
        (3, -1, "ai", 12.5),
        (4, 5, "human", 3.1),
        (6, -1, "honeypot", 30.0),
        (7, 8, "human", 7.8),
    ]
    
    for user_id, opponent_id, match_type, wait_time in test_matches:
        service._record_match(user_id, opponent_id, match_type, wait_time)
        print(f"  用户{user_id} vs {'用户'+str(opponent_id) if opponent_id > 0 else match_type}, "
              f"等待{wait_time:.1f}秒")
    
    # 获取统计信息
    stats = service.statistics.get_stats()
    
    print("\n统计信息:")
    print(f"  总匹配数：{stats['total_matches']}")
    print(f"  真人匹配：{stats['human_matches']}")
    print(f"  AI 匹配：{stats['ai_matches']}")
    print(f"  钓鱼机器人匹配：{stats['honeypot_matches']}")
    print(f"  真人匹配成功率：{stats['human_success_rate']}")
    print(f"  平均等待时间：{stats['avg_wait_time']}")
    
    print("\n✅ 匹配统计功能测试完成")


async def test_honeypot_assignment():
    """测试钓鱼机器人分配逻辑"""
    print("\n" + "=" * 60)
    print("测试 5: 钓鱼机器人分配逻辑")
    print("=" * 60)
    
    service = MatchService()
    
    # 模拟不同用户积分的钓鱼机器人分配
    print("\n钓鱼机器人分配概率测试 (各 100 次模拟):")
    
    test_scores = [
        (30, "低积分用户（回流）"),
        (100, "普通积分用户"),
        (250, "高积分用户（VIP）"),
    ]
    
    for score, description in test_scores:
        honeypot_count = 0
        for _ in range(100):
            if await service._should_assign_honeypot(1000 + score, score):
                honeypot_count += 1
        print(f"  {description} ({score}分): {honeypot_count}% 分配钓鱼机器人")
    
    # 测试频繁元对话用户
    print("\n频繁元对话用户测试:")
    user_id = 9999
    # 模拟用户匹配历史，包含多次元对话
    service.user_match_history[user_id] = [
        {"meta_count": 5, "timestamp": datetime.utcnow().timestamp()},
        {"meta_count": 6, "timestamp": datetime.utcnow().timestamp()},
        {"meta_count": 4, "timestamp": datetime.utcnow().timestamp()},
        {"meta_count": 7, "timestamp": datetime.utcnow().timestamp()},
        {"meta_count": 5, "timestamp": datetime.utcnow().timestamp()},
    ]
    
    honeypot_count = 0
    for _ in range(100):
        if await service._should_assign_honeypot(user_id, 100):
            honeypot_count += 1
    
    print(f"  频繁元对话用户：{honeypot_count}% 分配钓鱼机器人 (期望：~30%)")
    
    print("\n✅ 钓鱼机器人分配逻辑测试完成")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🧪 匹配机制完善测试")
    print("=" * 60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 运行所有测试
        await test_match_priority()
        await test_honeypot_behavior()
        await test_ai_typing_delay()
        await test_match_statistics()
        await test_honeypot_assignment()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
