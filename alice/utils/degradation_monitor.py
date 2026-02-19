#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
降级监控模块

根据编码规范实现：
- 降级事件记录
- 降级质量评估
- 降级告警
- 降级报告生成

使用示例:
    from alice.utils.degradation_monitor import degradation_monitor
    
    # 注册降级事件
    degradation_monitor.register_degradation(
        component='ltp_syntax_analysis',
        reason='LTP 不可用',
        severity=2,
        recovery_plan='安装 LTP 库'
    )
    
    # 解决降级
    degradation_monitor.resolve_degradation(degradation_id)
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DegradationEvent:
    """降级事件"""
    id: str
    component: str
    reason: str
    severity: int  # 1-5, 5 最严重
    start_time: float
    recovery_plan: Optional[str] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    alert_sent: bool = False
    quality_checks: Dict[str, bool] = field(default_factory=dict)


class DegradationQualityChecker:
    """
    降级质量检查器

    根据编码规范，降级应该满足：
    1. 功能完整性：降级后仍能完成核心任务
    2. 数据一致性：不会产生错误或矛盾的结果
    3. 用户体验：用户能够理解当前状态
    4. 可追溯性：能够追踪降级原因和影响
    5. 可恢复性：系统能够恢复正常状态
    """

    def check_degradation_quality(
        self,
        original_functionality: str,
        degraded_functionality: str,
        impact_level: str,
        user_notification: str
    ) -> Dict[str, bool]:
        """
        检查降级质量

        Args:
            original_functionality: 原始功能描述
            degraded_functionality: 降级后功能描述
            impact_level: 影响等级 ('low', 'medium', 'high')
            user_notification: 用户通知内容

        Returns:
            质量检查结果字典
        """
        checks = {
            '功能完整性': self._check_functionality_integrity(
                original_functionality, degraded_functionality
            ),
            '数据一致性': self._check_data_consistency(),
            '用户体验': self._check_user_experience(user_notification),
            '可追溯性': self._check_traceability(),
            '可恢复性': self._check_recoverability()
        }

        return checks

    def _check_functionality_integrity(self, original: str, degraded: str) -> bool:
        """检查功能完整性"""
        # 降级后的功能应该至少完成原始功能的核心部分
        # 这里简化处理，实际应该根据具体功能判断
        essential_tasks = self._extract_essential_tasks(original)
        degraded_tasks = self._extract_essential_tasks(degraded)

        # 如果降级后仍能完成核心任务，则认为功能完整
        return len(degraded_tasks) > 0

    def _extract_essential_tasks(self, functionality: str) -> List[str]:
        """提取功能的核心任务"""
        # 简化实现，根据关键词判断
        task_keywords = {
            '分析': 'analyze',
            '处理': 'process',
            '分词': 'segment',
            '理解': 'understand',
            '响应': 'respond',
        }
        return [task for kw, task in task_keywords.items() if kw in functionality]

    def _check_data_consistency(self) -> bool:
        """检查数据一致性"""
        # 默认认为降级不会导致数据不一致
        # 实际应该根据具体业务逻辑判断
        return True

    def _check_user_experience(self, notification: str) -> bool:
        """检查用户体验"""
        # 用户通知应该是清晰、有用的
        if not notification:
            return False

        # 不应该包含技术术语
        tech_terms = ['exception', 'null', 'undefined', 'stack trace', 'error']
        if any(term in notification.lower() for term in tech_terms):
            return False

        # 应该提供下一步建议或清晰说明
        helpful_keywords = ['请', '可以', '建议', '稍后', '暂时', '简化', '基础']
        return any(keyword in notification for keyword in helpful_keywords)

    def _check_traceability(self) -> bool:
        """检查可追溯性"""
        # 默认认为降级事件会被记录
        return True

    def _check_recoverability(self) -> bool:
        """检查可恢复性"""
        # 默认认为系统能够恢复正常状态
        return True


