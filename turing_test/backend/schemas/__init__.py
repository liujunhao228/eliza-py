"""
Pydantic Schemas

定义 API 请求和响应的数据模型。
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


# =============================================================================
# 基础模型
# =============================================================================

class BaseSchema(BaseModel):
    """所有 Schema 的基类"""

    class Config:
        from_attributes = True  # 允许从 ORM 对象创建


# =============================================================================
# 用户相关
# =============================================================================

class UserLogin(BaseModel):
    """用户登录请求"""
    invite_code: str = Field(..., min_length=4, max_length=20)


class UserRegister(BaseModel):
    """用户注册请求"""
    invite_code: str = Field(..., min_length=4, max_length=20)
    username: str = Field(..., min_length=2, max_length=50)


class UserResponse(BaseSchema):
    """用户响应"""
    id: int
    username: str
    score: int
    total_score_earned: int
    total_score_lost: int
    highest_score: int
    lowest_score: int
    risk_preference: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserStatsResponse(BaseSchema):
    """用户统计响应"""
    total_sessions: int
    ai_sessions: int
    human_sessions: int
    honeypot_sessions: int
    total_guesses: int
    correct_guesses: int
    accuracy: float
    low_confidence_count: int
    mid_confidence_count: int
    high_confidence_count: int
    total_meta_conversations: int
    avg_meta_per_session: float
    max_meta_in_one_session: int
    accuracy_with_meta: Optional[float]
    accuracy_without_meta: Optional[float]
    mid_game_judgments: int
    mid_game_accuracy: float
    avg_turns: float
    min_turns: Optional[int]
    max_turns: Optional[int]
    total_chat_time: int
    avg_session_duration: float


# =============================================================================
# 会话相关
# =============================================================================

class SessionCreate(BaseModel):
    """创建会话请求"""
    opponent_type: str = Field(..., pattern="^(human|ai|honeypot)$")


class SessionResponse(BaseSchema):
    """会话响应"""
    id: int
    user_id: int
    opponent_type: str
    is_honeypot: bool
    triggered_mid_game: bool
    meta_conversation_count: int
    confidence_level: Optional[str]
    is_correct: Optional[bool]
    final_score: Optional[int]
    score_breakdown: Optional[dict]
    turn_count: int
    started_at: Optional[datetime]
    ended_at: Optional[datetime]


# =============================================================================
# 消息相关
# =============================================================================

class MessageCreate(BaseModel):
    """创建消息请求"""
    content: str = Field(..., min_length=1, max_length=500)


class MessageResponse(BaseSchema):
    """消息响应"""
    id: int
    session_id: int
    sender: str
    content: str
    is_meta_conversation: bool
    meta_keyword: Optional[str]
    created_at: datetime


# =============================================================================
# 问卷和判断相关
# =============================================================================

class SurveyRequest(BaseModel):
    """问卷请求"""
    user_guess: str = Field(..., pattern="^(human|ai)$")
    confidence_level: str = Field(..., pattern="^(low|mid|high)$")
    fluency_rating: int = Field(..., ge=1, le=5)
    reason: Optional[str] = Field(None, max_length=500)


class MidGameJudgmentRequest(BaseModel):
    """场中判断请求"""
    user_guess: str = Field(..., pattern="^(human|ai)$")


class GameResultResponse(BaseSchema):
    """游戏结果响应"""
    session_id: int
    opponent_type: str
    user_guess: str
    is_correct: bool
    final_score: int
    score_breakdown: dict


# =============================================================================
# 积分相关
# =============================================================================

class ScoreHistoryResponse(BaseSchema):
    """积分历史响应"""
    id: int
    user_id: int
    session_id: Optional[int]
    score_change: int
    score_before: int
    score_after: int
    reason: str
    created_at: datetime


# =============================================================================
# 匹配相关
# =============================================================================

class MatchResponse(BaseSchema):
    """匹配响应"""
    session_id: int
    opponent_type: str
    is_honeypot: bool


class MatchingStatusResponse(BaseSchema):
    """匹配状态响应"""
    in_queue: bool
    queue_position: Optional[int]
    estimated_wait_time: Optional[int]


# =============================================================================
# WebSocket 消息
# =============================================================================

class WSMessage(BaseModel):
    """WebSocket 消息基类"""
    type: str
    data: dict


class ChatMessage(WSMessage):
    """聊天消息"""
    type: str = "chat"
    data: dict = Field(..., description="包含 sender, content, timestamp")


class MatchFoundMessage(WSMessage):
    """匹配成功消息"""
    type: str = "match_found"
    data: dict = Field(..., description="匹配信息")


class TypingMessage(WSMessage):
    """打字提示消息"""
    type: str = "typing"
    data: dict = Field(..., description="包含 sender, is_typing")


class ErrorMessage(WSMessage):
    """错误消息"""
    type: str = "error"
    data: dict = Field(..., description="包含 error_code, message")


# =============================================================================
# 通用响应
# =============================================================================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str
    message: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    database_connected: bool
    bot_pool_size: int


# =============================================================================
# 邀请码相关
# =============================================================================

class InviteCodeResponse(BaseSchema):
    """邀请码响应"""
    id: int
    code: str
    is_active: bool
    is_used: bool
    max_uses: int
    current_uses: int
    used_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    batch_id: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InviteCodeStatsResponse(BaseSchema):
    """邀请码统计响应"""
    total: int
    active: int
    used: int
    expired: int
    disabled: int
    available: int
    batches: int
