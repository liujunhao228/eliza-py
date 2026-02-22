from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from turing_test.backend.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"
    
    code = Column(String, primary_key=True, index=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="invite_code_ref")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    invite_code = Column(String, ForeignKey("invite_codes.code"))
    nickname = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    invite_code_ref = relationship("InviteCode", back_populates="user")
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    opponent_type = Column(String)  # 'human' or 'ai'
    opponent_id = Column(Integer, nullable=True)  # NULL if AI
    status = Column(String, default="matching")  # matching, active, completed
    match_duration = Column(Integer, nullable=True)  # 匹配用时（秒）
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    survey_result = relationship("SurveyResult", back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL if AI
    is_ai = Column(Boolean, default=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")
    sender = relationship("User", backref="sent_messages")


class SurveyResult(Base):
    __tablename__ = "survey_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    user_guess = Column(String)  # 'human', 'ai', 'unsure'
    fluency_rating = Column(Integer)  # 1-5
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="survey_result")
    opponent_guess = Column(String, nullable=True)  # 对方的判断（真人模式彩蛋）
    opponent_reason = Column(Text, nullable=True)  # 对方的判断理由
