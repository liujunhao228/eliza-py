#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控服务模块

提供统一的监控和日志服务：
- 性能追踪
- 错误记录
- 对话日志
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    component: str
    response_time_ms: float
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class UnifiedMonitor:
    """
    统一监控系统

    功能:
    - 性能指标收集
    - 结构化日志记录
    - 错误追踪
    - 性能报告生成
    """

    def __init__(self, sample_rate: float = 1.0):
        """
        初始化监控系统

        Args:
            sample_rate: 采样率 (0.0 - 1.0)
        """
        self.sample_rate = sample_rate
        self._metrics: List[PerformanceMetrics] = []
        self._errors: List[Dict[str, Any]] = []
        self._timers: Dict[str, float] = {}
        self._component_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_time": 0.0, "errors": 0}
        )

    def record_interaction(
        self,
        request_time: float,
        response_time: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录交互性能数据

        Args:
            request_time: 请求时间戳
            response_time: 响应时间戳
            success: 是否成功
            metadata: 额外元数据
        """
        duration_ms = (response_time - request_time) * 1000

        metrics = PerformanceMetrics(
            component="interaction",
            response_time_ms=duration_ms,
            success=success,
            metadata=metadata,
        )

        self._metrics.append(metrics)
        self._update_component_stats("interaction", duration_ms, success)

        logger.info(
            f"交互性能：{duration_ms:.2f}ms, 成功={success}",
            extra={"metrics": metrics.__dict__},
        )

    def start_timer(self, component: str) -> None:
        """
        开始计时

        Args:
            component: 组件名称
        """
        self._timers[component] = time.time()

    def stop_timer(
        self,
        component: str,
        success: bool = True,
    ) -> float:
        """
        停止计时

        Args:
            component: 组件名称
            success: 是否成功

        Returns:
            耗时（毫秒）
        """
        if component not in self._timers:
            logger.warning(f"计时器未启动：{component}")
            return 0.0

        start_time = self._timers.pop(component)
        duration_ms = (time.time() - start_time) * 1000

        self._update_component_stats(component, duration_ms, success)

        logger.debug(
            f"{component} 性能：{duration_ms:.2f}ms",
            extra={"component": component, "duration_ms": duration_ms},
        )

        return duration_ms

    def _update_component_stats(
        self,
        component: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """更新组件统计"""
        stats = self._component_stats[component]
        stats["count"] += 1
        stats["total_time"] += duration_ms
        if not success:
            stats["errors"] += 1

    def log_error(
        self,
        component: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录错误

        Args:
            component: 组件名称
            error: 异常对象
            context: 上下文信息
        """
        error_info = {
            "component": component,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        }

        self._errors.append(error_info)

        logger.error(
            f"{component} 错误：{type(error).__name__}: {error}",
            exc_info=True,
            extra={"error_info": error_info},
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告

        Returns:
            性能报告字典
        """
        if not self._metrics:
            return {"status": "no_data"}

        response_times = [m.response_time_ms for m in self._metrics]

        return {
            "total_interactions": len(self._metrics),
            "avg_response_time_ms": sum(response_times) / len(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "success_rate": (
                sum(1 for m in self._metrics if m.success) / len(self._metrics) * 100
            ),
            "component_stats": dict(self._component_stats),
        }

    def get_error_report(self) -> Dict[str, Any]:
        """
        获取错误报告

        Returns:
            错误报告字典
        """
        error_by_component = defaultdict(list)

        for error in self._errors:
            error_by_component[error["component"]].append(error)

        return {
            "total_errors": len(self._errors),
            "errors_by_component": dict(error_by_component),
            "recent_errors": self._errors[-10:],  # 最近 10 个错误
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "performance": self.get_performance_report(),
            "errors": self.get_error_report(),
            "sample_rate": self.sample_rate,
        }

    def clear(self) -> None:
        """清空监控数据"""
        self._metrics.clear()
        self._errors.clear()
        self._component_stats.clear()
        self._timers.clear()
        logger.info("监控数据已清空")


class DialogueLogger:
    """
    结构化对话日志

    功能:
    - 对话记录
    - 性能日志
    - 错误日志
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化对话日志

        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir
        self._dialogues: List[Dict[str, Any]] = []
        self._performance_logs: List[Dict[str, Any]] = []

        # 配置日志
        self._setup_logging()

    def _setup_logging(self) -> None:
        """配置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def log_dialogue(
        self,
        user_input: str,
        bot_response: str,
        rule_info: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录对话

        Args:
            user_input: 用户输入
            bot_response: 机器人响应
            rule_info: 规则触发信息（包含 script_id, intent, matched_pattern 等）
            metadata: 元数据
        """
        dialogue = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "bot_response": bot_response,
            "rule_info": rule_info or {},
            "metadata": metadata or {},
        }

        self._dialogues.append(dialogue)

        # 构建规则触发信息字符串
        rule_str = ""
        if rule_info:
            source = rule_info.get("source", "unknown")
            script_id = rule_info.get("script_id", "")
            if script_id:
                rule_str = f" [规则：{source}/{script_id}]"

        logger.info(
            f"对话：{user_input[:50]}... -> {bot_response[:50]}...{rule_str}",
            extra={"dialogue": dialogue, "rule_info": rule_info or {}},
        )

    def log_performance(
        self,
        component: str,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """
        记录性能日志

        Args:
            component: 组件名称
            duration_ms: 耗时
            success: 是否成功
        """
        perf_log = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "duration_ms": duration_ms,
            "success": success,
        }

        self._performance_logs.append(perf_log)

        logger.debug(
            f"性能：{component} = {duration_ms:.2f}ms",
            extra={"performance": perf_log},
        )

    def get_recent_dialogues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的对话记录"""
        return self._dialogues[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_dialogues": len(self._dialogues),
            "total_performance_logs": len(self._performance_logs),
        }

    def clear(self) -> None:
        """清空日志"""
        self._dialogues.clear()
        self._performance_logs.clear()
        logger.info("对话日志已清空")
