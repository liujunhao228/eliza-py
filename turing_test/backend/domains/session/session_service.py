"""
会话领域 - 统一状态管理

设计原则:
1. 单一状态源 - Session 聚合根是唯一的状态来源
2. 事件溯源 - 所有状态变更通过事件记录
3. 内存 + 持久化双层设计 - 热数据在内存，冷数据在数据库
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from contextlib import asynccontextmanager
import uuid

from turing_test.backend.infrastructure.events.event_bus import (
    EventBus, EventType, EventBuilder, event_bus,
)
from turing_test.backend.infrastructure.cqrs.cqrs import (
    Command, CommandHandler, CommandResult,
    Query, QueryHandler,
    CreateSessionCommand, EndSessionCommand,
    GetSessionQuery, GetUserSessionsQuery,
)

logger = logging.getLogger(__name__)


# ============== 会话领域模型 ==============


class SessionStatus(Enum):
    """会话状态"""
    CREATING = "creating"           # 创建中
    ACTIVE = "active"               # 活跃 (对话中)
    WAITING_OPPONENT = "waiting_opponent"  # 等待对方 (对方先离开)
    ENDED = "ended"                 # 已结束
    TIMEOUT = "timeout"             # 超时
    ERROR = "error"                 # 错误状态


class EndReason(Enum):
    """结束原因"""
    USER_REQUESTED = "user_requested"
    OPPONENT_LEFT = "opponent_left"
    TIMEOUT = "timeout"
    SYSTEM_ERROR = "system_error"
    ADMIN_FORCE_END = "admin_force_end"


@dataclass
class SessionState:
    """
    会话运行时状态 - 内存缓存层
    
    注意：这不是状态源，只是数据库状态的缓存
    所有写操作必须同步到数据库
    """
    session_id: int
    user_id: int
    opponent_id: Optional[int]
    status: SessionStatus = SessionStatus.CREATING
    turn_count: int = 0
    is_user_turn: bool = True
    meta_count: int = 0
    is_honeypot: bool = False
    opponent_type: str = "ai"
    
    # 对方猜错奖励暂存
    opponent_guess: Optional[str] = None
    opponent_confidence: Optional[str] = None
    
    # 并发控制
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _processing: bool = False
    
    def next_turn(self) -> Tuple[int, bool]:
        """切换到下一回合"""
        self.turn_count += 1
        self.is_user_turn = not self.is_user_turn
        return (self.turn_count, self.is_user_turn)
    
    def increment_meta(self) -> int:
        """增加元对话计数"""
        self.meta_count += 1
        return self.meta_count
    
    @asynccontextmanager
    async def acquire_lock(self, timeout: float = 10.0):
        """获取会话锁"""
        try:
            acquired = await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            if acquired:
                self._processing = True
                try:
                    yield
                finally:
                    self._processing = False
                    self._lock.release()
            else:
                raise TimeoutError(f"Failed to acquire session lock within {timeout}s")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Failed to acquire session lock within {timeout}s")


@dataclass
class Session:
    """
    会话聚合根 - 状态源
    
    不变量:
    1. 会话创建时必须包含用户 ID 和对手类型
    2. 只有 ACTIVE 状态可以接收消息
    3. 一旦进入终端状态，不能再改变
    """
    id: int
    user_id: int
    opponent_id: Optional[int]
    opponent_type: str  # "human", "bot", "honeypot"
    is_honeypot: bool = False
    status: SessionStatus = SessionStatus.CREATING
    turn_count: int = 0
    meta_count: int = 0
    opening_message_sent: bool = False
    
    # 积分相关
    base_score_settled: bool = False
    pending_opponent_bonus: bool = False
    opponent_guess: Optional[str] = None
    opponent_confidence: Optional[str] = None
    final_score: Optional[float] = None
    
    # 结束相关
    end_reason: Optional[str] = None
    ended_at: Optional[datetime] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # 领域行为
    def activate(self):
        """激活会话 (创建完成)"""
        self._check_can_modify()
        self.status = SessionStatus.ACTIVE
        self._touch()
    
    def start_message_processing(self):
        """开始消息处理 (发送开场白后)"""
        self._check_can_modify()
        if self.status != SessionStatus.ACTIVE:
            raise ValueError(f"Cannot start processing in status {self.status}")
        self.opening_message_sent = True
        self._touch()
    
    def next_turn(self) -> Tuple[int, bool]:
        """切换到下一回合"""
        self._check_can_modify()
        self.turn_count += 1
        is_user_turn = (self.turn_count % 2 == 1)
        self._touch()
        return (self.turn_count, is_user_turn)
    
    def increment_meta(self) -> int:
        """增加元对话计数"""
        self._check_can_modify()
        self.meta_count += 1
        self._touch()
        return self.meta_count
    
    def end(self, reason: EndReason, final_turn: Optional[int] = None):
        """结束会话"""
        self._check_can_modify()
        self.status = SessionStatus.ENDED
        self.end_reason = reason.value
        self.ended_at = datetime.utcnow()
        if final_turn:
            self.turn_count = final_turn
        self._touch()
    
    def mark_waiting_opponent(self):
        """标记为等待对方"""
        self._check_can_modify()
        self.status = SessionStatus.WAITING_OPPONENT
        self._touch()
    
    def set_opponent_guess(self, guess: str, confidence: str):
        """设置对方的判断 (用于计算奖励)"""
        self._check_can_modify()
        self.opponent_guess = guess
        self.opponent_confidence = confidence
        self._touch()
    
    def settle_base_score(self):
        """标记基础积分已结算"""
        self._check_can_modify()
        self.base_score_settled = True
        self._touch()
    
    def claim_opponent_bonus(self):
        """领取对方猜错奖励"""
        self._check_can_modify()
        self.pending_opponent_bonus = False
        self._touch()
    
    def is_terminal(self) -> bool:
        """是否是终端状态"""
        return self.status in {
            SessionStatus.ENDED,
            SessionStatus.TIMEOUT,
        }
    
    def can_receive_message(self) -> bool:
        """是否可以接收消息"""
        return self.status == SessionStatus.ACTIVE and self.opening_message_sent
    
    def _check_can_modify(self):
        """检查是否可以修改"""
        if self.is_terminal():
            raise ValueError(f"Cannot modify session in terminal status {self.status}")
    
    def _touch(self):
        """更新时间戳"""
        self.updated_at = datetime.utcnow()


# ============== 会话仓库接口 ==============


class SessionRepository:
    """会话仓库接口"""
    
    async def get_by_id(self, session_id: int) -> Optional[Session]:
        """获取会话"""
        raise NotImplementedError
    
    async def get_by_user_id(self, user_id: int, active_only: bool = True) -> List[Session]:
        """获取用户的会话"""
        raise NotImplementedError
    
    async def get_active_by_user_id(self, user_id: int) -> Optional[Session]:
        """获取用户活跃的会话"""
        raise NotImplementedError
    
    async def save(self, session: Session):
        """保存会话"""
        raise NotImplementedError
    
    async def create(self, session: Session) -> Session:
        """创建会话"""
        raise NotImplementedError


# ============== 会话管理器 ==============


class SessionManager:
    """
    会话管理器 - 内存状态管理
    
    职责:
    1. 维护活跃会话的内存缓存
    2. 提供并发安全的会话访问
    3. 同步状态到数据库
    """
    
    def __init__(self, repository: SessionRepository, event_bus: EventBus):
        self._repository = repository
        self._event_bus = event_bus
        self._states: Dict[int, SessionState] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
        self._user_sessions: Dict[int, Set[int]] = {}  # user_id -> session_ids
    
    async def load_session(self, session_id: int) -> Optional[SessionState]:
        """加载会话到内存"""
        session = await self._repository.get_by_id(session_id)
        if not session:
            return None
        
        state = SessionState(
            session_id=session.id,
            user_id=session.user_id,
            opponent_id=session.opponent_id,
            status=session.status,
            turn_count=session.turn_count,
            is_user_turn=(session.turn_count % 2 == 1),
            meta_count=session.meta_count,
            is_honeypot=session.is_honeypot,
            opponent_type=session.opponent_type,
            opponent_guess=session.opponent_guess,
            opponent_confidence=session.opponent_confidence,
        )
        
        self._states[session_id] = state
        if session.user_id not in self._user_sessions:
            self._user_sessions[session.user_id] = set()
        self._user_sessions[session.user_id].add(session_id)
        
        return state
    
    async def get_state(self, session_id: int) -> Optional[SessionState]:
        """获取会话状态"""
        if session_id not in self._states:
            return await self.load_session(session_id)
        return self._states.get(session_id)
    
    @asynccontextmanager
    async def session_lock(self, session_id: int, timeout: float = 10.0):
        """会话锁"""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        
        lock = self._locks[session_id]
        try:
            acquired = await asyncio.wait_for(lock.acquire(), timeout=timeout)
            if acquired:
                try:
                    yield
                finally:
                    lock.release()
            else:
                raise TimeoutError(f"Failed to acquire lock for session {session_id}")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Failed to acquire lock for session {session_id}")
    
    async def sync_to_db(self, session_id: int, state: SessionState):
        """同步状态到数据库"""
        session = await self._repository.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # 更新会话
        session.status = state.status
        session.turn_count = state.turn_count
        session.meta_count = state.meta_count
        session.opponent_guess = state.opponent_guess
        session.opponent_confidence = state.opponent_confidence
        
        await self._repository.save(session)
    
    async def cleanup(self, session_id: int):
        """清理会话缓存"""
        if session_id in self._states:
            state = self._states[session_id]
            if state.user_id in self._user_sessions:
                self._user_sessions[state.user_id].discard(session_id)
            del self._states[session_id]
        if session_id in self._locks:
            del self._locks[session_id]


# ============== 命令处理器 ==============


class CreateSessionHandler(CommandHandler[Session]):
    """创建会话命令处理器"""
    
    def __init__(
        self,
        repository: SessionRepository,
        event_bus: EventBus,
    ):
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: CreateSessionCommand) -> CommandResult[Session]:
        try:
            # 发布创建中事件
            await EventBuilder(EventType.SESSION_CREATING)\
                .aggregate(str(command.user_id), "user")\
                .with_data(opponent_type=command.opponent_type)\
                .publish(self._event_bus)
            
            # 创建会话
            session = Session(
                id=0,  # 由数据库生成
                user_id=command.user_id,
                opponent_id=command.opponent_id,
                opponent_type=command.opponent_type,
                is_honeypot=command.is_honeypot,
                status=SessionStatus.CREATING,
            )
            
            created = await self._repository.create(session)
            
            # 发布创建成功事件
            await EventBuilder(EventType.SESSION_CREATED)\
                .aggregate(str(created.id), "session")\
                .with_data(
                    user_id=created.user_id,
                    opponent_type=created.opponent_type,
                    is_honeypot=created.is_honeypot,
                )\
                .publish(self._event_bus)
            
            return CommandResult.ok(data=created)
            
        except Exception as e:
            logger.exception(f"Failed to create session: {e}")
            return CommandResult.fail(str(e), "CREATE_ERROR")


class EndSessionHandler(CommandHandler[bool]):
    """结束会话命令处理器"""
    
    def __init__(self, repository: SessionRepository, event_bus: EventBus):
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: EndSessionCommand) -> CommandResult[bool]:
        try:
            session = await self._repository.get_by_id(command.session_id)
            
            if not session:
                return CommandResult.fail("Session not found", "NOT_FOUND")
            
            if session.is_terminal():
                return CommandResult.fail(f"Session already ended: {session.status}", "ALREADY_ENDED")
            
            # 结束会话
            session.end(EndReason(command.end_reason), command.final_turn)
            await self._repository.save(session)
            
            # 发布结束事件
            await EventBuilder(EventType.SESSION_ENDED)\
                .aggregate(str(command.session_id), "session")\
                .with_data(
                    end_reason=command.end_reason,
                    final_turn=command.final_turn or session.turn_count,
                )\
                .publish(self._event_bus)
            
            return CommandResult.ok(data=True)
            
        except Exception as e:
            logger.exception(f"Failed to end session: {e}")
            return CommandResult.fail(str(e), "END_ERROR")


# ============== 查询处理器 ==============


@dataclass
class SessionDTO:
    """会话 DTO"""
    id: int
    user_id: int
    opponent_type: str
    status: str
    turn_count: int
    meta_count: int
    is_honeypot: bool
    created_at: datetime
    ended_at: Optional[datetime] = None
    end_reason: Optional[str] = None
    final_score: Optional[float] = None


class GetSessionHandler(QueryHandler[Optional[SessionDTO]]):
    """获取会话查询处理器"""
    
    def __init__(self, repository: SessionRepository):
        self._repository = repository
    
    async def handle(self, query: GetSessionQuery) -> Optional[SessionDTO]:
        session = await self._repository.get_by_id(query.session_id)
        
        if not session:
            return None
        
        return SessionDTO(
            id=session.id,
            user_id=session.user_id,
            opponent_type=session.opponent_type,
            status=session.status.value,
            turn_count=session.turn_count,
            meta_count=session.meta_count,
            is_honeypot=session.is_honeypot,
            created_at=session.created_at,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            final_score=session.final_score,
        )


class GetUserSessionsHandler(QueryHandler[List[SessionDTO]]):
    """获取用户会话列表查询处理器"""
    
    def __init__(self, repository: SessionRepository):
        self._repository = repository
    
    async def handle(self, query: GetUserSessionsQuery) -> List[SessionDTO]:
        sessions = await self._repository.get_by_user_id(
            query.user_id,
            active_only=False,
        )
        
        # 分页
        sessions = sessions[query.offset:query.offset + query.limit]
        
        return [
            SessionDTO(
                id=s.id,
                user_id=s.user_id,
                opponent_type=s.opponent_type,
                status=s.status.value,
                turn_count=s.turn_count,
                meta_count=s.meta_count,
                is_honeypot=s.is_honeypot,
                created_at=s.created_at,
                ended_at=s.ended_at,
                end_reason=s.end_reason,
                final_score=s.final_score,
            )
            for s in sessions
        ]
