"""
匹配服务类型定义

提供完整的类型注解，避免使用裸 dict。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Literal
from enum import Enum


class MatchType(str, Enum):
    """匹配类型"""
    HUMAN = "human"           # 真人匹配
    BOT = "bot"               # 普通 Bot
    HONEYPOT = "honeypot"     # 钓鱼 Bot
    BOT_TIMEOUT = "bot_timeout"  # 超时降级为 Bot


class OpponentType(str, Enum):
    """对手类型（前端可见）"""
    OPPONENT = "opponent"  # 统一返回给前端


@dataclass
class MatchRequest:
    """
    匹配请求

    Attributes:
        user_id: 用户 ID
        timestamp: 加入队列时间戳（UTC）
        match_type: 匹配类型
        websocket_ref: WebSocket 引用 ID
        user_score: 用户积分
    """
    user_id: int
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    match_type: MatchType = MatchType.HUMAN
    websocket_ref: Optional[int] = None
    user_score: int = 100


@dataclass
class MatchResultData:
    """
    匹配结果数据（内部使用）

    Attributes:
        session_id: 会话 ID
        opponent_type: 对手类型
        true_identity: 真实身份（后台记录）
        bot_level: Bot 等级（后台记录）
        is_honeypot: 是否钓鱼 Bot（后台记录）
        opponent_user_id: 对手用户 ID（真人匹配时）
        match_duration_ms: 假装延迟（毫秒）
        matched_at: 匹配时间（ISO 格式）
    """
    session_id: int
    opponent_type: str
    true_identity: Optional[str]
    bot_level: Optional[str]
    is_honeypot: bool
    opponent_user_id: Optional[int] = None
    match_duration_ms: int = 0
    matched_at: str = ""

    def __post_init__(self):
        """后处理：设置默认值"""
        if not self.matched_at:
            self.matched_at = datetime.now(timezone.utc).isoformat()


@dataclass
class SafeMatchResult:
    """
    安全匹配结果（返回给前端）

    仅包含非敏感字段，防止泄露对手真实身份。

    Attributes:
        session_id: 会话 ID
        opponent_type: 对手类型（固定为 "opponent"）
        match_duration_ms: 假装延迟（毫秒）
        message: 提示信息（可选）
    """
    session_id: int
    opponent_type: str = "opponent"
    match_duration_ms: int = 0
    message: Optional[str] = None


@dataclass
class MatchStatistics:
    """
    匹配服务统计信息

    Attributes:
        waiting_count: 等待队列人数
        human_waiting: 等待真人匹配的人数
        timeout_seconds: 超时时间（秒）
        bot_pool: Bot 池统计
        honeypot_pool: 钓鱼 Bot 池统计
    """
    waiting_count: int
    human_waiting: int
    timeout_seconds: int
    bot_pool: Dict[str, Any]
    honeypot_pool: Dict[str, Any]


# 类型别名
UserId = int
SessionId = int
WebsocketRef = int


@dataclass
class QueueSnapshot:
    """
    队列快照（供算法使用）

    Attributes:
        requests: 当前队列中的请求
        timestamp: 快照时间戳
    """
    requests: Dict[UserId, MatchRequest]
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
