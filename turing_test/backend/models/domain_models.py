"""
领域模型 - 三层分离架构 (全新表结构)

设计原则:
1. 匹配层 (Match) - 一次性事件记录
2. 对话层 (Room, RoomParticipant, Message) - 共享对话空间
3. 用户会话层 (UserSession) - 个人视角状态
4. 积分领域 (SessionScore, ScoreBreakdownItem) - 独立积分记录

注意：本文件只包含全新的表，不包含与现有模型重复的表
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
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from turing_test.backend.database import Base


# =============================================================================
# Bot 配置表 - Bot 元数据存储 (全新)
# =============================================================================

class BotConfig(Base):
    """
    Bot 配置元数据
    
    注意：仅存储元数据，实际规则在 YAML+Lua 文件中
    """
    
    __tablename__ = "bot_configs"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Bot 类型
    bot_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="normal/honeypot",
    )
    
    level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="lv1_newbie/lv2_typical/lv3_logic",
    )
    
    # 元数据 (YAML+Lua 文件路径/标识)
    script_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="YAML 脚本文件路径",
    )
    
    lua_module: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Lua 模块名",
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
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
    matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="bot_config",
        foreign_keys="Match.bot_config_id",
    )
    
    def __repr__(self) -> str:
        return f"<BotConfig(id={self.id}, name='{self.name}', level={self.level})>"


# =============================================================================
# 匹配层 - Match (全新)
# =============================================================================

class Match(Base):
    """
    匹配记录 - 记录用户请求匹配的事件
    
    状态机：pending → matched → (完成)
                   ↘ failed/cancelled/timeout
    """
    
    __tablename__ = "matches"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        comment="请求匹配的用户 ID",
    )
    
    room_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        unique=True,
        index=True,
        comment="匹配成功后创建的 Room ID",
    )
    
    # 匹配请求信息
    user_score_snapshot: Mapped[int] = mapped_column(
        Integer,
        comment="用户积分快照 (用于匹配算法)",
    )
    
    preferences: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="匹配偏好设置",
    )
    
    # 匹配结果
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True,
        comment="pending/matched/failed/cancelled/timeout",
    )
    
    opponent_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="对手类型：human/bot/honeypot",
    )
    
    matched_opponent_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="真人对手的用户 ID (仅 human 类型有值)",
    )
    
    bot_config_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("bot_configs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Bot 配置 ID (仅 bot/honeypot 类型有值)",
    )
    
    bot_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Bot 等级：lv1_newbie/lv2_typical/lv3_logic",
    )
    
    is_honeypot: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否钓鱼 Bot",
    )
    
    # 时间戳
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="请求匹配时间",
    )
    
    matched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="匹配成功时间",
    )
    
    expired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间",
    )
    
    # 关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="matches",
        foreign_keys="Match.user_id",
    )

    room: Mapped[Optional["Room"]] = relationship(
        "Room",
        back_populates="match",
        foreign_keys="Match.room_id",
        remote_side="Room.id",
    )

    matched_opponent: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys="Match.matched_opponent_id",
    )

    bot_config: Mapped[Optional["BotConfig"]] = relationship(
        "BotConfig",
        back_populates="matches",
        foreign_keys="Match.bot_config_id",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_matches_status_requested', 'status', 'requested_at'),
        Index('idx_matches_user_status', 'user_id', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<Match(id={self.id}, user_id={self.user_id}, status={self.status})>"


# =============================================================================
# 对话层 - Room (全新)
# =============================================================================

class Room(Base):
    """
    对话空间 - 多人共享的对话容器
    
    状态机：active → ended/timeout
    """
    
    __tablename__ = "rooms"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    match_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        comment="触发创建此 Room 的 Match ID",
    )
    
    # 对话类型
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="human_vs_bot/human_vs_human/honeypot",
    )
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        index=True,
        comment="active/ended/timeout",
    )
    
    end_reason: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="user_normal_end/user_gave_up/sys_timeout/sys_error",
    )
    
    # 对话统计
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    meta_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 第一个离开的用户 ID (真人对战时使用)
    first_leaver_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="真人对战时先离开一方的用户 ID",
    )
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="第一条消息发送时间",
    )
    
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    
    # 关系
    match: Mapped[Optional["Match"]] = relationship(
        "Match",
        foreign_keys="Room.match_id",
        remote_side="Match.id",
        viewonly=True,
    )
    
    participants: Mapped[List["RoomParticipant"]] = relationship(
        "RoomParticipant",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    user_sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="room",
        cascade="all, delete-orphan",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_rooms_status_created', 'status', 'created_at'),
        Index('idx_rooms_type_status', 'type', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<Room(id={self.id}, type={self.type}, status={self.status})>"


class RoomParticipant(Base):
    """
    对话参与者 - 关联用户和 Room (全新)
    """
    
    __tablename__ = "room_participants"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        index=True,
    )
    
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="用户 ID (Bot 参与者为 NULL)",
    )
    
    bot_config_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("bot_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # 角色
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user/opponent/bot",
    )
    
    # Bot 信息
    bot_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_honeypot: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 时间
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    
    left_reason: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="ended/timeout/gave_up",
    )
    
    # 关系
    room: Mapped["Room"] = relationship(
        "Room",
        back_populates="participants",
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="room_participations",
    )
    
    bot_config: Mapped[Optional["BotConfig"]] = relationship(
        "BotConfig",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_participants_room_user', 'room_id', 'user_id', unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<RoomParticipant(room_id={self.room_id}, user_id={self.user_id}, role={self.role})>"


# =============================================================================
# 消息表 - Message (全新，关联 Room 而非 Session)
# =============================================================================

class Message(Base):
    """
    消息 - 属于 Room，不属于特定用户
    
    这是新消息表，关联 room_id 而非 session_id
    """
    
    __tablename__ = "messages"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        index=True,
    )
    
    sender_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="发送者用户 ID (Bot 消息为 NULL)",
    )
    
    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user/bot",
    )
    
    # 内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 元对话标记
    is_meta: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    meta_keyword: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="触发的元对话关键词",
    )
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    
    # 关系
    room: Mapped["Room"] = relationship(
        "Room",
        back_populates="messages",
    )
    
    sender: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="messages",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_messages_room_created', 'room_id', 'created_at'),
        Index('idx_messages_room_sender', 'room_id', 'sender_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, room_id={self.room_id}, sender={self.sender_id})>"


# =============================================================================
# 用户会话层 - UserSession (全新)
# =============================================================================

class UserSession(Base):
    """
    用户会话 - 每个用户在每个 Room 中的独立状态
    
    状态机：active → ended/timeout
    """
    
    __tablename__ = "user_sessions"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        index=True,
    )
    
    match_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    
    # 回合状态 (个人视角)
    user_turn_count: Mapped[int] = mapped_column(Integer, default=0)
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    is_user_turn: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 判断 (个人视角)
    user_guess: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="human/ai",
    )
    
    confidence: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="low/mid/high",
    )
    
    is_mid_game: Mapped[bool] = mapped_column(Boolean, default=False)
    
    judgment_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    
    # 积分 (个人视角)
    final_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    score_settled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 对方猜错奖励
    bonus_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    bonus_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    bonus_claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        index=True,
        comment="active/ended/timeout/error",
    )
    
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    end_reason: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    last_message_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="最后一条消息 ID",
    )

    # 关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_sessions",
        foreign_keys="UserSession.user_id",
    )
    
    room: Mapped["Room"] = relationship(
        "Room",
        back_populates="user_sessions",
    )
    
    match: Mapped[Optional["Match"]] = relationship(
        "Match",
        foreign_keys="UserSession.match_id",
    )
    
    score: Mapped[Optional["SessionScore"]] = relationship(
        "SessionScore",
        back_populates="user_session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_user_sessions_user_room', 'user_id', 'room_id', unique=True),
        Index('idx_user_sessions_status_user', 'status', 'user_id'),
        Index('idx_user_sessions_room_user', 'room_id', 'user_id'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<UserSession(id={self.id}, user_id={self.user_id}, "
            f"room_id={self.room_id}, status={self.status})>"
        )


# =============================================================================
# 积分领域 - SessionScore (全新)
# =============================================================================

class SessionScore(Base):
    """
    会话积分 - 记录每次会话的积分结算
    
    与 UserSession 1:1 关联，但分离存储以便扩展
    """
    
    __tablename__ = "session_scores"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    user_session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        index=True,
    )
    
    # 积分构成
    base_score: Mapped[int] = mapped_column(Integer, default=0)
    confidence_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    meta_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    mid_game_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    entry_fee: Mapped[int] = mapped_column(Integer, default=2)
    turn_penalty: Mapped[int] = mapped_column(Integer, default=0)
    opponent_bonus: Mapped[int] = mapped_column(Integer, default=0)
    
    # 最终得分
    final_score: Mapped[int] = mapped_column(Integer)
    
    # 结算状态
    base_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    base_settled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    bonus_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    bonus_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    bonus_claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 对手判断信息
    opponent_guess: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    
    opponent_confidence: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    
    opponent_is_correct: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
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
    user_session: Mapped["UserSession"] = relationship(
        "UserSession",
        back_populates="score",
        foreign_keys="SessionScore.user_session_id",
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="session_scores",
    )
    
    room: Mapped["Room"] = relationship("Room")
    
    breakdown_items: Mapped[List["ScoreBreakdownItem"]] = relationship(
        "ScoreBreakdownItem",
        back_populates="session_score",
        cascade="all, delete-orphan",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_session_scores_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<SessionScore(id={self.id}, user_id={self.user_id}, score={self.final_score})>"


class ScoreBreakdownItem(Base):
    """
    积分明细分项 - 替代 JSON 存储 (全新)
    """
    
    __tablename__ = "score_breakdown_items"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 外键
    session_score_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("session_scores.id", ondelete="CASCADE"),
        index=True,
    )
    
    # 分项信息
    item_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="base/confidence/meta/mid_game/entry/penalty/bonus",
    )
    
    item_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="人类可读名称",
    )
    
    multiplier: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="倍率项的倍率值",
    )
    
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="金额 (正数表示增加，负数表示减少)",
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    
    # 关系
    session_score: Mapped["SessionScore"] = relationship(
        "SessionScore",
        back_populates="breakdown_items",
    )
    
    # 索引
    __table_args__ = (
        Index('idx_breakdown_score_type', 'session_score_id', 'item_type'),
    )
    
    def __repr__(self) -> str:
        return f"<ScoreBreakdownItem(id={self.id}, type={self.item_type}, amount={self.amount})>"
