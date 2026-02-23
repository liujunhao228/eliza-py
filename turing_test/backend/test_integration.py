#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享 NLP 服务与 Bot 池集成测试

测试 SharedNLPService 和 AliceBotPool 的集成功能。
"""

import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

from alice.services.shared_nlp_service import SharedNLPService
from turing_test.backend.bot_pool import AliceBotPool, get_bot_pool, reset_bot_pool
from turing_test.backend.config_manager import ConfigManager


def test_shared_nlp_service():
    """测试共享 NLP 服务"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 1: 共享 NLP 服务")
    logger.info("=" * 60)

    # 获取单例实例
    nlp_service1 = SharedNLPService()
    nlp_service2 = SharedNLPService()

    # 验证单例模式
    assert nlp_service1 is nlp_service2, "单例模式失败"
    logger.info("✅ 单例模式验证通过")

    # 测试分词功能
    test_text = "我喜欢吃苹果"
    tokens = nlp_service1.tokenize(test_text)
    logger.info(f"分词测试：'{test_text}' -> {tokens}")
    assert len(tokens) > 0, "分词结果不应为空"
    logger.info("✅ 分词功能验证通过")

    # 测试缓存功能
    nlp_service1.set_cached_result("test_key", "test_value", ttl=60)
    cached_value = nlp_service1.get_cached_result("test_key")
    assert cached_value == "test_value", "缓存功能失败"
    logger.info("✅ 缓存功能验证通过")

    # 获取服务状态
    status = nlp_service1.get_stats()
    logger.info(f"NLP 服务状态：{status}")

    logger.info("✅ 共享 NLP 服务测试通过")


def test_bot_pool():
    """测试 Bot 池"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: Bot 池管理")
    logger.info("=" * 60)

    # 获取 NLP 服务
    nlp_service = SharedNLPService()

    # 获取项目根目录
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # 创建 Bot 池 (使用 demo_enhanced.yaml 和 mapping.yaml 因为格式兼容)
    bot_pool = AliceBotPool(
        nlp_service=nlp_service,
        min_instances=2,
        max_instances=5,
        idle_timeout=60,
        script_file=os.path.join(project_root, "alice", "scripts", "demo_enhanced.yaml"),
        rules_file=os.path.join(project_root, "alice", "scripts", "rules", "mapping.yaml"),
    )

    # 验证初始状态
    stats = bot_pool.get_stats()
    logger.info(f"Bot 池初始状态：{stats}")
    assert stats["total_bots"] == 2, f"初始 Bot 数量应为 2，实际为 {stats['total_bots']}"
    logger.info("✅ Bot 池初始化验证通过")

    # 测试获取和释放 Bot
    bot1 = bot_pool.acquire_bot()
    assert bot1 is not None, "获取 Bot 失败"
    logger.info("✅ 获取 Bot 实例成功")

    stats = bot_pool.get_stats()
    logger.info(f"获取 Bot 后状态：{stats}")
    assert stats["busy_bots"] == 1, "忙碌 Bot 数量应为 1"

    bot_pool.release_bot(bot1)
    stats = bot_pool.get_stats()
    logger.info(f"释放 Bot 后状态：{stats}")
    assert stats["busy_bots"] == 0, "忙碌 Bot 数量应为 0"
    logger.info("✅ Bot 获取和释放验证通过")

    # 测试并发获取
    def worker(worker_id: int):
        bot = bot_pool.acquire_bot()
        if bot:
            time.sleep(0.1)  # 模拟工作
            bot_pool.release_bot(bot)
            return True
        return False

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, i) for i in range(5)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results), "并发获取 Bot 失败"
    logger.info("✅ 并发获取 Bot 验证通过")

    # 关闭 Bot 池
    bot_pool.shutdown()
    logger.info("✅ Bot 池测试通过")


def test_concurrent_nlp_access():
    """测试并发访问 NLP 服务"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 并发 NLP 访问")
    logger.info("=" * 60)

    nlp_service = SharedNLPService()
    test_texts = [
        "我喜欢吃苹果",
        "张三在北京工作",
        "自然语言处理是人工智能的重要分支",
        "清华大学位于北京市海淀区",
        "李四和王五一起去上海旅游",
    ]

    results: List[dict] = []
    lock = threading.Lock()

    def worker(text: str):
        start_time = time.time()
        try:
            tokens = nlp_service.tokenize(text)
            elapsed = (time.time() - start_time) * 1000
            with lock:
                results.append({
                    "text": text,
                    "tokens": tokens,
                    "elapsed_ms": elapsed,
                    "success": True,
                })
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            with lock:
                results.append({
                    "text": text,
                    "error": str(e),
                    "elapsed_ms": elapsed,
                    "success": False,
                })

    # 并发执行
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(20):
            text = test_texts[i % len(test_texts)]
            futures.append(executor.submit(worker, text))

        for f in as_completed(futures):
            f.result()  # 等待所有任务完成

    # 统计结果
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    avg_elapsed = sum(r["elapsed_ms"] for r in results if r["success"]) / max(1, successful)

    logger.info(f"总请求数：{len(results)}")
    logger.info(f"成功/失败：{successful} / {failed}")
    logger.info(f"平均延迟：{avg_elapsed:.2f} ms")

    assert successful == len(results), "存在失败的请求"
    logger.info("✅ 并发 NLP 访问测试通过")


def test_cache_performance():
    """测试缓存性能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 缓存性能")
    logger.info("=" * 60)

    nlp_service = SharedNLPService()
    test_text = "缓存性能测试文本"

    # 清空缓存
    nlp_service.clear_cache()

    # 第一次访问（未命中）
    start1 = time.time()
    nlp_service.tokenize(test_text)
    time1 = (time.time() - start1) * 1000

    # 第二次访问（命中缓存）
    start2 = time.time()
    nlp_service.tokenize(test_text)
    time2 = (time.time() - start2) * 1000

    # 第三次访问（命中缓存）
    start3 = time.time()
    nlp_service.tokenize(test_text)
    time3 = (time.time() - start3) * 1000

    logger.info(f"第一次访问（未命中）: {time1:.2f} ms")
    logger.info(f"第二次访问（命中）: {time2:.2f} ms")
    logger.info(f"第三次访问（命中）: {time3:.2f} ms")

    if time1 > 0:
        speedup = time1 / max(time2, 0.001)
        logger.info(f"缓存加速比：{speedup:.2f}x")

    # 获取缓存统计
    cache_stats = nlp_service.get_stats()
    logger.info(f"缓存统计：{cache_stats}")

    logger.info("✅ 缓存性能测试通过")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("共享 NLP 服务与 Bot 池集成测试")
    logger.info("=" * 60)

    try:
        # 运行所有测试
        test_shared_nlp_service()
        test_bot_pool()
        test_concurrent_nlp_access()
        test_cache_performance()

        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有测试通过！")
        logger.info("=" * 60)

    except AssertionError as e:
        logger.error(f"❌ 测试失败：{e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 测试异常：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
