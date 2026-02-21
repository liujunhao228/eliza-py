from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# 邀请码相关
class InviteCodeLogin(BaseModel):
    code: str


class InviteCodeResponse(BaseModel):
    code: str
    is_used: bool


# 用户相关
class UserLogin(BaseModel):
    code: str
    nickname: str


class UserResponse(BaseModel):
    id: int
    nickname: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# 会话相关
class SessionResponse(BaseModel):
    id: int
    opponent_type: str
    status: str
    started_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# 消息相关
class MessageSend(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    session_id: int
    sender_id: Optional[int] = None
    is_ai: bool
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# 问卷相关
class SurveySubmit(BaseModel):
    session_id: int
    user_guess: str  # 'human', 'ai', 'unsure'
    fluency_rating: int  # 1-5
    reason: Optional[str] = None


class SurveyResponse(BaseModel):
    id: int
    session_id: int
    user_guess: str
    fluency_rating: int
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True


# 匹配相关
class MatchRequest(BaseModel):
    user_id: int


class MatchStatus(BaseModel):
    status: str  # 'matching', 'found', 'timeout'
    session_id: Optional[int] = None
    opponent_type: Optional[str] = None
