#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 性能优化测试脚本

用于验证按需使用 LTP 功能的性能改善效果
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from alice.core import AliceBot


def performance_comparison_test():
    """性能对比测试"""
    print("🤖 LTP 性能优化测试")
    print("=" * 50)
    
    # 测试用例
    test_cases = [
        ("你好", "简单问候"),
        ("我觉得今天很开心", "简单情感表达"),
        ("我和朋友去了餐厅，那里的食物很美味", "中等复杂度句子"),
        ("因为工作压力太大，所以我最近总是感到焦虑和疲惫，希望能找到更好的平衡", "高复杂度句子"),
        ("你认为人工智能会取代人类工作吗？这是一个值得深思的问题", "复杂疑问句"),
    ]
    
    # 创建两个bot实例进行对比
    print("正在初始化测试环境...")
    
    # 普通模式（不使用LTP）
    bot_normal = AliceBot(enable_ltp=False)
    
    # 优化模式（按需使用LTP）
    bot_optimized = AliceBot(enable_ltp=True)
    
    print("开始性能测试...\n")
    print(f"{'测试内容':<20} {'普通模式(ms)':<15} {'优化模式(ms)':<15} {'改善率':<10}")
    print("-" * 70)
    
    total_normal_time = 0
    total_optimized_time = 0
    
    for text, description in test_cases:
        # 测试普通模式
        start_time = time.time()
        try:
            response1 = bot_normal.respond(text)
            normal_time = (time.time() - start_time) * 1000
        except Exception as e:
            normal_time = -1
            response1 = f"错误: {e}"
        
        # 测试优化模式
        start_time = time.time()
        try:
            response2 = bot_optimized.respond(text)
            optimized_time = (time.time() - start_time) * 1000
        except Exception as e:
            optimized_time = -1
            response2 = f"错误: {e}"
        
        # 计算改善率
        if normal_time > 0 and optimized_time > 0:
            improvement = (normal_time - optimized_time) / normal_time * 100
            improvement_str = f"{improvement:.1f}%"
            total_normal_time += normal_time
            total_optimized_time += optimized_time
        else:
            improvement_str = "N/A"
            normal_time = "ERROR" if normal_time == -1 else f"{normal_time:.2f}"
            optimized_time = "ERROR" if optimized_time == -1 else f"{optimized_time:.2f}"
        
        print(f"{description:<20} {normal_time:<15} {optimized_time:<15} {improvement_str:<10}")
    
    print("-" * 70)
    
    # 总体统计
    if total_normal_time > 0 and total_optimized_time > 0:
        overall_improvement = (total_normal_time - total_optimized_time) / total_normal_time * 100
        print(f"{'总体平均':<20} {total_normal_time/len(test_cases):<15.2f} {total_optimized_time/len(test_cases):<15.2f} {overall_improvement:.1f}%")
    
    # 显示LTP使用统计
    print("\n📊 LTP 使用统计:")
    ltp_stats = bot_optimized.script_engine.get_ltp_stats()
    print(f"  LTP 初始化尝试次数: {ltp_stats.get('attempts', 0)}")
    print(f"  LTP 成功使用次数: {ltp_stats.get('successes', 0)}")
    print(f"  LTP 失败次数: {ltp_stats.get('failures', 0)}")
    print(f"  因简单内容跳过的次数: {ltp_stats.get('skipped_for_simple', 0)}")
    print(f"  降级到简化模式次数: {ltp_stats.get('fallback_to_simple', 0)}")
    print(f"  当前缓存大小: {ltp_stats.get('cache_size', 0)}/{ltp_stats.get('cache_limit', 0)}")


def stress_test():
    """压力测试"""
    print("\n💪 压力测试")
    print("=" * 30)
    
    bot = AliceBot(enable_ltp=True)
    
    # 大量简单对话
    simple_messages = ["你好", "在吗", "再见", "谢谢", "好的"] * 20
    
    start_time = time.time()
    for i, msg in enumerate(simple_messages):
        try:
            response = bot.respond(msg)
        except Exception as e:
            print(f"第{i+1}条消息处理失败: {e}")
    
    total_time = time.time() - start_time
    avg_time = total_time / len(simple_messages) * 1000
    
    print(f"处理 {len(simple_messages)} 条简单消息")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"平均每条: {avg_time:.2f} 毫秒")
    
    # 显示最终统计
    stats = bot.script_engine.get_ltp_stats()
    print(f"LTP实际使用次数: {stats.get('successes', 0)}")
    print(f"因简单内容跳过: {stats.get('skipped_for_simple', 0)}")


def memory_usage_test():
    """内存使用测试"""
    print("\n💾 内存使用测试")
    print("=" * 20)
    
    import psutil
    import gc
    
    # 获取初始内存使用
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"初始内存使用: {initial_memory:.2f} MB")
    
    # 创建多个bot实例
    bots = []
    for i in range(5):
        bot = AliceBot(enable_ltp=True)
        bots.append(bot)
        current_memory = process.memory_info().rss / 1024 / 1024
        print(f"创建第{i+1}个实例后: {current_memory:.2f} MB (+{(current_memory-initial_memory):.2f} MB)")
    
    # 强制垃圾回收
    gc.collect()
    final_memory = process.memory_info().rss / 1024 / 1024
    print(f"垃圾回收后: {final_memory:.2f} MB")
    
    print(f"总内存增长: {final_memory - initial_memory:.2f} MB")
    print(f"平均每个实例: {(final_memory - initial_memory) / 5:.2f} MB")


if __name__ == "__main__":
    print("开始 LTP 性能测试...\n")
    
    try:
        performance_comparison_test()
        stress_test()
        memory_usage_test()
        
        print("\n✅ 所有测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
