#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享 NLP 服务压力测试

测试高并发场景下 NLP 服务的性能表现。
"""

import asyncio
import sys
import os
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from dataclasses import dataclass
import threading

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from turing_test.backend.services.nlp_service import get_nlp_service, reset_nlp_service
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)


@dataclass
class StressTestResult:
    """压力测试结果"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    cache_hit_rate: str


def run_single_request(nlp_service, text: str, operation: str) -> tuple[bool, float]:
    """
    执行单次请求

    Args:
        nlp_service: NLP 服务实例
        text: 测试文本
        operation: 操作类型 (segment, ner, pos, syntax)

    Returns:
        (是否成功，延迟毫秒数)
    """
    start_time = time.time()
    try:
        if operation == "segment":
            result = nlp_service.segment(text)
        elif operation == "ner":
            result = nlp_service.get_entities(text)
        elif operation == "pos":
            result = nlp_service.get_pos_tags(text)
        elif operation == "syntax":
            result = nlp_service.analyze_syntax(text)
        else:
            raise ValueError(f"未知操作：{operation}")

        elapsed_ms = (time.time() - start_time) * 1000
        return True, elapsed_ms
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(f"请求失败：{e}")
        return False, elapsed_ms


def stress_test_threaded(
    num_threads: int,
    requests_per_thread: int,
    test_texts: List[str],
    operations: List[str],
) -> StressTestResult:
    """
    多线程压力测试

    Args:
        num_threads: 线程数
        requests_per_thread: 每个线程的请求数
        test_texts: 测试文本列表
        operations: 操作类型列表

    Returns:
        压力测试结果
    """
    logger.info(f"开始多线程压力测试：{num_threads} 线程 x {requests_per_thread} 请求")

    nlp_service = get_nlp_service()
    latencies: List[float] = []
    successful = 0
    failed = 0

    def worker(thread_id: int):
        nonlocal successful, failed
        results = []
        for i in range(requests_per_thread):
            text = test_texts[i % len(test_texts)]
            operation = operations[i % len(operations)]
            success, latency = run_single_request(nlp_service, text, operation)
            results.append((success, latency))
        return results

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for future in as_completed(futures):
            results = future.result()
            for success, latency in results:
                latencies.append(latency)
                if success:
                    successful += 1
                else:
                    failed += 1

    total_time = time.time() - start_time

    # 计算统计信息
    return calculate_stats(successful, failed, latencies, total_time, nlp_service)


