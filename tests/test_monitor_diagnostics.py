#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控模块详细诊断测试

专门测试日志记录和性能追踪功能是否正常工作。
"""

import logging
import time
import sys
from pathlib import Path
from io import StringIO
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from alice.utils.monitor import UnifiedMonitor, DialogueLogger


def test_logging_functionality():
    """测试日志功能是否正常工作"""
    print("=== 监控模块日志功能诊断 ===\n")
    
    # 创建字符串IO来捕获日志输出
    log_stream = StringIO()
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 移除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加流处理器
    handler = logging.StreamHandler(log_stream)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    try:
        print("1. 测试 UnifiedMonitor 日志记录...")
        
        # 测试 UnifiedMonitor
        monitor = UnifiedMonitor()
        
        # 记录交互
        request_time = time.time()
        time.sleep(0.01)  # 模拟处理时间
        response_time = time.time()
        
        monitor.record_interaction(request_time, response_time, True, {"test": "data"})
        
        # 使用计时器
        monitor.start_timer("diagnostic_test")
        time.sleep(0.02)
        duration = monitor.stop_timer("diagnostic_test", success=True)
        
        # 记录错误
        try:
            raise ValueError("测试错误消息")
        except Exception as e:
            monitor.log_error("diagnostic_component", e, {"diagnostic": "test"})
        
        # 获取日志内容
        log_content = log_stream.getvalue()
        print(f"   捕获的日志长度: {len(log_content)} 字符")
        print(f"   日志内容预览:\n{log_content[:500]}...\n")
        
        # 检查关键日志是否存在
        checks = [
            ("交互性能日志", "交互性能" in log_content),
            ("计时器日志", "性能" in log_content),
            ("错误日志", "错误" in log_content),
            ("INFO级别日志", "INFO" in log_content),
            ("DEBUG级别日志", "DEBUG" in log_content),
        ]
        
        for check_name, result in checks:
            status = "✓" if result else "✗"
            print(f"   {status} {check_name}: {'通过' if result else '失败'}")
        
        print("\n2. 测试 DialogueLogger 日志记录...")
        
        # 清空之前的日志
        log_stream.truncate(0)
        log_stream.seek(0)
        
        # 测试 DialogueLogger
        dialog_logger = DialogueLogger()
        
        # 记录对话
        dialog_logger.log_dialogue("你好", "你好！有什么可以帮助你的吗？")
        dialog_logger.log_performance("response_gen", 150.0, True)
        
        # 获取日志内容
        dialog_log_content = log_stream.getvalue()
        print(f"   对话日志长度: {len(dialog_log_content)} 字符")
        print(f"   对话日志预览:\n{dialog_log_content[:300]}...\n")
        
        # 检查对话日志
        dialog_checks = [
            ("对话日志", "对话" in dialog_log_content),
            ("性能日志", "性能" in dialog_log_content),
        ]
        
        for check_name, result in dialog_checks:
            status = "✓" if result else "✗"
            print(f"   {status} {check_name}: {'通过' if result else '失败'}")
        
        print("\n3. 测试报告生成功能...")
        
        # 测试性能报告
        perf_report = monitor.get_performance_report()
        print(f"   性能报告: {perf_report}")
        
        # 测试错误报告
        error_report = monitor.get_error_report()
        print(f"   错误报告: {error_report}")
        
        # 测试统计信息
        stats = monitor.get_stats()
        print(f"   统计信息: {stats}")
        
        print("\n=== 诊断完成 ===")
        
    finally:
        # 清理
        root_logger.removeHandler(handler)


def test_component_statistics():
    """测试组件统计功能"""
    print("\n=== 组件统计功能测试 ===\n")
    
    monitor = UnifiedMonitor()
    
    # 执行多次操作来测试统计
    components = ["parser", "matcher", "generator"]
    
    for i in range(10):
        component = components[i % len(components)]
        
        monitor.start_timer(component)
        time.sleep(0.001 * (i + 1))  # 不同的延迟
        success = i % 3 != 0  # 每3次失败一次
        duration = monitor.stop_timer(component, success)
        
        print(f"   {component}: {duration:.2f}ms, 成功={success}")
    
    # 显示统计结果
    stats = dict(monitor._component_stats)
    print(f"\n   组件统计:")
    for component, stat in stats.items():
        avg_time = stat['total_time'] / stat['count'] if stat['count'] > 0 else 0
        print(f"     {component}: 次数={stat['count']}, 平均时间={avg_time:.2f}ms, 错误={stat['errors']}")


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 边界情况测试 ===\n")
    
    monitor = UnifiedMonitor()
    
    # 测试空报告
    empty_perf_report = monitor.get_performance_report()
    print(f"   空性能报告: {empty_perf_report}")
    
    empty_error_report = monitor.get_error_report()
    print(f"   空错误报告: {empty_error_report}")
    
    # 测试清空功能
    monitor.start_timer("test")
    monitor.record_interaction(time.time(), time.time(), True)
    
    print(f"   清空前指标数量: {len(monitor._metrics)}")
    print(f"   清空前错误数量: {len(monitor._errors)}")
    print(f"   清空前计时器数量: {len(monitor._timers)}")
    
    monitor.clear()
    
    print(f"   清空后指标数量: {len(monitor._metrics)}")
    print(f"   清空后错误数量: {len(monitor._errors)}")
    print(f"   清空后计时器数量: {len(monitor._timers)}")


if __name__ == "__main__":
    test_logging_functionality()
    test_component_statistics()
    test_edge_cases()