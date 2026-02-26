"""
SQLAlchemy 模型

定义数据库表结构。
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from turing_test.backend.database import Base


# =============================================================================
# 用户表
# =============================================================================

class User(Base):
    """用户表"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    # 积分字段
    score: Mapped[int] = mapped_column(Integer, default=100, index=True)
    total_score_earned: Mapped[int] = mapped_column(Integer, default=0)
    total_score_lost: Mapped[int] = mapped_column(Integer, default=0)
    highest_score: Mapped[int] = mapped_column(Integer, default=100)
    lowest_score: Mapped[int] = mapped_column(Integer, default=100)
    risk_preference: Mapped[str] = mapped_column(
        String(20),
        default="moderate",
        comment="风险偏好分类"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 关系
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    score_history: Mapped[list["ScoreHistory"]] = relationship(
        "ScoreHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    stats: Mapped[Optional["UserStats"]] = relationship(
        "UserStats",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    surveys: Mapped[list["Survey"]] = relationship(
        "Survey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    shared_sessions: Mapped[list["SessionShare"]] = relationship(
        "SessionShare",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', score={self.score})>"


# =============================================================================
# 会话表
# =============================================================================

class Session(Base):
    """游戏会话表"""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # 会话类型
    opponent_type: Mapped[str] = mapped_column(
        String(20),
        index=True,
        comment="'human', 'ai', 'honeypot'"
    )

    # 博弈字段
    is_honeypot: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )
    triggered_mid_game: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    meta_conversation_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )
    confidence_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="'low', 'mid', 'high'"
    )
    is_correct: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="判断是否正确"
    )

    # 积分字段
    final_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    score_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="积分明细 JSON"
    )

    # 聊天统计
    turn_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 结束原因
    end_reason: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="结束原因：'normal_end', 'user_gave_up', 'mid_game_judgment', 'timeout'"
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    survey: Mapped[Optional["Survey"]] = relationship(
        "Survey",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    shares: Mapped[list["SessionShare"]] = relationship(
        "SessionShare",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Session(id={self.id}, user_id={self.user_id}, "
            f"opponent_type='{self.opponent_type}')>"
        )


# =============================================================================
# 消息表
# =============================================================================

class Message(Base):
    """聊天消息表"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    # 消息内容
    sender: Mapped[str] = mapped_column(
        String(20),
        index=True,
        comment="'user' 或 'opponent'"
    )
    content: Mapped[str] = mapped_column(Text)

    # 元对话标记
    is_meta_conversation: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )
    meta_keyword: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # 关系
    session: Mapped["Session"] = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, session_id={self.session_id}, "
            f"sender='{self.sender}')>"
        )


# =============================================================================
# 积分历史表
# =============================================================================

class ScoreHistory(Base):
    """积分历史记录表"""

    __tablename__ = "score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 积分变化
    score_change: Mapped[int] = mapped_column(
        Integer,
        comment="正数表示增加，负数表示减少"
    )
    score_before: Mapped[int] = mapped_column(Integer)
    score_after: Mapped[int] = mapped_column(Integer)

    # 原因
    reason: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="'session_end', 'daily_bonus', 'relief' 等"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="score_history")

    def __repr__(self) -> str:
        return (
            f"<ScoreHistory(id={self.id}, user_id={self.user_id}, "
            f"score_change={self.score_change})>"
        )


# =============================================================================
# 用户统计表
# =============================================================================

class UserStats(Base):
    """用户统计数据表"""

    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # 对话统计
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    ai_sessions: Mapped[int] = mapped_column(Integer, default=0)
    human_sessions: Mapped[int] = mapped_column(Integer, default=0)
    honeypot_sessions: Mapped[int] = mapped_column(Integer, default=0)

    # 判断准确率
    total_guesses: Mapped[int] = mapped_column(Integer, default=0)
    correct_guesses: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Integer, default=0)

    # 信心等级统计
    low_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    mid_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    high_confidence_count: Mapped[int] = mapped_column(Integer, default=0)

    # 元对话统计
    total_meta_conversations: Mapped[int] = mapped_column(Integer, default=0)
    avg_meta_per_session: Mapped[float] = mapped_column(Integer, default=0.0)
    max_meta_in_one_session: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_with_meta: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    accuracy_without_meta: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)

    # 场中判断统计
    mid_game_judgments: Mapped[int] = mapped_column(Integer, default=0)
    mid_game_accuracy: Mapped[float] = mapped_column(Integer, default=0.0)

    # 轮数统计
    avg_turns: Mapped[float] = mapped_column(Integer, default=0.0)
    min_turns: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_turns: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 时间统计
    total_chat_time: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="总聊天时间（秒）"
    )
    avg_session_duration: Mapped[float] = mapped_column(
        Integer,
        default=0.0,
        comment="平均会话时长（秒）"
    )

    # 时间戳
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="stats")

    def __repr__(self) -> str:
        return f"<UserStats(id={self.id}, user_id={self.user_id})>"


# =============================================================================
# 问卷表
# =============================================================================

class Survey(Base):
    """用户问卷记录表"""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="关联的会话 ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # 身份判断
    user_guess: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="'human' | 'ai' | 'unsure'"
    )
    confidence_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="'low' | 'mid' | 'high'"
    )

    # 评分
    fluency_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="流畅度评分 1-5"
    )

    # 开放式问题
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="判断理由"
    )
    self_role: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="'prover' | 'interferer' | 'other'"
    )
    strategy: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="策略描述"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # 关系
    session: Mapped["Session"] = relationship("Session", back_populates="survey")
    user: Mapped["User"] = relationship("User", back_populates="surveys")

    def __repr__(self) -> str:
        return (
            f"<Survey(id={self.id}, session_id={self.session_id}, "
            f"user_guess='{self.user_guess}')>"
        )


# =============================================================================
# 邀请码表
# =============================================================================

class InviteCode(Base):
    """邀请码表"""

    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    # 邀请码状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        comment="邀请码是否可用"
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="是否已被使用"
    )

    # 使用信息
    used_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 邀请码元数据
    batch_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="生成批次 ID"
    )
    max_uses: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="最大使用次数，-1 表示无限"
    )
    current_uses: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="当前已使用次数"
    )
    expire_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间"
    )

    # 备注
    note: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 关系
    used_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="invite_code_usage",
    )

    def __repr__(self) -> str:
        return (
            f"<InviteCode(id={self.id}, code='{self.code}', "
            f"is_active={self.is_active}, is_used={self.is_used})>"
        )


# =============================================================================
# 会话分享表
# =============================================================================

class SessionShare(Base):
    """会话分享表"""

    __tablename__ = "session_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # 分享令牌
    share_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )

    # 分享设置
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否公开分享"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间"
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="访问密码哈希"
    )

    # 访问统计
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 关系
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="shares",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="shared_sessions",
    )
    access_logs: Mapped[List["SessionShareAccess"]] = relationship(
        "SessionShareAccess",
        back_populates="share",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SessionShare(id={self.id}, session_id={self.session_id}, "
            f"token={self.share_token})>"
        )


# =============================================================================
# 会话分享访问日志表
# =============================================================================

class SessionShareAccess(Base):
    """会话分享访问日志表"""

    __tablename__ = "session_share_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    share_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("session_shares.id", ondelete="CASCADE"),
        index=True,
        comment="分享 ID"
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        comment="访问者 IP 地址"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="User-Agent"
    )
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="访问时间"
    )

    # 关系
    share: Mapped["SessionShare"] = relationship(
        "SessionShare",
        back_populates="access_logs",
    )

    def __repr__(self) -> str:
        return f"<SessionShareAccess(id={self.id}, share_id={self.share_id}, ip={self.ip_address})>"


# =============================================================================
# 更新用户表关系
# =============================================================================

# 添加邀请码使用关系到 User 模型
User.invite_code_usage: Mapped[Optional["InviteCode"]] = relationship(
    "InviteCode",
    back_populates="used_by_user",
    uselist=False,
    foreign_keys=[InviteCode.used_by_user_id],
)


# =============================================================================
# 索引定义
# =============================================================================

Index("idx_sessions_user_started", Session.user_id, Session.started_at)
Index("idx_messages_session_created", Message.session_id, Message.created_at)
Index("idx_score_history_user_created", ScoreHistory.user_id, ScoreHistory.created_at)
