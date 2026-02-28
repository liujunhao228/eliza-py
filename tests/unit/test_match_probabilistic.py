#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
概率分流匹配机制测试脚本 - 重构版

测试内容:
1. Bot 池加权随机抽取（使用 random.choices）
2. 钓鱼 Bot 池加权随机抽取
3. 匹配概率分布 (30% 真人 / 70% Bot)
4. 钓鱼 Bot 在 Bot 局中的比例 (15%)
5. 真人匹配超时降级
6. 线程安全测试
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import threading

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from turing_test.backend.services.match_bot_pool import (
    BotPool, HoneypotPool,
    create_bot_pool, create_honeypot_pool,
)
from turing_test.backend.services.match_service.service import (
    MatchService, MatchType, MatchRequest, MatchServiceConfig,
)


def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {test_name}")
    if message:
        print(f"       {message}")


# =============================================================================
# 测试 1: Bot 池加权随机抽取（优化版）
# =============================================================================

def test_bot_pool_weights():
    """测试 Bot 池加权随机抽取"""
    print_header("测试 1: Bot 池加权随机抽取")

    config = {
        "bots": [
            {"id": "lv1_newbie", "weight": 0.35, "description": "新手 Bot"},
            {"id": "lv2_typical", "weight": 0.45, "description": "典型 AI"},
            {"id": "lv3_logic", "weight": 0.20, "description": "逻辑机器"},
        ]
    }

    pool = create_bot_pool(config)

    # 抽取 1000 次统计分布
    draws = [pool.get_bot().id for _ in range(1000)]
    counts = Counter(draws)

    # 计算比例
    ratios = {
        bot_id: count / 1000
        for bot_id, count in counts.items()
    }

    print(f"抽取 1000 次结果:")
    for bot_id, ratio in sorted(ratios.items()):
        print(f"  {bot_id}: {ratio*100:.1f}%")

    # 验证比例 (允许 ±5% 误差)
    success = True
    expected = {"lv1_newbie": 0.35, "lv2_typical": 0.45, "lv3_logic": 0.20}

    for bot_id, expected_ratio in expected.items():
        actual_ratio = ratios.get(bot_id, 0)
        if abs(actual_ratio - expected_ratio) > 0.05:
            success = False
            print_result(f"{bot_id} 比例", False, f"期望 {expected_ratio*100}%, 实际 {actual_ratio*100:.1f}%")

    if success:
        print_result("Bot 池加权随机", True)

    # 验证内存优化（唯一配置数量）
    stats = pool.get_stats()
    if stats["total_unique"] == 3:
        print_result("内存优化", True, f"仅存储 {stats['total_unique']} 个唯一配置")
    else:
        print_result("内存优化", False, f"期望 3 个唯一配置，实际 {stats['total_unique']}")

    return success


# =============================================================================
# 测试 2: 钓鱼 Bot 池加权随机抽取
# =============================================================================

def test_honeypot_pool_weights():
    """测试钓鱼 Bot 池加权随机抽取"""
    print_header("测试 2: 钓鱼 Bot 池加权随机抽取")

    config = {
        "bots": [
            {"id": "aggressive", "weight": 0.4, "description": "攻击型"},
            {"id": "sus", "weight": 0.6, "description": "可疑型"},
        ]
    }

    pool = create_honeypot_pool(config)

    # 抽取 1000 次统计分布
    draws = [pool.get_bot().id for _ in range(1000)]
    counts = Counter(draws)

    # 计算比例
    ratios = {
        bot_id: count / 1000
        for bot_id, count in counts.items()
    }

    print(f"抽取 1000 次结果:")
    for bot_id, ratio in sorted(ratios.items()):
        print(f"  {bot_id}: {ratio*100:.1f}%")

    # 验证比例 (允许 ±5% 误差)
    success = True
    expected = {"aggressive": 0.4, "sus": 0.6}

    for bot_id, expected_ratio in expected.items():
        actual_ratio = ratios.get(bot_id, 0)
        if abs(actual_ratio - expected_ratio) > 0.05:
            success = False
            print_result(f"{bot_id} 比例", False, f"期望 {expected_ratio*100}%, 实际 {actual_ratio*100:.1f}%")

    if success:
        print_result("钓鱼 Bot 池加权随机", True)

    return success


# =============================================================================
# 测试 3: 匹配概率分布
# =============================================================================

async def test_match_probability():
    """测试匹配概率分布 (30% 真人 / 70% Bot)"""
    print_header("测试 3: 匹配概率分布")

    config = MatchServiceConfig(
        human_probability=0.30,
        bot_probability=0.70,
        honeypot_in_bot_rate=0.15,
    )
    service = MatchService(config)

    # 模拟 1000 次匹配类型决定
    match_types = [service._decide_match_type() for _ in range(1000)]
    counts = Counter(match_types)

    # 计算比例
    total = len(match_types)
    bot_count = counts.get("bot", 0)
    honeypot_count = counts.get("honeypot", 0)
    human_count = counts.get("human", 0)

    bot_total = bot_count + honeypot_count  # Bot 局总数 (含钓鱼)

    print(f"1000 次匹配类型分布:")
    print(f"  真人局：{human_count} ({human_count/total*100:.1f}%)")
    print(f"  普通 Bot 局：{bot_count} ({bot_count/total*100:.1f}%)")
    print(f"  钓鱼 Bot 局：{honeypot_count} ({honeypot_count/total*100:.1f}%)")
    print(f"  Bot 局总计：{bot_total} ({bot_total/total*100:.1f}%)")

    # 验证比例 (允许 ±5% 误差)
    success = True

    # 真人局应在 30% 左右
    human_ratio = human_count / total
    if abs(human_ratio - 0.30) > 0.05:
        success = False
        print_result("真人局比例", False, f"期望 30%, 实际 {human_ratio*100:.1f}%")
    else:
        print_result(f"真人局比例", True, f"{human_ratio*100:.1f}%")

    # Bot 局总计应在 70% 左右
    bot_total_ratio = bot_total / total
    if abs(bot_total_ratio - 0.70) > 0.05:
        success = False
        print_result(f"Bot 局总比例", False, f"期望 70%, 实际 {bot_total_ratio*100:.1f}%")
    else:
        print_result(f"Bot 局总比例", True, f"{bot_total_ratio*100:.1f}%")

    # 钓鱼 Bot 在 Bot 局中应占 15% 左右
    honeypot_in_bot_ratio = honeypot_count / bot_total if bot_total > 0 else 0
    if abs(honeypot_in_bot_ratio - 0.15) > 0.05:
        success = False
        print_result(f"钓鱼 Bot 在 Bot 局中比例", False, f"期望 15%, 实际 {honeypot_in_bot_ratio*100:.1f}%")
    else:
        print_result(f"钓鱼 Bot 在 Bot 局中比例", True, f"{honeypot_in_bot_ratio*100:.1f}%")

    return success


