"""
匹配领域 - CQRS 实现

包含:
- 匹配命令处理器
- 匹配查询处理器
- 匹配聚合根
- 匹配事件
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from turing_test.backend.infrastructure.cqrs.cqrs import (
    Command, CommandHandler, CommandResult, CommandBus,
    Query, QueryHandler, QueryBus,
    RequestMatchCommand, CancelMatchCommand,
    GetMatchStatusQuery,
)
from turing_test.backend.infrastructure.events.event_bus import (
    EventBus, Event, EventType, EventBuilder, event_bus,
)

logger = logging.getLogger(__name__)


# ============== 匹配领域模型 ==============


class MatchStatus(Enum):
    """匹配状态"""
    PENDING = "pending"           # 等待中
    QUEUED = "queued"             # 已加入队列
    MATCHED = "matched"           # 已匹配 (等待会话创建)
    COMPLETED = "completed"       # 已完成 (会话已创建)
    FAILED = "failed"             # 匹配失败
    CANCELLED = "cancelled"       # 已取消
    TIMEOUT = "timeout"           # 超时


@dataclass
class MatchRequest:
    """匹配请求 - 值对象"""
    user_id: int
    user_score: int
    preferences: Dict[str, Any]
    requested_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.preferences:
            self.preferences = {}


@dataclass
class MatchResult:
    """匹配结果 - 值对象"""
    match_id: str
    user_id: int
    opponent_type: str  # "human", "bot", "honeypot"
    opponent_id: Optional[int]
    bot_config: Optional[Dict[str, Any]]
    is_honeypot: bool
    matched_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "opponent_type": self.opponent_type,
            "opponent_id": self.opponent_id,
            "is_honeypot": self.is_honeypot,
            "matched_at": self.matched_at.isoformat(),
        }


@dataclass
class Match:
    """
    匹配聚合根
    
    不变量:
    1. 匹配结果只能在 MATCHED 状态设置
    2. 一旦进入终端状态 (COMPLETED/FAILED/CANCELLED/TIMEOUT), 不能再改变
    3. 会话 ID 只能在 COMPLETED 状态设置
    """
    match_id: str
    user_id: int
    status: MatchStatus = MatchStatus.PENDING
    request: Optional[MatchRequest] = None
    result: Optional[MatchResult] = None
    session_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    timeout_at: Optional[datetime] = None
    
    # 领域行为
    def queue(self, timeout_seconds: int = 30):
        """加入队列"""
        self._check_can_modify()
        self.status = MatchStatus.QUEUED
        self.timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        self._touch()
    
    def complete(self, result: MatchResult, session_id: int):
        """完成匹配"""
        self._check_can_modify()
        if self.status != MatchStatus.MATCHED:
            raise ValueError(f"Cannot complete match in status {self.status}")
        
        self.result = result
        self.session_id = session_id
        self.status = MatchStatus.COMPLETED
        self._touch()
    
    def mark_matched(self, result: MatchResult):
        """标记为已匹配 (等待会话创建)"""
        self._check_can_modify()
        self.result = result
        self.status = MatchStatus.MATCHED
        self._touch()
    
    def fail(self, reason: str):
        """失败"""
        self._check_can_modify()
        self.status = MatchStatus.FAILED
        self.error_message = reason
        self._touch()
    
    def cancel(self, reason: str = "user_cancelled"):
        """取消"""
        self._check_can_modify()
        self.status = MatchStatus.CANCELLED
        self.error_message = reason
        self._touch()
    
    def timeout(self):
        """超时"""
        self._check_can_modify()
        self.status = MatchStatus.TIMEOUT
        self.error_message = "Match timeout"
        self._touch()
    
    def is_terminal(self) -> bool:
        """是否是终端状态"""
        return self.status in {
            MatchStatus.COMPLETED,
            MatchStatus.FAILED,
            MatchStatus.CANCELLED,
            MatchStatus.TIMEOUT,
        }
    
    def is_expired(self) -> bool:
        """是否超时"""
        if self.timeout_at is None:
            return False
        return datetime.utcnow() > self.timeout_at
    
    def _check_can_modify(self):
        """检查是否可以修改"""
        if self.is_terminal():
            raise ValueError(f"Cannot modify match in terminal status {self.status}")
    
    def _touch(self):
        """更新时间戳"""
        self.updated_at = datetime.utcnow()


# ============== 匹配仓库接口 ==============


class MatchRepository:
    """匹配仓库接口"""
    
    async def get_by_user_id(self, user_id: int) -> Optional[Match]:
        """获取用户的匹配"""
        raise NotImplementedError
    
    async def get_by_match_id(self, match_id: str) -> Optional[Match]:
        """获取匹配"""
        raise NotImplementedError
    
    async def save(self, match: Match):
        """保存匹配"""
        raise NotImplementedError
    
    async def delete(self, match_id: str):
        """删除匹配"""
        raise NotImplementedError
    
    async def get_queued_users(self) -> List[int]:
        """获取队列中的用户 ID 列表"""
        raise NotImplementedError


# ============== 匹配策略接口 ==============


class MatchStrategy:
    """匹配策略接口"""
    
    async def find_opponent(self, user_id: int, user_score: int, preferences: Dict[str, Any]) -> Optional[MatchResult]:
        """寻找对手"""
        raise NotImplementedError


# ============== 命令处理器 ==============


class RequestMatchHandler(CommandHandler[MatchResult]):
    """
    请求匹配命令处理器
    
    流程:
    1. 检查用户是否已有进行中的匹配
    2. 执行匹配策略寻找对手
    3. 创建匹配聚合根
    4. 发布事件
    """
    
    def __init__(
        self,
        repository: MatchRepository,
        strategy: MatchStrategy,
        event_bus: EventBus,
        timeout_seconds: int = 30,
    ):
        self._repository = repository
        self._strategy = strategy
        self._event_bus = event_bus
        self._timeout_seconds = timeout_seconds
    
    async def handle(self, command: RequestMatchCommand) -> CommandResult[MatchResult]:
        try:
            # 1. 检查是否已有进行中的匹配
            existing = await self._repository.get_by_user_id(command.user_id)
            if existing and not existing.is_terminal():
                return CommandResult.fail("Match already in progress", "MATCH_IN_PROGRESS")
            
            # 2. 创建匹配请求
            request = MatchRequest(
                user_id=command.user_id,
                user_score=command.user_score,
                preferences=command.preferences,
            )
            
            # 3. 发布匹配请求事件
            await EventBuilder(EventType.MATCH_REQUESTED)\
                .aggregate(str(command.user_id), "user")\
                .with_data(user_score=command.user_score)\
                .publish(self._event_bus)
            
            # 4. 执行匹配策略
            match_result = await self._strategy.find_opponent(
                command.user_id,
                command.user_score,
                command.preferences,
            )
            
            # 5. 创建匹配聚合根
            import uuid
            match_id = str(uuid.uuid4())
            match = Match(match_id=match_id, user_id=command.user_id)
            match.request = request
            
            if match_result:
                # 立即匹配成功
                match.mark_matched(match_result)
                
                # 发布匹配成功事件
                await EventBuilder(EventType.MATCH_FOUND)\
                    .aggregate(match_id, "match")\
                    .with_data(**match_result.to_dict())\
                    .publish(self._event_bus)
            else:
                # 加入队列等待
                match.queue(self._timeout_seconds)
                
                # 发布加入队列事件
                await EventBuilder(EventType.MATCH_QUEUED)\
                    .aggregate(match_id, "match")\
                    .with_data(timeout_seconds=self._timeout_seconds)\
                    .publish(self._event_bus)
            
            # 6. 保存匹配
            await self._repository.save(match)
            
            # 7. 返回结果
            if match_result:
                return CommandResult.ok(data=match_result)
            else:
                # 队列中，返回 None 表示等待
                return CommandResult.ok(data=None)
                
        except Exception as e:
            logger.exception(f"Failed to process match request: {e}")
            return CommandResult.fail(str(e), "MATCH_ERROR")


class CancelMatchHandler(CommandHandler[bool]):
    """取消匹配命令处理器"""
    
    def __init__(self, repository: MatchRepository, event_bus: EventBus):
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: CancelMatchCommand) -> CommandResult[bool]:
        try:
            match = await self._repository.get_by_user_id(command.user_id)
            
            if not match:
                return CommandResult.fail("No active match found", "NO_MATCH")
            
            if match.is_terminal():
                return CommandResult.fail(f"Match already in terminal status: {match.status}", "INVALID_STATUS")
            
            # 取消匹配
            match.cancel(command.reason)
            await self._repository.save(match)
            
            # 发布取消事件
            await EventBuilder(EventType.MATCH_CANCELLED)\
                .aggregate(match.match_id, "match")\
                .with_data(reason=command.reason)\
                .publish(self._event_bus)
            
            return CommandResult.ok(data=True)
            
        except Exception as e:
            logger.exception(f"Failed to cancel match: {e}")
            return CommandResult.fail(str(e), "CANCEL_ERROR")


# ============== 查询处理器 ==============


@dataclass
class MatchStatusDTO:
    """匹配状态 DTO"""
    user_id: int
    status: str
    match_id: Optional[str] = None
    opponent_type: Optional[str] = None
    session_id: Optional[int] = None
    error_message: Optional[str] = None
    queued_since: Optional[datetime] = None
    timeout_at: Optional[datetime] = None


class GetMatchStatusHandler(QueryHandler[Optional[MatchStatusDTO]]):
    """获取匹配状态查询处理器"""
    
    def __init__(self, repository: MatchRepository):
        self._repository = repository
    
    async def handle(self, query: GetMatchStatusQuery) -> Optional[MatchStatusDTO]:
        match = await self._repository.get_by_user_id(query.user_id)
        
        if not match:
            return None
        
        return MatchStatusDTO(
            user_id=match.user_id,
            status=match.status.value,
            match_id=match.match_id,
            opponent_type=match.result.opponent_type if match.result else None,
            session_id=match.session_id,
            error_message=match.error_message,
            queued_since=match.created_at if match.status == MatchStatus.QUEUED else None,
            timeout_at=match.timeout_at,
        )


# ============== 匹配服务 (外观模式) ==============


class MatchService:
    """
    匹配服务 - 统一外观接口
    
    组合命令总线和查询总线，提供简化的 API
    """
    
    def __init__(
        self,
        command_bus: CommandBus,
        query_bus: QueryBus,
        event_bus: EventBus,
    ):
        self._command_bus = command_bus
        self._query_bus = query_bus
        self._event_bus = event_bus
    
    async def request_match(
        self,
        user_id: int,
        user_score: int = 100,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> CommandResult[Optional[MatchResult]]:
        """请求匹配"""
        command = RequestMatchCommand(
            user_id=user_id,
            user_score=user_score,
            preferences=preferences or {},
        )
        return await self._command_bus.dispatch(command)
    
    async def cancel_match(self, user_id: int, reason: str = "user_cancelled") -> CommandResult[bool]:
        """取消匹配"""
        command = CancelMatchCommand(user_id=user_id, reason=reason)
        return await self._command_bus.dispatch(command)
    
    async def get_match_status(self, user_id: int) -> Optional[MatchStatusDTO]:
        """获取匹配状态"""
        query = GetMatchStatusQuery(user_id=user_id)
        return await self._query_bus.dispatch(query)
    
    async def wait_for_match(
        self,
        user_id: int,
        timeout_seconds: float = 30,
        poll_interval: float = 1.0,
    ) -> Optional[MatchResult]:
        """
        等待匹配结果
        
        轮询检查匹配状态，直到:
        - 匹配成功
        - 超时
        - 失败/取消
        """
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout_seconds:
            status = await self.get_match_status(user_id)
            
            if not status:
                return None
            
            if status.status == "matched" or status.status == "completed":
                # 匹配成功，但需要等待会话创建完成
                if status.session_id:
                    return MatchResult(
                        match_id=status.match_id or "",
                        user_id=user_id,
                        opponent_type=status.opponent_type or "unknown",
                        opponent_id=None,
                        bot_config=None,
                        is_honeypot=False,
                    )
            
            if status.status in {"failed", "cancelled", "timeout"}:
                return None
            
            await asyncio.sleep(poll_interval)
        
        return None
