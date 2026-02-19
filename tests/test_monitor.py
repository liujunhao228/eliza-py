#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控模块测试用例

测试 UnifiedMonitor 和 DialogueLogger 的功能是否正常工作。
"""

import pytest
import time
import logging
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from alice.utils.monitor import UnifiedMonitor, DialogueLogger, PerformanceMetrics


class TestUnifiedMonitor:
    """测试统一监控系统"""

    def test_initialization(self):
        """测试初始化"""
        monitor = UnifiedMonitor(sample_rate=0.5)
        
        assert monitor.sample_rate == 0.5
        assert len(monitor._metrics) == 0
        assert len(monitor._errors) == 0
        assert len(monitor._timers) == 0

    def test_start_stop_timer(self):
        """测试计时器功能"""
        monitor = UnifiedMonitor()
        
        # 开始计时
        monitor.start_timer("test_component")
        assert "test_component" in monitor._timers
        
        # 停止计时
        time.sleep(0.01)  # 等待一小段时间
        duration = monitor.stop_timer("test_component")
        
        assert duration > 0
        assert "test_component" not in monitor._timers
        assert monitor._component_stats["test_component"]["count"] > 0  # 修复：移除len()

    def test_timer_not_started(self):
        """测试未启动计时器的情况"""
        monitor = UnifiedMonitor()
        
        # 尝试停止未启动的计时器
        duration = monitor.stop_timer("nonexistent_component")
        assert duration == 0.0

    def test_record_interaction(self):
        """测试记录交互性能"""
        monitor = UnifiedMonitor()
        
        request_time = time.time()
        time.sleep(0.01)  # 模拟处理时间
        response_time = time.time()
        
        monitor.record_interaction(
            request_time=request_time,
            response_time=response_time,
            success=True,
            metadata={"test": "data"}
        )
        
        assert len(monitor._metrics) == 1
        metric = monitor._metrics[0]
        assert metric.component == "interaction"
        assert metric.success is True
        assert metric.metadata == {"test": "data"}

    def test_log_error(self):
        """测试错误记录"""
        monitor = UnifiedMonitor()
        
        try:
            raise ValueError("测试错误")
        except Exception as e:
            monitor.log_error("test_component", e, {"context": "test"})
        
        assert len(monitor._errors) == 1
        error = monitor._errors[0]
        assert error["component"] == "test_component"
        assert error["error_type"] == "ValueError"
        assert error["error_message"] == "测试错误"
        assert error["context"] == {"context": "test"}

    def test_get_performance_report(self):
        """测试获取性能报告"""
        monitor = UnifiedMonitor()
        
        # 添加一些测试数据
        monitor.record_interaction(time.time(), time.time() + 0.1, True)
        monitor.record_interaction(time.time(), time.time() + 0.2, True)
        monitor.record_interaction(time.time(), time.time() + 0.15, False)
        
        report = monitor.get_performance_report()
        
        assert report["total_interactions"] == 3
        assert report["success_rate"] == pytest.approx(66.67, 0.01)
        assert "avg_response_time_ms" in report
        assert "component_stats" in report

    def test_get_error_report(self):
        """测试获取错误报告"""
        monitor = UnifiedMonitor()
        
        # 添加一些错误
        try:
            raise ValueError("错误1")
        except Exception as e:
            monitor.log_error("component1", e)
            
        try:
            raise RuntimeError("错误2")
        except Exception as e:
            monitor.log_error("component2", e)
        
        report = monitor.get_error_report()
        
        assert report["total_errors"] == 2
        assert len(report["errors_by_component"]) == 2
        assert "recent_errors" in report

    def test_clear(self):
        """测试清空数据"""
        monitor = UnifiedMonitor()
        
        # 添加一些数据
        monitor.start_timer("test")
        monitor.record_interaction(time.time(), time.time(), True)
        monitor.log_error("test", ValueError("test"))
        
        # 清空
        monitor.clear()
        
        assert len(monitor._metrics) == 0
        assert len(monitor._errors) == 0
        assert len(monitor._timers) == 0
        assert len(monitor._component_stats) == 0


class TestDialogueLogger:
    """测试对话日志器"""

    def test_initialization(self):
        """测试初始化"""
        logger = DialogueLogger(log_dir="/tmp/test")
        
        assert logger.log_dir == "/tmp/test"
        assert len(logger._dialogues) == 0
        assert len(logger._performance_logs) == 0

    def test_log_dialogue(self):
        """测试记录对话"""
        logger = DialogueLogger()
        
        logger.log_dialogue(
            user_input="你好",
            bot_response="你好！有什么可以帮助你的吗？",
            metadata={"session_id": "test123"}
        )
        
        assert len(logger._dialogues) == 1
        dialogue = logger._dialogues[0]
        assert dialogue["user_input"] == "你好"
        assert dialogue["bot_response"] == "你好！有什么可以帮助你的吗？"
        assert dialogue["metadata"] == {"session_id": "test123"}

    def test_log_performance(self):
        """测试记录性能日志"""
        logger = DialogueLogger()
        
        logger.log_performance("test_component", 150.5, True)
        
        assert len(logger._performance_logs) == 1
        perf_log = logger._performance_logs[0]
        assert perf_log["component"] == "test_component"
        assert perf_log["duration_ms"] == 150.5
        assert perf_log["success"] is True

    def test_get_recent_dialogues(self):
        """测试获取最近对话"""
        logger = DialogueLogger()
        
        # 添加多个对话
        for i in range(15):
            logger.log_dialogue(f"用户{i}", f"回复{i}")
        
        recent = logger.get_recent_dialogues(10)
        assert len(recent) == 10
        assert recent[0]["user_input"] == "用户5"  # 最早的10个中的第一个

    def test_get_stats(self):
        """测试获取统计信息"""
        logger = DialogueLogger()
        
        logger.log_dialogue("用户", "机器人")
        logger.log_performance("test", 100.0)
        
        stats = logger.get_stats()
        assert stats["total_dialogues"] == 1
        assert stats["total_performance_logs"] == 1

    def test_clear(self):
        """测试清空日志"""
        logger = DialogueLogger()
        
        logger.log_dialogue("用户", "机器人")
        logger.log_performance("test", 100.0)
        
        logger.clear()
        
        assert len(logger._dialogues) == 0
        assert len(logger._performance_logs) == 0


class TestIntegration:
    """集成测试"""

    def test_monitor_with_logging(self):
        """测试监控与日志系统的集成"""
        # 创建内存日志处理器来捕获日志
        log_capture = []
        
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())
        
        # 设置日志
        logger = logging.getLogger('alice.utils.monitor')
        handler = CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            monitor = UnifiedMonitor()
            
            # 测试各种功能
            monitor.start_timer("integration_test")
            time.sleep(0.01)
            duration = monitor.stop_timer("integration_test", success=True)
            
            monitor.record_interaction(time.time(), time.time() + 0.05, True)
            
            # 检查日志是否被捕获
            assert len(log_capture) > 0
            assert any("性能" in msg for msg in log_capture)
            assert any("交互性能" in msg for msg in log_capture)
            
        finally:
            logger.removeHandler(handler)

    def test_dialogue_logger_with_real_scenario(self):
        """测试真实场景下的对话日志"""
        logger = DialogueLogger()
        
        # 模拟一个完整的对话流程
        conversation = [
            ("你好", "你好！有什么可以帮助你的吗？"),
            ("今天天气怎么样？", "我无法获取实时天气信息。"),
            ("再见", "再见！期待下次交流。")
        ]
        
        for user_input, bot_response in conversation:
            logger.log_dialogue(user_input, bot_response)
            logger.log_performance("response_generation", 50.0 + len(user_input))
        
        # 验证记录
        assert len(logger._dialogues) == 3
        assert len(logger._performance_logs) == 3
        
        # 检查统计数据
        stats = logger.get_stats()
        assert stats["total_dialogues"] == 3
        assert stats["total_performance_logs"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])