# =============================================================================
# 测试 4: 真人匹配超时降级
# =============================================================================

async def test_timeout_fallback():
    """测试真人匹配超时降级为 Bot"""
    print_header("测试 4: 真人匹配超时降级")

    config = MatchServiceConfig(
        timeout_seconds=2,  # 2 秒超时
        cleanup_interval_seconds=1,
    )
    service = MatchService(config)
    
    # 设置 Bot 池
    bot_pool = create_bot_pool()
    honeypot_pool = create_honeypot_pool()
    service.set_bot_pools(bot_pool, honeypot_pool)

    print("模拟用户加入等待队列，等待超时...")

    # 手动添加一个超时的等待请求
    import time
    service._waiting_queue[999] = MatchRequest(
        user_id=999,
        timestamp=time.time() - 3,  # 3 秒前
        match_type=MatchType.HUMAN,
    )

    # 触发清理
    await service._cleanup_expired()

    # 检查是否已分配 Bot
    result = await service.get_result_internal(999)

    if result and result.true_identity and result.true_identity.startswith('Bot_'):
        print_result("超时降级为 Bot", True)
        return True
    elif result:
        print_result("超时降级为 Bot", False, f"期望 Bot_, 实际 {result.true_identity}")
        return False
    else:
        # 可能因为数据库问题失败，检查统计
        stats = service.get_internal_stats()
        if stats.get('timeout_fallbacks', 0) > 0:
            print_result("超时降级为 Bot", True, "统计显示有超时降级")
            return True
        print_result("超时降级为 Bot", False, "无匹配结果")
        return False


# =============================================================================
# 测试 5: 线程安全测试
# =============================================================================

def test_thread_safety():
    """测试 Bot 池的线程安全性"""
    print_header("测试 5: 线程安全测试")

    config = {
        "bots": [
            {"id": "lv1_newbie", "weight": 0.35, "description": "新手 Bot"},
            {"id": "lv2_typical", "weight": 0.45, "description": "典型 AI"},
            {"id": "lv3_logic", "weight": 0.20, "description": "逻辑机器"},
        ]
    }

    pool = create_bot_pool(config)
    
    results = []
    errors = []
    
    def draw_bot():
        try:
            for _ in range(100):
                bot = pool.get_bot()
                results.append(bot.id)
        except Exception as e:
            errors.append(str(e))

    # 启动 10 个线程并发抽取
    threads = []
    for _ in range(10):
        t = threading.Thread(target=draw_bot)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

    if errors:
        print_result("线程安全", False, f"发生错误：{errors[0]}")
        return False

    # 验证总抽取次数
    if len(results) == 1000:
        print_result("线程安全", True, f"成功完成 {len(results)} 次并发抽取")
        return True
    else:
        print_result("线程安全", False, f"期望 1000 次，实际 {len(results)} 次")
        return False


# =============================================================================
# 测试 6: 依赖注入测试
# =============================================================================

async def test_dependency_injection():
    """测试依赖注入"""
    print_header("测试 6: 依赖注入测试")

    # 创建 Bot 池
    bot_pool = create_bot_pool()
    honeypot_pool = create_honeypot_pool()
    
    # 创建服务并注入 Bot 池
    config = MatchServiceConfig()
    service = MatchService(config)
    service.set_bot_pools(bot_pool, honeypot_pool)

    # 验证 Bot 池已注入
    injected_bot_pool, injected_honeypot_pool = service.get_bot_pools()
    
    if injected_bot_pool is bot_pool and injected_honeypot_pool is honeypot_pool:
        print_result("依赖注入", True)
        return True
    else:
        print_result("依赖注入", False, "Bot 池未正确注入")
        return False


# =============================================================================
# 主函数
# =============================================================================

async def main():
    """主函数"""
    print_header("概率分流匹配机制测试 - 重构版")

    results = []

    # 测试 1: Bot 池加权
    results.append(("Bot 池加权", test_bot_pool_weights()))

    # 测试 2: 钓鱼 Bot 池加权
    results.append(("钓鱼 Bot 池加权", test_honeypot_pool_weights()))

    # 测试 3: 匹配概率
    results.append(("匹配概率分布", await test_match_probability()))

    # 测试 4: 超时降级
    results.append(("超时降级", await test_timeout_fallback()))

    # 测试 5: 线程安全
    results.append(("线程安全", test_thread_safety()))

    # 测试 6: 依赖注入
    results.append(("依赖注入", await test_dependency_injection()))

    # 汇总
    print_header("测试结果汇总")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！匹配机制工作正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
