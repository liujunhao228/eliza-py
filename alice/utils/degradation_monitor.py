#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
降级监控器模块

根据编码规范实现：
- 降级事件注册和追踪
- 降级告警机制
- 降级报告生成
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class DegradationEvent:
    """降级事件数据类"""
    component: str              # 降级组件
    reason: str                 # 降级原因
    severity: int               # 严重度 (1-5)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    recovery_plan: str = ""
    alert_sent: bool = False

    @property
    def duration(self) -> float:
        """获取降级持续时间（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'component': self.component,
            'reason': self.reason,
            'severity': self.severity,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'duration_seconds': self.duration,
            'recovery_plan': self.recovery_plan,
            'alert_sent': self.alert_sent
        }


class DegradationMonitor:
    """
    降级监控器

    功能:
    - 注册降级事件
    - 追踪活跃降级
    - 发送告警
    - 生成报告
    """

    def __init__(self, alert_threshold_frequency: int = 10,
                 alert_threshold_duration: float = 300,
                 alert_threshold_severity: int = 3):
        """
        初始化降级监控器

        Args:
            alert_threshold_frequency: 频率告警阈值（次/小时）
            alert_threshold_duration: 持续时间告警阈值（秒）
            alert_threshold_severity: 严重度告警阈值
        """
        self.active_degradations: Dict[str, DegradationEvent] = {}
        self.degradation_history: deque = deque(maxlen=1000)

        self.alert_thresholds = {
            'frequency': alert_threshold_frequency,
            'duration': alert_threshold_duration,
            'severity': alert_threshold_severity
        }

        self._alert_callbacks: List[callable] = []

    def register_degradation(
        self,
        component: str,
        reason: str,
        severity: int,
        recovery_plan: str = ""
    ) -> str:
        """
        注册降级事件

        Args:
            component: 组件名称
            reason: 降级原因
            severity: 严重度 (1-5)
            recovery_plan: 恢复计划

        Returns:
            降级事件 ID
        """
        degradation_id = f"{component}_{int(time.time() * 1000)}"

        degradation_info = DegradationEvent(
            component=component,
            reason=reason,
            severity=severity,
            recovery_plan=recovery_plan
        )

        self.active_degradations[degradation_id] = degradation_info
        self.degradation_history.append(degradation_info)

        logger.warning(
            f"组件降级：{component} | 原因：{reason} | "
            f"严重度：{severity}/5 | 恢复计划：{recovery_plan}"
        )

        # 检查是否需要发送告警
        self._check_and_send_alerts(degradation_info)

        return degradation_id

    def resolve_degradation(self, degradation_id: str) -> bool:
        """
        解决降级

        Args:
            degradation_id: 降级事件 ID

        Returns:
            是否成功解决
        """
        if degradation_id in self.active_degradations:
            degradation = self.active_degradations[degradation_id]
            degradation.end_time = time.time()

            logger.info(
                f"降级已解决：{degradation.component} "
                f"(持续时间：{degradation.duration:.1f}秒)"
            )

            del self.active_degradations[degradation_id]
            return True

        return False

    def resolve_all_degradations(self, component: str = None) -> int:
        """
        解决所有降级（或指定组件的降级）

        Args:
            component: 组件名称，None 则解决所有

        Returns:
            解决的降级数量
        """
        resolved_count = 0

        degradation_ids = list(self.active_degradations.keys())
        for degradation_id in degradation_ids:
            degradation = self.active_degradations[degradation_id]
            if component is None or degradation.component == component:
                if self.resolve_degradation(degradation_id):
                    resolved_count += 1

        return resolved_count

    def _check_and_send_alerts(self, degradation_info: DegradationEvent):
        """检查并发送告警"""
        # 严重度检查
        if degradation_info.severity >= self.alert_thresholds['severity']:
            self._send_alert('severity', degradation_info)

        # 频率检查（最近 1 小时内同一组件的降级次数）
        component_degradations = [
            d for d in self.degradation_history
            if d.component == degradation_info.component
            and time.time() - d.start_time < 3600
        ]

        if len(component_degradations) >= self.alert_thresholds['frequency']:
            self._send_alert('frequency', degradation_info, len(component_degradations))

    def _send_alert(self, alert_type: str, degradation_info: DegradationEvent,
                    count: int = None):
        """发送告警"""
        degradation_info.alert_sent = True

        if alert_type == 'severity':
            message = (
                f"[严重告警] 组件降级：{degradation_info.component} | "
                f"严重度：{degradation_info.severity}/5 | "
                f"原因：{degradation_info.reason}"
            )
        else:
            message = (
                f"[频率告警] 组件 {degradation_info.component} "
                f"在最近 1 小时内降级 {count} 次"
            )

        logger.critical(message)

        # 调用告警回调
        for callback in self._alert_callbacks:
            try:
                callback(message, degradation_info.to_dict())
            except Exception as e:
                logger.error(f"告警回调执行失败：{e}")

    def register_alert_callback(self, callback: callable):
        """
        注册告警回调

        Args:
            callback: 回调函数 (message: str, degradation_info: dict)
        """
        self._alert_callbacks.append(callback)

    def get_active_degradations(self) -> List[Dict]:
        """获取当前活跃的降级列表"""
        return [d.to_dict() for d in self.active_degradations.values()]

    def get_degradation_report(self) -> Dict:
        """获取降级报告"""
        now = time.time()
        recent_24h = [
            d for d in self.degradation_history
            if now - d.start_time < 86400
        ]

        # 统计最常降级的组件
        component_counts: Dict[str, int] = {}
        for d in recent_24h:
            component_counts[d.component] = component_counts.get(d.component, 0) + 1

        most_degraded = sorted(
            component_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # 计算平均恢复时间
        resolved_degradations = [
            d for d in self.degradation_history
            if d.end_time is not None
        ]

        avg_recovery_time = 0
        if resolved_degradations:
            total_recovery = sum(d.duration for d in resolved_degradations)
            avg_recovery_time = total_recovery / len(resolved_degradations)

        return {
            'active_degradations': len(self.active_degradations),
            'recent_degradations_24h': len(recent_24h),
            'most_degraded_components': most_degraded,
            'average_recovery_time_seconds': avg_recovery_time,
            'alert_thresholds': self.alert_thresholds
        }

    def clear_history(self):
        """清空历史记录"""
        self.degradation_history.clear()

    def reset(self):
        """重置所有状态"""
        self.active_degradations.clear()
        self.degradation_history.clear()


# 全局降级监控器实例
degradation_monitor = DegradationMonitor()
