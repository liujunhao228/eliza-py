"""
Alice 工具模块

包含各种工具类和函数：
- 上下文管理
- 日志记录
- 性能监控
- 降级监控
- 敏感信息脱敏
- YAML 热重载
"""

from alice.utils.context import ContextManager
from alice.utils.logger import setup_logger
from alice.utils.monitor import UnifiedMonitor, DialogueLogger
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
from alice.utils.hot_reloader import (
    HotReloader,
    ManualHotReloader,
    ReloadResult,
    YAMLFileChangeHandler,
    create_hot_reloader,
)

__all__ = [
    # 上下文
    "ContextManager",
    # 日志
    "setup_logger",
    # 监控
    "UnifiedMonitor",
    "DialogueLogger",
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
    # 热重载
    "HotReloader",
    "ManualHotReloader",
    "ReloadResult",
    "YAMLFileChangeHandler",
    "create_hot_reloader",
]
