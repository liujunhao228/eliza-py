#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
匹配机制重构版测试脚本

测试新架构的各组件：
1. 配置管理
2. 概率决策算法
3. Bot 池加权随机
4. 队列管理器
5. 结果管理器
6. 匹配协调器
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from turing_test.backend.services.match_service import (
    MatchConfig,
    MatchService,
    MatchCoordinator,
    MatchQueue,
    ResultManager,
    ProbabilityAlgorithm,
    BotPool,
    BotPoolConfig,
    BotConfig,
    HoneypotPool,
    HoneypotPoolConfig,
    HoneypotBotConfig,
    MatchType,
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
# 测试 1: 配置管理
# =============================================================================

def test_config():
    """测试配置管理"""
    print_header("测试 1: 配置管理")

    # 测试默认配置
    config = MatchConfig()
    print(f"默认配置:")
    print(f"  human_probability: {config.human_probability}")
    print(f"  bot_probability: {config.bot_probability}")
    print(f"  honeypot_in_bot_rate: {config.honeypot_in_bot_rate}")
    print(f"  timeout_seconds: {config.timeout_seconds}")

    # 测试阈值计算
    honeypot_threshold, human_threshold = config.get_bot_thresholds()
    print(f"\n概率阈值:")
    print(f"  honeypot_threshold: {honeypot_threshold:.3f}")
    print(f"  human_threshold: {human_threshold:.3f}")

    # 验证阈值
    expected_honeypot = 0.15 * 0.70  # 0.105
    expected_human = expected_honeypot + 0.30  # 0.405

    success = (
        abs(honeypot_threshold - expected_honeypot) < 0.001 and
        abs(human_threshold - expected_human) < 0.001
    )

    print_result("配置阈值计算", success, f"期望 ({expected_honeypot:.3f}, {expected_human:.3f})")

    # 测试配置验证
    try:
        invalid_config = MatchConfig(human_probability=1.5)
        invalid_config.validate()
        print_result("配置验证", False, "应该抛出异常")
    except ValueError:
        print_result("配置验证", True)

    return success


# =============================================================================
# 测试 2: 概率决策算法
# =============================================================================

def test_probability_algorithm():
    """测试概率决策算法"""
    print_header("测试 2: 概率决策算法")

    config = MatchConfig(
        human_probability=0.30,
        bot_probability=0.70,
        honeypot_in_bot_rate=0.15,
    )
    algorithm = ProbabilityAlgorithm()

    # 模拟 1000 次决策
    results = [algorithm.decide_match_type(config) for _ in range(1000)]
    counts = Counter(results)

    total = len(results)
    human_count = counts.get(MatchType.HUMAN, 0)
    honeypot_count = counts.get(MatchType.HONEYPOT, 0)
    bot_count = counts.get(MatchType.BOT, 0)

    print(f"1000 次决策结果:")
    print(f"  真人局：{human_count} ({human_count/total*100:.1f}%)")
    print(f"  钓鱼 Bot 局：{honeypot_count} ({honeypot_count/total*100:.1f}%)")
    print(f"  普通 Bot 局：{bot_count} ({bot_count/total*100:.1f}%)")

    # 验证比例（允许 ±5% 误差）
    human_ratio = human_count / total
    bot_total_ratio = (bot_count + honeypot_count) / total

    success = (
        0.25 <= human_ratio <= 0.35 and
        0.65 <= bot_total_ratio <= 0.75
    )

    print_result("概率分布", success, f"真人~30%, Bot~70%")

    return success


# =============================================================================
# 测试 3: Bot 池加权随机
# =============================================================================

def test_bot_pool():
    """测试 Bot 池加权随机"""
    print_header("测试 3: Bot 池加权随机")

    config = BotPoolConfig(
        bots=[
            BotConfig(id="lv1_newbie", weight=0.35, description="新手 Bot"),
            BotConfig(id="lv2_typical", weight=0.45, description="典型 AI"),
            BotConfig(id="lv3_logic", weight=0.20, description="逻辑机器"),
        ]
    )
    pool = BotPool(config)

    # 抽取 1000 次
    draws = [pool.draw().id for _ in range(1000)]
    counts = Counter(draws)

    print(f"抽取 1000 次结果:")
    for bot_id, count in sorted(counts.items()):
        ratio = count / 1000 * 100
        print(f"  {bot_id}: {ratio:.1f}%")

    # 验证比例
    expected = {"lv1_newbie": 0.35, "lv2_typical": 0.45, "lv3_logic": 0.20}
    success = True

    for bot_id, expected_ratio in expected.items():
        actual_ratio = counts.get(bot_id, 0) / 1000
        if abs(actual_ratio - expected_ratio) > 0.05:
            success = False
            print_result(f"{bot_id} 比例", False, f"期望 {expected_ratio*100}%, 实际 {actual_ratio*100:.1f}%")

    if success:
        print_result("Bot 池加权随机", True)

    return success


# =============================================================================
# 测试 4: 钓鱼 Bot 池
# =============================================================================

def test_honeypot_pool():
    """测试钓鱼 Bot 池"""
    print_header("测试 4: 钓鱼 Bot 池")

    config = HoneypotPoolConfig(
        bots=[
            HoneypotBotConfig(id="aggressive", weight=0.4, description="攻击型"),
            HoneypotBotConfig(id="sus", weight=0.6, description="可疑型"),
        ]
    )
    pool = HoneypotPool(config)

    # 抽取 1000 次
    draws = [pool.draw().id for _ in range(1000)]
    counts = Counter(draws)

    print(f"抽取 1000 次结果:")
    for bot_id, count in sorted(counts.items()):
        ratio = count / 1000 * 100
        print(f"  {bot_id}: {ratio:.1f}%")

    # 验证比例
    expected = {"aggressive": 0.4, "sus": 0.6}
    success = True

    for bot_id, expected_ratio in expected.items():
        actual_ratio = counts.get(bot_id, 0) / 1000
        if abs(actual_ratio - expected_ratio) > 0.05:
            success = False
            print_result(f"{bot_id} 比例", False)

    if success:
        print_result("钓鱼 Bot 池加权随机", True)

    return success


# =============================================================================
# 测试 5: 队列管理器
# =============================================================================

async def test_queue_manager():
    """测试队列管理器"""
    print_header("测试 5: 队列管理器")

    queue = MatchQueue()

    # 测试加入队列
    from turing_test.backend.services.match_service import MatchRequest

    request1 = MatchRequest(user_id=101, websocket_ref=1001, user_score=100)
    request2 = MatchRequest(user_id=102, websocket_ref=1002, user_score=100)

    success1 = await queue.add(request1)
    success2 = await queue.add(request2)
    duplicate = await queue.add(request1)  # 重复加入

    print(f"加入队列：{success1}, {success2}")
    print(f"重复加入：{duplicate}")
    print(f"队列大小：{await queue.size()}")

    # 测试移除
    removed = await queue.remove(101)
    print(f"移除用户 101: {removed}")
    print(f"移除后队列大小：{await queue.size()}")

    # 测试快照
    snapshot = await queue.get_snapshot()
    print(f"快照请求数：{len(snapshot.requests)}")

    success = (
        success1 and success2 and
        not duplicate and
        await queue.size() == 1 and
        removed
    )

    print_result("队列管理器", success)
    return success


# =============================================================================
# 测试 6: 结果管理器
# =============================================================================

async def test_result_manager():
    """测试结果管理器"""
    print_header("测试 6: 结果管理器")

    manager = ResultManager()

    # 存储结果
    from turing_test.backend.services.match_service import MatchResultData
    from datetime import datetime, timezone

    result = MatchResultData(
        session_id=999,
        opponent_type="opponent",
        true_identity="Human",
        bot_level=None,
        is_honeypot=False,
        opponent_user_id=102,
        match_duration_ms=1500,
    )

    await manager.store(101, result)

    # 获取内部结果
    internal = await manager.get(101)
    print(f"内部结果：session_id={internal.session_id if internal else None}")

    # 获取安全结果
    safe = await manager.get_safe(101)
    print(f"安全结果：opponent_type={safe.opponent_type if safe else None}")

    # 验证安全过滤
    is_safe = (
        safe.opponent_type == "opponent" and
        not hasattr(safe, 'true_identity')
    )

    # 清除结果
    await manager.clear(101)
    cleared = await manager.get(101)

    success = (
        internal is not None and
        safe is not None and
        is_safe and
        cleared is None
    )

    print_result("结果管理器", success)
    return success


# =============================================================================
# 测试 7: 匹配协调器
# =============================================================================

async def test_coordinator():
    """测试匹配协调器"""
    print_header("测试 7: 匹配协调器")

    config = MatchConfig()
    coordinator = MatchCoordinator(
        config=config,
        bot_pool=BotPool(),
        honeypot_pool=HoneypotPool(),
    )

    # 测试 1: Bot 匹配应该立即成功
    try:
        # 清除队列中的残留
        await coordinator.queue.clear()
        
        # 多次尝试直到匹配到 Bot（因为概率分布）
        bot_matched = False
        for i in range(10):
            user_id = 300 + i
            try:
                result = await coordinator.match_user(
                    user_id=user_id,
                    websocket_ref=3000 + i,
                    user_score=100,
                )
                print(f"用户 {user_id} 匹配结果：type={result.opponent_type}")
                bot_matched = True
                break
            except RuntimeError as e:
                # 可能是真人匹配超时，继续尝试
                continue
        
        if bot_matched:
            print_result("匹配协调器", True)
            return True
        else:
            print_result("匹配协调器", False, "多次尝试仍未匹配成功")
            return False
            
    except Exception as e:
        print_result("匹配协调器", False, str(e))
        return False


# =============================================================================
# 主函数
# =============================================================================

async def main():
    """主函数"""
    print_header("匹配机制重构版测试")

    results = []

    # 同步测试
    results.append(("配置管理", test_config()))
    results.append(("概率决策算法", test_probability_algorithm()))
    results.append(("Bot 池加权随机", test_bot_pool()))
    results.append(("钓鱼 Bot 池", test_honeypot_pool()))

    # 异步测试
    results.append(("队列管理器", await test_queue_manager()))
    results.append(("结果管理器", await test_result_manager()))
    results.append(("匹配协调器", await test_coordinator()))

    # 汇总
    print_header("测试结果汇总")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！重构版匹配机制工作正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