async def stress_test_async(
    num_concurrent: int,
    total_requests: int,
    test_texts: List[str],
    operations: List[str],
) -> StressTestResult:
    """
    异步压力测试

    Args:
        num_concurrent: 并发数
        total_requests: 总请求数
        test_texts: 测试文本列表
        operations: 操作类型列表

    Returns:
        压力测试结果
    """
    logger.info(f"开始异步压力测试：并发 {num_concurrent} x 总请求 {total_requests}")

    nlp_service = get_nlp_service()
    latencies: List[float] = []
    successful = 0
    failed = 0
    lock = threading.Lock()

    def run_request(text: str, operation: str):
        nonlocal successful, failed
        success, latency = run_single_request(nlp_service, text, operation)
        with lock:
            latencies.append(latency)
            if success:
                successful += 1
            else:
                failed += 1

    async def worker():
        loop = asyncio.get_event_loop()
        for i in range(total_requests // num_concurrent):
            text = test_texts[i % len(test_texts)]
            operation = operations[i % len(operations)]
            await loop.run_in_executor(None, run_request, text, operation)

    start_time = time.time()

    tasks = [asyncio.create_task(worker()) for _ in range(num_concurrent)]
    await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    return calculate_stats(successful, failed, latencies, total_time, nlp_service)


def calculate_stats(
    successful: int,
    failed: int,
    latencies: List[float],
    total_time: float,
    nlp_service,
) -> StressTestResult:
    """计算统计信息"""
    total_requests = successful + failed

    if not latencies:
        return StressTestResult(
            total_requests=total_requests,
            successful_requests=0,
            failed_requests=0,
            total_time_seconds=0,
            avg_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            median_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            requests_per_second=0,
            cache_hit_rate="0%",
        )

    sorted_latencies = sorted(latencies)
    avg_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 0 else 0
    p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 0 else 0
    rps = total_requests / total_time if total_time > 0 else 0

    cache_stats = nlp_service.get_cache_stats()

    return StressTestResult(
        total_requests=total_requests,
        successful_requests=successful,
        failed_requests=failed,
        total_time_seconds=total_time,
        avg_latency_ms=avg_latency,
        min_latency_ms=min_latency,
        max_latency_ms=max_latency,
        median_latency_ms=median_latency,
        p95_latency_ms=p95_latency,
        p99_latency_ms=p99_latency,
        requests_per_second=rps,
        cache_hit_rate=cache_stats["hit_rate"],
    )


def print_results(result: StressTestResult, test_name: str):
    """打印测试结果"""
    logger.info(f"\n{'='*60}")
    logger.info(f"测试结果：{test_name}")
    logger.info(f"{'='*60}")
    logger.info(f"总请求数：{result.total_requests}")
    logger.info(f"成功/失败：{result.successful_requests} / {result.failed_requests}")
    logger.info(f"总耗时：{result.total_time_seconds:.2f} 秒")
    logger.info(f"请求/秒：{result.requests_per_second:.2f}")
    logger.info(f"\n延迟统计:")
    logger.info(f"  平均延迟：{result.avg_latency_ms:.2f} ms")
    logger.info(f"  最小延迟：{result.min_latency_ms:.2f} ms")
    logger.info(f"  最大延迟：{result.max_latency_ms:.2f} ms")
    logger.info(f"  中位数延迟：{result.median_latency_ms:.2f} ms")
    logger.info(f"  P95 延迟：{result.p95_latency_ms:.2f} ms")
    logger.info(f"  P99 延迟：{result.p99_latency_ms:.2f} ms")
    logger.info(f"\n缓存命中率：{result.cache_hit_rate}")
    logger.info(f"{'='*60}\n")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("共享 NLP 服务压力测试")
    logger.info("=" * 60)

    # 初始化 NLP 服务
    logger.info("\n初始化 NLP 服务...")
    nlp_service = get_nlp_service()
    status = nlp_service.get_status()
    logger.info(f"NLP 服务状态：{status}")

    # 测试文本
    test_texts = [
        "我喜欢吃苹果",
        "张三在北京工作",
        "自然语言处理是人工智能的重要分支",
        "清华大学位于北京市海淀区",
        "李四和王五一起去上海旅游",
        "深度学习在图像识别领域取得了巨大成功",
        "Python 是一种广泛使用的高级编程语言",
        "机器学习算法可以从数据中自动学习规律",
    ]

    operations = ["segment", "ner", "pos", "syntax"]

    # 测试场景 1: 低并发 (5 线程)
    logger.info("\n" + "=" * 60)
    logger.info("场景 1: 低并发测试 (5 线程 x 20 请求)")
    logger.info("=" * 60)
    result1 = stress_test_threaded(
        num_threads=5,
        requests_per_thread=20,
        test_texts=test_texts,
        operations=operations,
    )
    print_results(result1, "低并发测试 (5 线程)")

    # 测试场景 2: 中并发 (20 线程)
    logger.info("\n" + "=" * 60)
    logger.info("场景 2: 中并发测试 (20 线程 x 50 请求)")
    logger.info("=" * 60)
    result2 = stress_test_threaded(
        num_threads=20,
        requests_per_thread=50,
        test_texts=test_texts,
        operations=operations,
    )
    print_results(result2, "中并发测试 (20 线程)")

    # 测试场景 3: 高并发 (50 线程)
    logger.info("\n" + "=" * 60)
    logger.info("场景 3: 高并发测试 (50 线程 x 100 请求)")
    logger.info("=" * 60)
    result3 = stress_test_threaded(
        num_threads=50,
        requests_per_thread=100,
        test_texts=test_texts,
        operations=operations,
    )
    print_results(result3, "高并发测试 (50 线程)")

    # 测试场景 4: 异步并发
    logger.info("\n" + "=" * 60)
    logger.info("场景 4: 异步并发测试 (并发 30 x 总请求 500)")
    logger.info("=" * 60)
    result4 = asyncio.run(
        stress_test_async(
            num_concurrent=30,
            total_requests=500,
            test_texts=test_texts,
            operations=operations,
        )
    )
    print_results(result4, "异步并发测试")

    # 最终缓存统计
    logger.info("\n" + "=" * 60)
    logger.info("最终缓存统计")
    logger.info("=" * 60)
    final_cache_stats = nlp_service.get_cache_stats()
    logger.info(f"缓存统计：{final_cache_stats}")

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("压力测试总结")
    logger.info("=" * 60)
    logger.info(f"✅ 所有测试场景已完成")
    logger.info(f"📊 最终缓存命中率：{final_cache_stats['hit_rate']}")
    logger.info(f"🚀 最高吞吐：{max(result1.requests_per_second, result2.requests_per_second, result3.requests_per_second, result4.requests_per_second):.2f} 请求/秒")
    logger.info(f"⏱️  P99 延迟 (高并发): {result3.p99_latency_ms:.2f} ms")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
