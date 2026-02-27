#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试

测试 Alice 对话系统的性能指标：
- 响应时间
- 缓存命中率
- 并发性能
- NLP 分析性能
- 脚本匹配性能

使用方法:
    pytest tests/performance/test_benchmark.py -v
    pytest tests/performance/test_benchmark.py::test_response_time -v
    pytest tests/performance/test_benchmark.py -v --tb=short
"""

import pytest
import time
import asyncio
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = str(Path(__file__).resolve().parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# =============================================================================
# 测试数据
# =============================================================================

TEST_INPUTS = [
    "你好",
    "你是谁？",
    "今天天气怎么样？",
    "你喜欢吃什么？",
    "你有什么爱好？",
    "能讲个笑话吗？",
    "再见",
    "谢谢",
    "对不起",
    "我不知道",
]

LONG_INPUTS = [
    "我今天去了公园，看到了很多漂亮的花，有红色的玫瑰，有黄色的郁金香，还有紫色的薰衣草，真是美不胜收啊！",
    "最近在看一本科幻小说，叫做《三体》，是刘慈欣写的，讲述了地球文明和三体文明之间的故事，非常精彩，推荐你也看看。",
    "我觉得人工智能是一个非常有前景的领域，它可以改变我们的生活方式，提高工作效率，解决一些复杂的问题，比如医疗诊断、自动驾驶等。",
]


# =============================================================================
# 性能测试工具类
# =============================================================================

class PerformanceTester:
    """性能测试器"""

    def __init__(self):
        self.results: Dict[str, List[float]] = {}

    def record(self, test_name: str, duration_ms: float):
        """记录测试结果"""
        if test_name not in self.results:
            self.results[test_name] = []
        self.results[test_name].append(duration_ms)

    def get_stats(self, test_name: str) -> Dict[str, float]:
        """获取统计信息"""
        if test_name not in self.results or not self.results[test_name]:
            return {}

        data = self.results[test_name]
        return {
            'count': len(data),
            'avg_ms': statistics.mean(data),
            'min_ms': min(data),
            'max_ms': max(data),
            'median_ms': statistics.median(data),
            'p95_ms': sorted(data)[int(len(data) * 0.95)] if len(data) > 1 else data[0],
            'p99_ms': sorted(data)[int(len(data) * 0.99)] if len(data) > 1 else data[0],
            'std_dev_ms': statistics.stdev(data) if len(data) > 1 else 0,
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """获取所有测试的统计信息"""
        return {name: self.get_stats(name) for name in self.results}

    def print_report(self):
        """打印性能报告"""
        print("\n" + "=" * 80)
        print("性能测试报告")
        print("=" * 80)

        for name, stats in self.get_all_stats().items():
            print(f"\n{name}:")
            print(f"  测试次数：{stats['count']}")
            print(f"  平均：{stats['avg_ms']:.2f}ms")
            print(f"  最小：{stats['min_ms']:.2f}ms")
            print(f"  最大：{stats['max_ms']:.2f}ms")
            print(f"  中位数：{stats['median_ms']:.2f}ms")
            print(f"  P95: {stats['p95_ms']:.2f}ms")
            print(f"  P99: {stats['p99_ms']:.2f}ms")
            print(f"  标准差：{stats['std_dev_ms']:.2f}ms")

        print("\n" + "=" * 80)


# 全局测试器实例
tester = PerformanceTester()


# =============================================================================
# 导入被测模块
# =============================================================================

@pytest.fixture(scope="module")
def dialogue_engine():
    """创建对话引擎实例"""
    from alice.core.dialogue_engine import DialogueEngine

    engine = DialogueEngine(enable_response_cache=True)
    engine.initialize()
    yield engine
    engine.cleanup()


@pytest.fixture(scope="module")
def nlp_service():
    """创建 NLP 服务实例"""
    from alice.services.shared_nlp_service import SharedNLPService

    service = SharedNLPService()
    service.initialize_ltp(enable_ltp=False)  # 仅使用 jieba
    yield service


# =============================================================================
# 响应时间测试
# =============================================================================

class TestResponseTime:
    """响应时间测试"""

    def test_short_input_response_time(self, dialogue_engine):
        """测试短输入响应时间"""
        durations = []

        for input_text in TEST_INPUTS[:5]:
            start = time.perf_counter()
            response, _ = dialogue_engine.respond(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)
            tester.record("short_input_response", duration)

            assert response is not None
            assert len(response) > 0

        stats = tester.get_stats("short_input_response")
        print(f"\n短输入响应时间：avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")

    def test_long_input_response_time(self, dialogue_engine):
        """测试长输入响应时间"""
        durations = []

        for input_text in LONG_INPUTS:
            start = time.perf_counter()
            response, _ = dialogue_engine.respond(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)
            tester.record("long_input_response", duration)

            assert response is not None
            assert len(response) > 0

        stats = tester.get_stats("long_input_response")
        print(f"\n长输入响应时间：avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")

    def test_repeated_input_cache_hit(self, dialogue_engine):
        """测试重复输入的缓存命中"""
        input_text = "你好"
        durations = []

        # 第一次（缓存未命中）
        start = time.perf_counter()
        dialogue_engine.respond(input_text)
        duration1 = (time.perf_counter() - start) * 1000

        # 后续（缓存命中）
        for _ in range(10):
            start = time.perf_counter()
            response, _ = dialogue_engine.respond(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)
            tester.record("cache_hit_response", duration)

        stats = tester.get_stats("cache_hit_response")
        print(f"\n缓存命中响应时间：avg={stats['avg_ms']:.2f}ms (vs 首次：{duration1:.2f}ms)")

        # 缓存命中应该比首次快
        assert stats['avg_ms'] < duration1 * 0.5, "缓存命中应该显著快于首次请求"


# =============================================================================
# NLP 性能测试
# =============================================================================

class TestNLPPerformance:
    """NLP 性能测试"""

    def test_tokenization_performance(self, nlp_service):
        """测试分词性能"""
        durations = []

        for input_text in TEST_INPUTS + LONG_INPUTS:
            start = time.perf_counter()
            tokens = nlp_service.tokenize(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)
            tester.record("tokenization", duration)

            assert tokens is not None
            assert len(tokens) > 0

        stats = tester.get_stats("tokenization")
        print(f"\n分词性能：avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")

    def test_analysis_performance(self, nlp_service):
        """测试分析性能"""
        durations = []

        for input_text in TEST_INPUTS:
            start = time.perf_counter()
            result = nlp_service.analyze(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)
            tester.record("nlp_analysis", duration)

            assert result is not None

        stats = tester.get_stats("nlp_analysis")
        print(f"\nNLP 分析性能：avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")

    def test_nlp_cache_performance(self, nlp_service):
        """测试 NLP 缓存性能"""
        input_text = "测试缓存性能"

        # 第一次（缓存未命中）
        start = time.perf_counter()
        nlp_service.analyze(input_text)
        duration1 = (time.perf_counter() - start) * 1000

        # 后续（缓存命中）
        durations = []
        for _ in range(10):
            start = time.perf_counter()
            nlp_service.analyze(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)
            tester.record("nlp_cache_hit", duration)

        stats = tester.get_stats("nlp_cache_hit")
        cache_stats = nlp_service.get_cache_stats()

        print(f"\nNLP 缓存命中响应时间：avg={stats['avg_ms']:.2f}ms (vs 首次：{duration1:.2f}ms)")
        print(f"NLP 缓存命中率：{cache_stats.get('overall_hit_rate', 'N/A')}")


# =============================================================================
# 并发性能测试
# =============================================================================

class TestConcurrency:
    """并发性能测试"""

    def test_concurrent_requests(self, dialogue_engine):
        """测试并发请求"""
        async def make_request(engine, input_text: str) -> float:
            start = time.perf_counter()
            engine.respond(input_text)
            return (time.perf_counter() - start) * 1000

        async def run_concurrent():
            tasks = [
                make_request(dialogue_engine, input_text)
                for input_text in TEST_INPUTS * 2
            ]
            return await asyncio.gather(*tasks)

        # 运行并发测试
        durations = asyncio.run(run_concurrent())
        for duration in durations:
            tester.record("concurrent_requests", duration)

        stats = tester.get_stats("concurrent_requests")
        print(f"\n并发请求响应时间：avg={stats['avg_ms']:.2f}ms, count={stats['count']}")

    def test_thread_pool_performance(self, dialogue_engine):
        """测试线程池性能"""
        def make_request(input_text: str) -> float:
            start = time.perf_counter()
            dialogue_engine.respond(input_text)
            return (time.perf_counter() - start) * 1000

        # 使用线程池
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(make_request, input_text)
                for input_text in TEST_INPUTS * 2
            ]
            durations = [f.result() for f in futures]

        for duration in durations:
            tester.record("thread_pool_requests", duration)

        stats = tester.get_stats("thread_pool_requests")
        print(f"\n线程池请求响应时间：avg={stats['avg_ms']:.2f}ms, count={stats['count']}")


# =============================================================================
# 缓存性能测试
# =============================================================================

class TestCachePerformance:
    """缓存性能测试"""

    def test_cache_hit_rate(self, dialogue_engine):
        """测试缓存命中率"""
        # 使用固定输入集
        test_inputs = TEST_INPUTS * 5

        hits = 0
        misses = 0

        for input_text in test_inputs:
            # 响应会内部更新统计
            dialogue_engine.respond(input_text)

        stats = dialogue_engine.get_stats()
        perf_stats = stats.get('performance', {})

        cache_hits = perf_stats.get('cache_hits', 0)
        cache_misses = perf_stats.get('cache_misses', 0)
        total = cache_hits + cache_misses

        if total > 0:
            hit_rate = cache_hits / total * 100
            print(f"\n缓存命中率：{hit_rate:.2f}% ({cache_hits}/{total})")
            assert hit_rate > 20, f"缓存命中率应该大于 20%，实际：{hit_rate:.2f}%"


# =============================================================================
# 压力测试
# =============================================================================

class TestStress:
    """压力测试"""

    def test_high_load(self, dialogue_engine):
        """高负载测试"""
        iterations = 50
        durations = []

        for i in range(iterations):
            input_text = TEST_INPUTS[i % len(TEST_INPUTS)]
            start = time.perf_counter()
            dialogue_engine.respond(input_text)
            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)

        stats = tester.get_stats("high_load")
        # 手动添加到统计
        for d in durations:
            tester.record("high_load", d)

        stats = tester.get_stats("high_load")
        print(f"\n高负载测试 ({iterations}次): avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")

        # 平均响应时间应该小于 100ms
        assert stats['avg_ms'] < 100, f"平均响应时间应该小于 100ms，实际：{stats['avg_ms']:.2f}ms"


# =============================================================================
# 测试完成报告
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def print_report():
    """测试完成后打印报告"""
    yield
    tester.print_report()


# =============================================================================
# 命令行运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
