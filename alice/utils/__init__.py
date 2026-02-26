"""
Alice 工具模块

包含各种工具类和函数：
- 日志记录
- 性能监控
- 降级监控
- 敏感信息脱敏

注意：
- ContextManager 已移至 alice.core.context_manager
- UnifiedMonitor, DialogueLogger 已移至 alice.services.monitoring_service
"""

from alice.utils.logger import setup_logger
from alice.utils.performance import PerformanceMonitor
from alice.utils.degradation_monitor import (
    DegradationMonitor,
    DegradationQualityChecker,
    DegradationQualityStatus,
    degradation_monitor,
)
from alice.utils.degradation_recovery import RecoveryManager, recovery_manager
from alice.utils.sanitizer import (
    sanitize_text,
    sanitize_dict,
    sanitize_value,
    sanitize_for_logging,
    contains_sensitive_info,
    get_sensitive_info_types,
)

__all__ = [
    # 日志
    "setup_logger",
    # 监控
    "PerformanceMonitor",
    # 降级监控
    "DegradationMonitor",
    "DegradationQualityChecker",
    "DegradationQualityStatus",
    "degradation_monitor",
    # 降级恢复
    "RecoveryManager",
    "recovery_manager",
    # 脱敏工具
    "sanitize_text",
    "sanitize_dict",
    "sanitize_value",
    "sanitize_for_logging",
    "contains_sensitive_info",
    "get_sensitive_info_types",
]
