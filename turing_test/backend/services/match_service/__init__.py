"""
匹配服务模块（重构版）

基于新架构的匹配服务，职责清晰、易于测试。

架构层次:
1. Config: 配置管理
2. Algorithm: 匹配算法（可插拔）
3. Pools: Bot 池（普通 Bot/钓鱼 Bot）
4. Queue: 队列管理
5. ResultManager: 结果管理
6. Matcher: 匹配协调器
7. Service: 对外接口

匹配逻辑:
- 30% 概率匹配真人（FIFO）
- 70% 概率匹配 Bot（含 15% 钓鱼 Bot）
- 真人超时降级为 Bot
- 结果暂存，前端主动拉取
"""

from .config import MatchConfig
from .service import (
    MatchService,
    create_match_service,
    get_match_service,
    set_match_service,
    reset_match_service,
)
from .matcher import MatchCoordinator
from .queue import MatchQueue
from .result_manager import ResultManager
from .algorithm import (
    MatchAlgorithm,
    QueueSnapshot,
    ProbabilityAlgorithm,
    FIFOAlgorithm,
)
from .pools import (
    BotPoolBase,
    BotConfig,
    HoneypotBotConfig,
    BotPool,
    BotPoolConfig,
    HoneypotPool,
    HoneypotPoolConfig,
)
from .types import (
    UserId,
    SessionId,
    WebsocketRef,
    OpponentType,
    MatchType,
    MatchRequest,
    MatchResultData,
    SafeMatchResult,
    MatchStatistics,
)

__all__ = [
    # 配置
    "MatchConfig",
    # 服务类
    "MatchService",
    "MatchCoordinator",
    # 组件
    "MatchQueue",
    "ResultManager",
    # 算法
    "MatchAlgorithm",
    "QueueSnapshot",
    "ProbabilityAlgorithm",
    "FIFOAlgorithm",
    # Bot 池
    "BotPoolBase",
    "BotConfig",
    "HoneypotBotConfig",
    "BotPool",
    "BotPoolConfig",
    "HoneypotPool",
    "HoneypotPoolConfig",
    # 工厂函数
    "create_match_service",
    "get_match_service",
    "set_match_service",
    "reset_match_service",
    # 类型
    "MatchType",
    "MatchRequest",
    "MatchResultData",
    "SafeMatchResult",
    "MatchStatistics",
    # 类型别名
    "UserId",
    "SessionId",
    "WebsocketRef",
    "OpponentType",
]
