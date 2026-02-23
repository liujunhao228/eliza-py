"""
数据分析埋点 Schema

定义用户行为追踪和数据采集的数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# 事件类型定义
# =============================================================================

class EventType(str, Enum):
    """分析事件类型"""

    # =============================================================================
    # 页面访问
    # =============================================================================
    PAGE_VIEW = "page_view"
    PAGE_LOAD = "page_load"

    # =============================================================================
    # 用户行为
    # =============================================================================
    BUTTON_CLICK = "button_click"
    INPUT_CHANGE = "input_change"
    FORM_SUBMIT = "form_submit"

    # =============================================================================
    # 匹配相关
    # =============================================================================
    MATCH_START = "match_start"
    MATCH_FOUND = "match_found"
    MATCH_TIMEOUT = "match_timeout"
    MATCH_CANCEL = "match_cancel"
    QUEUE_STATUS_UPDATE = "queue_status_update"

    # =============================================================================
    # 聊天相关
    # =============================================================================
    CHAT_MESSAGE_SENT = "chat_message_sent"
    CHAT_MESSAGE_RECEIVED = "chat_message_received"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"

    # =============================================================================
    # 博弈决策
    # =============================================================================
    META_CONVERSATION = "meta_conversation"
    MID_GAME_JUDGMENT = "mid_game_judgment"
    CONFIDENCE_SELECT = "confidence_select"
    SURVEY_SUBMIT = "survey_submit"
    GAME_END = "game_end"

    # =============================================================================
    # 积分相关
    # =============================================================================
    SCORE_CHANGE = "score_change"
    SCORE_HISTORY_VIEW = "score_history_view"

    # =============================================================================
    # 性能数据
    # =============================================================================
    API_RESPONSE = "api_response"
    WS_MESSAGE_SENT = "ws_message_sent"
    WS_MESSAGE_RECEIVED = "ws_message_received"
    ERROR_OCCURRED = "error_occurred"


# =============================================================================
# 事件数据模型
# =============================================================================

class AnalyticsEvent(BaseModel):
    """分析事件"""

    # 事件基本信息
    event_type: EventType = Field(..., description="事件类型")
    event_id: Optional[str] = Field(None, description="事件唯一 ID")

    # 用户信息
    user_id: Optional[int] = Field(None, description="用户 ID")
    session_id: Optional[int] = Field(None, description="会话 ID")

    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间戳")

    # 事件元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="事件元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# =============================================================================
# 特定事件类型
# =============================================================================

class PageViewEvent(AnalyticsEvent):
    """页面访问事件"""
    event_type: EventType = EventType.PAGE_VIEW
    metadata: dict = Field(..., description={
        "page": "页面路径",
        "title": "页面标题",
        "referrer": "来源页面",
    })


class ButtonClickEvent(AnalyticsEvent):
    """按钮点击事件"""
    event_type: EventType = EventType.BUTTON_CLICK
    metadata: dict = Field(..., description={
        "button_id": "按钮 ID",
        "button_text": "按钮文本",
        "page": "所在页面",
    })


class MatchStartEvent(AnalyticsEvent):
    """匹配开始事件"""
    event_type: EventType = EventType.MATCH_START
    metadata: dict = Field(..., description={
        "match_type": "匹配类型 (human/ai)",
        "queue_size": "队列大小",
    })


class MatchFoundEvent(AnalyticsEvent):
    """匹配成功事件"""
    event_type: EventType = EventType.MATCH_FOUND
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "opponent_type": "对手类型",
        "wait_time": "等待时间 (秒)",
        "is_honeypot": "是否为钓鱼机器人",
    })


class ChatMessageEvent(AnalyticsEvent):
    """聊天消息事件"""
    event_type: EventType = EventType.CHAT_MESSAGE_SENT
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "message_length": "消息长度",
        "is_meta": "是否为元对话",
        "meta_keyword": "元对话关键词",
    })


class MetaConversationEvent(AnalyticsEvent):
    """元对话事件"""
    event_type: EventType = EventType.META_CONVERSATION
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "keyword": "触发的关键词",
        "meta_count": "当前元对话次数",
        "message": "消息内容",
    })


class MidGameJudgmentEvent(AnalyticsEvent):
    """场中判断事件"""
    event_type: EventType = EventType.MID_GAME_JUDGMENT
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "user_guess": "用户判断",
        "confidence": "信心等级",
        "turn": "当前轮数",
        "meta_count": "元对话次数",
    })


class ConfidenceSelectEvent(AnalyticsEvent):
    """信心选择事件"""
    event_type: EventType = EventType.CONFIDENCE_SELECT
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "confidence_level": "信心等级 (low/mid/high)",
        "predicted_score": "预测积分",
    })


class SurveySubmitEvent(AnalyticsEvent):
    """问卷提交事件"""
    event_type: EventType = EventType.SURVEY_SUBMIT
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "user_guess": "用户判断",
        "confidence_level": "信心等级",
        "fluency_rating": "流畅度评分",
        "has_reason": "是否填写理由",
    })


class ScoreChangeEvent(AnalyticsEvent):
    """积分变化事件"""
    event_type: EventType = EventType.SCORE_CHANGE
    metadata: dict = Field(..., description={
        "session_id": "会话 ID",
        "score_change": "积分变化",
        "score_before": "变化前积分",
        "score_after": "变化后积分",
        "reason": "变化原因",
        "is_correct": "判断是否正确",
    })


class ApiResponseEvent(AnalyticsEvent):
    """API 响应事件"""
    event_type: EventType = EventType.API_RESPONSE
    metadata: dict = Field(..., description={
        "endpoint": "API 端点",
        "method": "HTTP 方法",
        "status_code": "响应状态码",
        "response_time_ms": "响应时间 (毫秒)",
        "error_message": "错误消息 (如果有)",
    })


class WsMessageEvent(AnalyticsEvent):
    """WebSocket 消息事件"""
    event_type: EventType = EventType.WS_MESSAGE_SENT
    metadata: dict = Field(..., description={
        "ws_type": "WebSocket 类型 (match/chat)",
        "message_type": "消息类型",
        "message_size": "消息大小 (字节)",
    })


class ErrorEvent(AnalyticsEvent):
    """错误事件"""
    event_type: EventType = EventType.ERROR_OCCURRED
    metadata: dict = Field(..., description={
        "error_code": "错误代码",
        "error_message": "错误消息",
        "page": "发生错误的页面",
        "stack_trace": "堆栈跟踪 (如果有)",
    })


# =============================================================================
# 批量提交
# =============================================================================

class AnalyticsBatchSubmit(BaseModel):
    """批量提交分析事件"""

    events: List[AnalyticsEvent] = Field(..., description="事件列表", min_items=1, max_items=100)
    user_id: Optional[int] = Field(None, description="用户 ID")
    submitted_at: datetime = Field(default_factory=datetime.utcnow, description="提交时间")


class AnalyticsBatchResponse(BaseModel):
    """批量提交响应"""

    success: bool = True
    accepted_count: int = Field(..., description="接受的事件数")
    rejected_count: int = Field(..., description="拒绝的事件数")
    message: Optional[str] = None


# =============================================================================
# 统计数据
# =============================================================================

class AnalyticsSummary(BaseModel):
    """分析数据摘要"""

    # 时间范围
    start_time: datetime
    end_time: datetime

    # 用户统计
    total_users: int = 0
    active_users: int = 0

    # 匹配统计
    total_matches: int = 0
    human_matches: int = 0
    ai_matches: int = 0
    avg_wait_time: float = 0.0

    # 聊天统计
    total_messages: int = 0
    total_meta_conversations: int = 0
    avg_messages_per_session: float = 0.0

    # 博弈统计
    total_judgments: int = 0
    correct_judgments: int = 0
    judgment_accuracy: float = 0.0
    total_score_changes: int = 0

    # 性能统计
    avg_api_response_time_ms: float = 0.0
    total_errors: int = 0


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "EventType",
    "AnalyticsEvent",
    "PageViewEvent",
    "ButtonClickEvent",
    "MatchStartEvent",
    "MatchFoundEvent",
    "ChatMessageEvent",
    "MetaConversationEvent",
    "MidGameJudgmentEvent",
    "ConfidenceSelectEvent",
    "SurveySubmitEvent",
    "ScoreChangeEvent",
    "ApiResponseEvent",
    "WsMessageEvent",
    "ErrorEvent",
    "AnalyticsBatchSubmit",
    "AnalyticsBatchResponse",
    "AnalyticsSummary",
]
