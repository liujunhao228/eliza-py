"""
Pydantic Schemas

定义 API 请求和响应的数据模型。
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


# =============================================================================
# 基础模型
# =============================================================================

class BaseSchema(BaseModel):
    """所有 Schema 的基类"""

    model_config = ConfigDict(from_attributes=True)  # 允许从 ORM 对象创建


# =============================================================================
# 用户相关
# =============================================================================

class UserLogin(BaseModel):
    """用户登录/注册请求"""
    nickname: Optional[str] = Field(None, min_length=2, max_length=50, description="昵称（注册模式需要）")
    username: Optional[str] = Field(None, min_length=2, max_length=50, description="用户名（登录模式需要）")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    invite_code: Optional[str] = Field(None, min_length=4, max_length=20, description="邀请码（新用户注册时必需）")


class UserRegister(BaseModel):
    """用户注册请求"""
    invite_code: str = Field(..., min_length=4, max_length=20, description="邀请码")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")
    password: str = Field(..., min_length=8, max_length=128, description="密码")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        验证密码强度

        要求:
        - 长度 >= 8
        - 包含大写字母
        - 包含小写字母
        - 包含数字
        """
        if len(v) < 8:
            raise ValueError("密码长度至少 8 位")
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含数字")
        return v


class UserResponse(BaseSchema):
    """用户响应"""
    id: int
    nickname: str
    score: int
    total_score_earned: int
    total_score_lost: int
    highest_score: int
    lowest_score: int
    risk_preference: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserLoginResponse(BaseSchema):
    """用户登录响应（包含 token）"""
    id: int
    nickname: str
    score: int
    invite_code: str
    access_token: str
    token_type: str = "bearer"


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
    session_id: int
    user_guess: Optional[str] = Field(None, pattern="^(human|ai|unsure)$")  # 场中判断后无需传递
    confidence_level: Optional[str] = Field(None, pattern="^(low|mid|high)$")  # 场中判断后无需传递
    fluency_rating: int = Field(..., ge=1, le=5)
    reason: Optional[str] = Field(None, max_length=1000)
    self_role: str = Field(..., pattern="^(prover|interferer|other)$")
    strategy: Optional[str] = Field(None, max_length=1000)


class SurveyResponse(BaseSchema):
    """问卷响应"""
    session_id: int
    user_guess: str
    confidence_level: str
    fluency_rating: int
    reason: Optional[str]
    self_role: str
    strategy: Optional[str]


class ScoreBreakdownResponse(BaseModel):
    """积分明细响应 - 简化版，不暴露计算细节"""
    final_score: int
    is_correct: bool
    # 对方猜错奖励字段
    opponent_guess: Optional[str] = None
    opponent_confidence: Optional[str] = None
    opponent_is_correct: Optional[bool] = None
    opponent_score_if_correct: Optional[int] = None
    bonus_from_opponent_wrong: Optional[int] = None


class GameResultResponse(BaseSchema):
    """游戏结果响应"""
    session_id: int
    opponent_type: str
    user_guess: str
    is_correct: bool
    final_score: int
    score_breakdown: ScoreBreakdownResponse
    survey: Optional[SurveyResponse] = None


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
    # 对方猜错奖励字段
    bonus_from_opponent: Optional[int] = None
    opponent_guess: Optional[str] = None
    opponent_confidence: Optional[str] = None
    opponent_is_correct: Optional[bool] = None


# =============================================================================
# 匹配相关
# =============================================================================

class MatchResponse(BaseSchema):
    """
    匹配响应 - 安全版本
    
    ⚠️ 仅包含安全字段，前端无法得知对手真实身份
    """
    session_id: int
    opponent_type: str = "opponent"  # 统一返回 "opponent"，不泄露
    match_duration_ms: int = 0       # 匹配耗时 (前端用于模拟延迟)
    message: str = "匹配成功"


class AdminMatchResponse(BaseSchema):
    """
    管理员匹配响应 - 完整版本
    
    ✅ 包含完整信息，仅管理员可访问
    """
    session_id: int
    opponent_type: str
    true_identity: Optional[str] = None    # 真实身份 (仅管理员可见)
    bot_level: Optional[str] = None        # Bot 等级 (仅管理员可见)
    is_honeypot: bool = False              # 是否钓鱼 (仅管理员可见)
    opponent_user_id: Optional[int] = None
    match_duration_ms: int = 0
    message: str = "匹配成功"


class MatchingStatusResponse(BaseSchema):
    """匹配状态响应"""
    waiting_count: int = 0
    estimated_wait_time: Optional[int] = None


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


# =============================================================================
# 历史会话相关
# =============================================================================

class SessionListItem(BaseSchema):
    """会话列表项"""
    id: int
    opponent_type: str
    turn_count: int
    final_score: Optional[int]
    is_correct: Optional[bool]
    confidence_level: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    has_share: bool


class SessionListResponse(BaseSchema):
    """会话列表响应（分页）"""
    items: List[SessionListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class SessionDetailResponse(BaseSchema):
    """会话详情响应"""
    id: int
    opponent_type: str
    is_honeypot: bool
    turn_count: int
    meta_conversation_count: int
    final_score: Optional[int]
    is_correct: Optional[bool]
    confidence_level: Optional[str]
    score_breakdown: Optional[dict]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]


# =============================================================================
# 分享会话相关
# =============================================================================

class CreateShareRequest(BaseModel):
    """创建分享请求"""
    is_public: bool = True
    expires_days: Optional[int] = None
    password: Optional[str] = None


class CreateShareResponse(BaseSchema):
    """创建分享响应"""
    share_id: int
    share_token: str
    share_url: str
    expires_at: Optional[datetime]
    has_password: bool


class ShareInfoResponse(BaseSchema):
    """分享信息响应（公开访问）"""
    session_id: int
    opponent_type: str
    turn_count: int
    final_score: Optional[int]
    is_correct: Optional[bool]
    started_at: datetime
    ended_at: Optional[datetime]
    view_count: int
    is_expired: bool
    requires_password: bool


class SharedMessagesResponse(BaseSchema):
    """分享会话消息响应"""
    session_id: int
    opponent_type: str
    messages: List[MessageResponse]


class UpdateShareRequest(BaseModel):
    """更新分享请求"""
    is_public: Optional[bool] = None
    expires_days: Optional[int] = None
    password: Optional[str] = None


class VerifyPasswordRequest(BaseModel):
    """验证密码请求"""
    password: str = Field(..., min_length=1)


class VerifyPasswordResponse(BaseModel):
    """验证密码响应"""
    success: bool
    message: str
    access_token: Optional[str] = None
