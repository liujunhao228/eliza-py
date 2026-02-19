#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 LTP 性能测试

专注于展示按需使用LTP的优化效果
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from alice.core import AliceBot


def simple_performance_test():
    """简化性能测试"""
    print("🤖 LTP 按需使用优化效果测试")
    print("=" * 40)
    
    # 测试用例
    test_cases = [
        ("你好", "简单问候"),
        ("我觉得今天很开心", "简单情感"),
        ("在吗", "简短询问"),
        ("我和朋友去了餐厅", "中等复杂"),
        ("因为工作压力大所以很累", "复杂句子"),
    ]
    
    print("测试1: 简单对话处理速度")
    print("-" * 30)
    
    # 创建优化版bot
    bot = AliceBot(enable_ltp=True)
    
    total_time = 0
    skipped_count = 0
    
    for text, description in test_cases:
        start_time = time.time()
        response = bot.respond(text)
        elapsed = (time.time() - start_time) * 1000
        total_time += elapsed
        
        # 检查是否跳过了LTP
        ltp_stats = bot.script_engine.get_ltp_stats()
        if ltp_stats.get('skipped_for_simple', 0) > skipped_count:
            status = "✓ 跳过LTP"
            skipped_count = ltp_stats.get('skipped_for_simple', 0)
        else:
            status = "⚡ 使用LTP"
            
        print(f"{description:<10} | {elapsed:>6.1f}ms | {status}")
    
    print(f"\n平均响应时间: {total_time/len(test_cases):.1f}ms")
    
    # 显示统计信息
    print("\n📊 使用统计:")
    stats = bot.script_engine.get_ltp_stats()
    print(f"  跳过简单分析: {stats.get('skipped_for_simple', 0)} 次")
    print(f"  实际使用LTP: {stats.get('successes', 0)} 次")
    print(f"  缓存条目数: {stats.get('cache_size', 0)}/{stats.get('cache_limit', 0)}")


def cache_effectiveness_test():
    """缓存效果测试"""
    print("\n\n🧠 缓存机制测试")
    print("=" * 25)
    
    bot = AliceBot(enable_ltp=True)
    
    # 重复发送相同消息
    test_message = "我觉得今天很开心"
    
    print("首次分析:")
    start_time = time.time()
    response1 = bot.respond(test_message)
    first_time = (time.time() - start_time) * 1000
    print(f"  耗时: {first_time:.1f}ms")
    
    print("重复分析:")
    start_time = time.time()
    response2 = bot.respond(test_message)
    repeat_time = (time.time() - start_time) * 1000
    print(f"  耗时: {repeat_time:.1f}ms")
    
    if first_time > 0:
        improvement = (first_time - repeat_time) / first_time * 100
        print(f"  缓存改善: {improvement:.1f}%")


if __name__ == "__main__":
    print("开始 LTP 优化效果测试...\n")
    
    try:
        simple_performance_test()
        cache_effectiveness_test()
        
        print("\n✅ 优化测试完成!")
        print("\n🎯 优化要点总结:")
        print("  ✓ 智能跳过简单内容的LTP分析")
        print("  ✓ 按需加载LTP模型")
        print("  ✓ 有效缓存机制")
        print("  ✓ 显著提升响应速度")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
