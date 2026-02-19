#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具
提供响应时间监控、性能分析和日志记录功能
"""

import time
import functools
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import json


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error_message': self.error_message
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_records: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_records: 最大记录数量
        """
        self.metrics = deque(maxlen=max_records)
        self.start_times: Dict[str, datetime] = {}
        
    def start_timer(self, name: str):
        """
        开始计时
        
        Args:
            name: 计时器名称
        """
        self.start_times[name] = datetime.now()
    
    def stop_timer(self, name: str, success: bool = True, error_message: str = "") -> Optional[float]:
        """
        停止计时并记录
        
        Args:
            name: 计时器名称
            success: 是否成功
            error_message: 错误信息
            
        Returns:
            耗时（毫秒）
        """
        if name not in self.start_times:
            return None
        
        end_time = datetime.now()
        duration = (end_time - self.start_times[name]).total_seconds() * 1000
        
        metric = PerformanceMetric(
            name=name,
            duration_ms=duration,
            success=success,
            error_message=error_message
        )
        self.metrics.append(metric)
        del self.start_times[name]
        
        return duration
    
    def get_statistics(self, name: Optional[str] = None, last_n: int = 100) -> Dict:
        """
        获取统计数据
        
        Args:
            name: 指标名称（None 表示所有）
            last_n: 统计最近 n 条记录
            
        Returns:
            统计字典
        """
        metrics = list(self.metrics)
        
        if name:
            metrics = [m for m in metrics if m.name == name]
        
        metrics = metrics[-last_n:]
        
        if not metrics:
            return {
                'count': 0,
                'avg_ms': 0,
                'min_ms': 0,
                'max_ms': 0,
                'success_rate': 0
            }
        
        durations = [m.duration_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)
        
        return {
            'count': len(metrics),
            'avg_ms': sum(durations) / len(durations),
            'min_ms': min(durations),
            'max_ms': max(durations),
            'success_rate': success_count / len(metrics) * 100,
            'p50_ms': sorted(durations)[len(durations) // 2],
            'p95_ms': sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
            'p99_ms': sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0]
        }
    
    def get_all_metrics(self, last_n: int = 100) -> List[Dict]:
        """
        获取所有指标
        
        Args:
            last_n: 返回最近 n 条
            
        Returns:
            指标列表
        """
        return [m.to_dict() for m in list(self.metrics)[-last_n:]]
    
    def reset(self):
        """重置所有记录"""
        self.metrics.clear()
        self.start_times.clear()
    
    def export_json(self, last_n: int = 100) -> str:
        """
        导出为 JSON
        
        Args:
            last_n: 导出最近 n 条
            
        Returns:
            JSON 字符串
        """
        data = {
            'exported_at': datetime.now().isoformat(),
            'statistics': self.get_statistics(last_n=last_n),
            'metrics': self.get_all_metrics(last_n=last_n)
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


def timed(name: str):
    """
    性能监控装饰器
    
    Usage:
        @timed("my_function")
        def my_function():
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = kwargs.get('monitor', None)
            
            # 如果没有传入 monitor，使用全局默认
            if monitor is None:
                monitor = global_monitor
            
            monitor.start_timer(name)
            try:
                result = func(*args, **kwargs)
                monitor.stop_timer(name, success=True)
                return result
            except Exception as e:
                monitor.stop_timer(name, success=False, error_message=str(e))
                raise
        return wrapper
    return decorator


# 全局性能监控器
global_monitor = PerformanceMonitor()


class ResponseTimeLogger:
    """响应时间日志器"""
    
    def __init__(self, alice_bot, log_file: str = "alice_performance.log"):
        """
        初始化日志器
        
        Args:
            alice_bot: AliceBot 实例
            log_file: 日志文件路径
        """
        self.alice = alice_bot
        self.log_file = log_file
        self.monitor = PerformanceMonitor()
        self.request_count = 0
        
    def respond(self, user_input: str) -> str:
        """
        带性能监控的响应方法
        
        Args:
            user_input: 用户输入
            
        Returns:
            机器人回复
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            response = self.alice.respond(user_input)
            duration = (time.time() - start_time) * 1000
            
            self.monitor.stop_timer(f"request_{self.request_count}", success=True)
            self._log(user_input, response, duration, success=True)
            
            return response
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.monitor.stop_timer(f"request_{self.request_count}", success=False, error_message=str(e))
            self._log(user_input, "", duration, success=False, error=str(e))
            raise
    
    def _log(self, user_input: str, response: str, duration_ms: float, 
             success: bool = True, error: str = ""):
        """
        记录日志
        
        Args:
            user_input: 用户输入
            response: 机器人回复
            duration_ms: 响应时间（毫秒）
            success: 是否成功
            error: 错误信息
        """
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'request_id': self.request_count,
            'user_input': user_input[:100],  # 限制长度
            'response': response[:100] if response else "",
            'duration_ms': round(duration_ms, 2),
            'success': success,
            'error': error
        }
        
        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # 打印到控制台（可选）
        status = "✓" if success else "✗"
        print(f"[{status}] 请求 #{self.request_count} | 耗时：{duration_ms:.2f}ms")
    
    def get_report(self) -> str:
        """
        生成性能报告
        
        Returns:
            性能报告字符串
        """
        stats = self.monitor.get_statistics()
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║              Alice 性能报告                              ║
╠══════════════════════════════════════════════════════════╣
║  总请求数：{stats['count']:>10}                                  ║
║  平均响应时间：{stats['avg_ms']:>10.2f} ms                       ║
║  最小响应时间：{stats['min_ms']:>10.2f} ms                       ║
║  最大响应时间：{stats['max_ms']:>10.2f} ms                       ║
║  P50 响应时间：{stats.get('p50_ms', 0):>10.2f} ms                       ║
║  P95 响应时间：{stats.get('p95_ms', 0):>10.2f} ms                       ║
║  成功率：{stats['success_rate']:>10.1f}%                             ║
╚══════════════════════════════════════════════════════════╝
"""
        return report


# 使用示例
if __name__ == "__main__":
    # 测试性能监控
    monitor = PerformanceMonitor()
    
    # 模拟性能测试
    for i in range(10):
        monitor.start_timer(f"request_{i}")
        time.sleep(0.01 + 0.005 * i)  # 模拟处理时间
        monitor.stop_timer(f"request_{i}")
    
    # 打印统计
    stats = monitor.get_statistics()
    print("性能统计:")
    print(f"  请求数：{stats['count']}")
    print(f"  平均：{stats['avg_ms']:.2f}ms")
    print(f"  最小：{stats['min_ms']:.2f}ms")
    print(f"  最大：{stats['max_ms']:.2f}ms")
    print(f"  P95: {stats['p95_ms']:.2f}ms")