class DegradationMonitor:
    """
    降级监控器

    功能:
    - 降级事件注册和解决
    - 降级频率和严重度告警
    - 降级报告生成
    - 降级质量评估
    """

    def __init__(self):
        """初始化降级监控器"""
        self.active_degradations: Dict[str, DegradationEvent] = {}
        self.degradation_history: List[DegradationEvent] = []
        self.quality_checker = DegradationQualityChecker()

        # 告警阈值
        self.alert_thresholds = {
            'frequency': 10,      # 同一降级 10 次以上告警
            'duration': 300,      # 持续 5 分钟以上告警
            'impact_severity': 3  # 影响严重度阈值
        }

        # 事件计数器
        self._event_counter = 0
        self._component_counts: Dict[str, int] = defaultdict(int)

    def _generate_degradation_id(self, component: str) -> str:
        """生成降级事件 ID"""
        self._event_counter += 1
        return f"{component}_{int(time.time())}_{self._event_counter}"

    def register_degradation(
        self,
        component: str,
        reason: str,
        severity: int,
        recovery_plan: Optional[str] = None,
        quality_check_result: Optional[Dict[str, bool]] = None,
    ) -> str:
        """
        注册降级事件

        Args:
            component: 组件名称
            reason: 降级原因
            severity: 严重程度 (1-5)
            recovery_plan: 恢复计划
            quality_check_result: 质量检查结果

        Returns:
            降级事件 ID
        """
        degradation_id = self._generate_degradation_id(component)

        degradation_info = DegradationEvent(
            id=degradation_id,
            component=component,
            reason=reason,
            severity=severity,
            start_time=time.time(),
            recovery_plan=recovery_plan,
            quality_checks=quality_check_result or {},
        )

        self.active_degradations[degradation_id] = degradation_info
        self.degradation_history.append(degradation_info)
        self._component_counts[component] += 1

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
            是否解决成功
        """
        if degradation_id not in self.active_degradations:
            logger.warning(f"降级事件不存在：{degradation_id}")
            return False

        degradation = self.active_degradations[degradation_id]
        degradation.end_time = time.time()
        degradation.duration = degradation.end_time - degradation.start_time

        logger.info(
            f"降级已解决：{degradation.component} "
            f"(持续时间：{degradation.duration:.1f}秒)"
        )

        del self.active_degradations[degradation_id]
        return True

    def _check_and_send_alerts(self, degradation_info: DegradationEvent) -> None:
        """检查并发送告警"""
        # 频率检查
        component_degradations = [
            d for d in self.degradation_history
            if d.component == degradation_info.component
            and time.time() - d.start_time < 3600  # 最近 1 小时内
        ]

        if len(component_degradations) >= self.alert_thresholds['frequency']:
            self._send_frequency_alert(degradation_info, len(component_degradations))

        # 严重度检查
        if degradation_info.severity >= self.alert_thresholds['impact_severity']:
            self._send_severity_alert(degradation_info)

    def _send_frequency_alert(self, degradation_info: DegradationEvent, count: int) -> None:
        """发送频率告警"""
        if not degradation_info.alert_sent:
            logger.critical(
                f"降级频率过高告警：{degradation_info.component} "
                f"在最近 1 小时内发生 {count} 次降级"
            )
            degradation_info.alert_sent = True

    def _send_severity_alert(self, degradation_info: DegradationEvent) -> None:
        """发送严重度告警"""
        if not degradation_info.alert_sent:
            logger.critical(
                f"降级严重度告警：{degradation_info.component} "
                f"严重度 {degradation_info.severity}/5"
            )
            degradation_info.alert_sent = True

    def get_active_degradations(self) -> List[Dict[str, Any]]:
        """获取当前激活的降级事件"""
        return [
            {
                'id': d.id,
                'component': d.component,
                'reason': d.reason,
                'severity': d.severity,
                'duration': time.time() - d.start_time,
                'recovery_plan': d.recovery_plan,
            }
            for d in self.active_degradations.values()
        ]

    def get_degradation_report(self) -> Dict[str, Any]:
        """获取降级报告"""
        # 计算平均恢复时间
        resolved_degradations = [
            d for d in self.degradation_history
            if d.end_time is not None
        ]

        avg_recovery_time = 0.0
        if resolved_degradations:
            total_recovery_time = sum(
                d.duration for d in resolved_degradations if d.duration
            )
            avg_recovery_time = total_recovery_time / len(resolved_degradations)

        # 获取最常降级的组件
        most_degraded = sorted(
            self._component_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'active_degradations': len(self.active_degradations),
            'recent_degradations': len([
                d for d in self.degradation_history
                if time.time() - d.start_time < 86400  # 最近 24 小时
            ]),
            'most_degraded_components': most_degraded,
            'average_recovery_time': avg_recovery_time,
            'total_degradations': len(self.degradation_history),
        }

    def reset(self) -> None:
        """重置监控器（用于测试）"""
        self.active_degradations.clear()
        self.degradation_history.clear()
        self._component_counts.clear()
        self._event_counter = 0
        logger.info("降级监控器已重置")


# 全局降级监控器实例
degradation_monitor = DegradationMonitor()
