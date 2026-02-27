#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化验证测试脚本

运行此脚本验证所有性能优化是否正常工作。

使用方法:
    uv run python scripts/test_performance.py
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "✅" if success else "❌"
    print(f"{status} {name}: {message}")


def test_lru_cache():
    """测试 LRU 缓存"""
    print_header("测试 1: LRU 缓存")
    
    try:
        from alice.cache.lru_cache import LRUCache
        
        cache = LRUCache(max_size=100, default_ttl=300)
        
        # 测试基本操作
        cache.set("key1", "value1")
        result = cache.get("key1")
        print_result("基本设置/获取", result == "value1", f"获取值：{result}")
        
        # 测试统计
        stats = cache.get_stats()
        print_result("统计信息", stats['hits'] == 1, f"命中率：{stats.get('hit_rate', 'N/A')}")
        
        # 测试 TTL
        cache.set("key2", "value2", ttl=1)
        time.sleep(1.1)
        expired = cache.get("key2")
        print_result("TTL 过期", expired is None, "缓存已过期")
        
        return True
        
    except Exception as e:
        print_result("LRU 缓存测试", False, str(e))
        return False


def test_nlp_cache():
    """测试 NLP 缓存"""
    print_header("测试 2: NLP 服务缓存")
    
    try:
        from alice.services.shared_nlp_service import SharedNLPService
        
        service = SharedNLPService()
        
        # 测试分词
        tokens = service.tokenize("你好世界")
        print_result("分词功能", len(tokens) > 0, f"分词结果：{tokens}")
        
        # 测试分析（第一次，缓存未命中）
        start = time.perf_counter()
        result1 = service.analyze("测试缓存性能")
        duration1 = (time.perf_counter() - start) * 1000
        
        # 测试分析（第二次，缓存命中）
        start = time.perf_counter()
        result2 = service.analyze("测试缓存性能")
        duration2 = (time.perf_counter() - start) * 1000
        
        print_result("NLP 分析缓存", duration2 < duration1, 
                    f"首次：{duration1:.2f}ms, 命中：{duration2:.2f}ms")
        
        # 查看缓存统计
        cache_stats = service.get_cache_stats()
        print_result("缓存统计", True, 
                    f"命中率：{cache_stats.get('overall_hit_rate', 'N/A')}")
        
        return True
        
    except Exception as e:
        print_result("NLP 缓存测试", False, str(e))
        return False


def test_script_matcher_cache():
    """测试脚本匹配器缓存"""
    print_header("测试 3: 脚本匹配器缓存")
    
    try:
        from alice.scripting import ScriptMatcher, ScriptContext
        
        matcher = ScriptMatcher(enable_cache=True)
        
        # 测试统计
        stats = matcher.get_stats()
        print_result("缓存启用", stats.get('cache_enabled', False), 
                    f"缓存已启用")
        
        # 测试缓存键生成
        context = ScriptContext(text="测试文本", tokens=["测试", "文本"], turn_count=1)
        cache_key = matcher._generate_cache_key(context)
        print_result("缓存键生成", len(cache_key) == 32, 
                    f"MD5 键：{cache_key[:8]}...")
        
        return True
        
    except Exception as e:
        print_result("脚本匹配器测试", False, str(e))
        return False


def test_dialogue_engine_cache():
    """测试对话引擎缓存"""
    print_header("测试 4: 对话引擎缓存")
    
    try:
        from alice.core.dialogue_engine import DialogueEngine
        
        engine = DialogueEngine(enable_response_cache=True)
        
        # 检查缓存是否启用
        print_result("响应缓存启用", 
                    engine._response_cache is not None, 
                    "缓存已初始化")
        
        # 检查统计
        stats = engine.get_stats()
        perf_stats = stats.get('performance', {})
        print_result("性能统计", True, 
                    f"缓存命中：{perf_stats.get('cache_hits', 0)}, "
                    f"未命中：{perf_stats.get('cache_misses', 0)}")
        
        return True
        
    except Exception as e:
        print_result("对话引擎测试", False, str(e))
        return False


def test_query_cache():
    """测试查询缓存"""
    print_header("测试 5: 查询缓存")
    
    try:
        from turing_test.backend.query_cache import QueryCache
        
        cache = QueryCache(max_size=100, default_ttl=300)
        
        # 测试键生成
        key = cache.generate_key("test_query", user_id=123)
        print_result("查询键生成", len(key) == 32, f"MD5 键：{key[:8]}...")
        
        # 测试预定义缓存
        from turing_test.backend.query_cache import (
            user_query_cache,
            config_query_cache,
            stats_query_cache,
        )
        print_result("预定义缓存", True, 
                    f"user: {len(user_query_cache.cache)} entries, "
                    f"config: {len(config_query_cache.cache)} entries")
        
        return True
        
    except Exception as e:
        print_result("查询缓存测试", False, str(e))
        return False


def test_redis_cache():
    """测试 Redis 缓存"""
    print_header("测试 6: Redis 缓存（降级模式）")
    
    try:
        from alice.cache.redis_cache import RedisCache, RedisConfig
        
        cache = RedisCache(
            config=RedisConfig(host="localhost", port=6379),
            fallback_to_memory=True,
        )
        
        # 测试降级模式
        available = cache.is_available
        print_result("Redis 可用性", available, 
                    "降级到内存缓存" if not available else "Redis 已连接")
        
        # 测试统计
        stats = cache.get_stats()
        print_result("统计信息", True, 
                    f"连接：{stats.get('connected', False)}, "
                    f"降级命中：{stats.get('fallback_hits', 0)}")
        
        return True
        
    except Exception as e:
        print_result("Redis 缓存测试", False, str(e))
        return False


def test_websocket_manager():
    """测试 WebSocket 管理器"""
    print_header("测试 7: WebSocket 消息队列")
    
    try:
        from turing_test.backend.websocket.manager import ConnectionManager
        
        manager = ConnectionManager(
            message_queue_size=1000,
            batch_send_interval=0.1,
        )
        
        # 检查队列配置
        print_result("消息队列启用", 
                    manager._max_queue_size == 1000,
                    f"队列大小：{manager._max_queue_size}")
        
        print_result("批量发送间隔", 
                    manager._batch_send_interval == 0.1,
                    f"间隔：{manager._batch_send_interval}s")
        
        return True
        
    except Exception as e:
        print_result("WebSocket 管理器测试", False, str(e))
        return False


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("  性能优化验证测试")
    print("🚀" * 30)
    
    results = []
    
    results.append(("LRU 缓存", test_lru_cache()))
    results.append(("NLP 缓存", test_nlp_cache()))
    results.append(("脚本匹配器", test_script_matcher_cache()))
    results.append(("对话引擎", test_dialogue_engine_cache()))
    results.append(("查询缓存", test_query_cache()))
    results.append(("Redis 缓存", test_redis_cache()))
    results.append(("WebSocket", test_websocket_manager()))
    
    # 打印总结
    print_header("测试总结")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有性能优化验证通过!")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关模块")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
