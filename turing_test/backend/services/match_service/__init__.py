"""
匹配服务模块（概率分流版）- 重构版

修复内容:
- 添加缺失的 join_queue 方法
- 为所有共享状态添加锁保护
- 优化 Bot 池实现效率
- 完善类型注解
- 增强错误处理
- 修复资源泄漏

匹配逻辑:
- 30% 概率匹配真人（FIFO）
- 70% 概率匹配 Bot（含 15% 钓鱼 Bot）
- 真人超时 10 秒降级为 Bot
- 结果暂存，前端主动拉取
"""

from .service import (
    MatchService,
    get_match_service,
    create_match_service,
    reset_match_service,
    MatchType,
    MatchRequest,
    MatchResultData,
    SafeMatchResult,
    MatchStatistics,
    MatchServiceConfig,
)
from .types import (
    UserId,
    SessionId,
    WebsocketRef,
    OpponentType,
)

__all__ = [
    # 服务类
    "MatchService",
    # 工厂函数
    "get_match_service",
    "create_match_service",
    "reset_match_service",
    # 类型
    "MatchType",
    "MatchRequest",
    "MatchResultData",
    "SafeMatchResult",
    "MatchStatistics",
    "MatchServiceConfig",
    # 类型别名
    "UserId",
    "SessionId",
    "WebsocketRef",
    "OpponentType",
]
