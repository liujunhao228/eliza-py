"""
CQRS 模式 - 命令和查询分离

设计原则:
1. 命令 (Command) - 改变状态的操作，返回结果或错误
2. 查询 (Query) - 读取状态的操作，不产生副作用
3. 命令处理器 - 处理命令并产生事件
4. 查询处理器 - 处理查询并返回数据
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
import uuid

# ============== 命令模型 ==============


@dataclass(frozen=True, kw_only=True)
class Command:
    """命令基类"""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # 关联 ID，用于追踪请求链
    causation_id: Optional[str] = None    # 前因命令 ID


@dataclass(frozen=True, kw_only=True)
class RequestMatchCommand(Command):
    """请求匹配命令"""
    user_id: int
    user_score: int = 100
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class CancelMatchCommand(Command):
    """取消匹配命令"""
    user_id: int
    reason: str = "user_cancelled"


@dataclass(frozen=True, kw_only=True)
class CreateSessionCommand(Command):
    """创建会话命令"""
    user_id: int
    opponent_type: str  # "human", "bot", "honeypot"
    opponent_id: Optional[int] = None
    bot_config: Optional[Dict[str, Any]] = None
    is_honeypot: bool = False


@dataclass(frozen=True, kw_only=True)
class EndSessionCommand(Command):
    """结束会话命令"""
    session_id: int
    user_id: int
    end_reason: str = "user_requested"
    final_turn: Optional[int] = None


@dataclass(frozen=True, kw_only=True)
class SubmitJudgmentCommand(Command):
    """提交判断命令 (场中/最终)"""
    session_id: int
    user_id: int
    guess: str  # "human" or "ai"
    confidence: str  # "low", "mid", "high"
    is_mid_game: bool = False
    meta_keywords: List[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ClaimBonusCommand(Command):
    """领取奖励命令"""
    session_id: int
    user_id: int


# ============== 查询模型 ==============


@dataclass(frozen=True, kw_only=True)
class Query:
    """查询基类"""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True, kw_only=True)
class GetMatchStatusQuery(Query):
    """获取匹配状态查询"""
    user_id: int


@dataclass(frozen=True, kw_only=True)
class GetSessionQuery(Query):
    """获取会话查询"""
    session_id: int


@dataclass(frozen=True, kw_only=True)
class GetUserSessionsQuery(Query):
    """获取用户会话列表查询"""
    user_id: int
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, kw_only=True)
class GetSessionMessagesQuery(Query):
    """获取会话消息查询"""
    session_id: int
    limit: int = 100
    before_id: Optional[int] = None


@dataclass(frozen=True, kw_only=True)
class GetScoreQuery(Query):
    """获取积分查询"""
    user_id: int


@dataclass(frozen=True, kw_only=True)
class GetScoreHistoryQuery(Query):
    """获取积分历史查询"""
    user_id: int
    session_id: Optional[int] = None
    limit: int = 50


# ============== 命令结果 ==============


T = TypeVar('T')


@dataclass
class CommandResult(Generic[T]):
    """命令执行结果"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def ok(cls, data: Optional[T] = None, warnings: Optional[List[str]] = None) -> CommandResult[T]:
        return cls(success=True, data=data, warnings=warnings or [])
    
    @classmethod
    def fail(cls, error: str, error_code: Optional[str] = None) -> CommandResult[T]:
        return cls(success=False, error=error, error_code=error_code)


# ============== 命令/查询处理器接口 ==============


class CommandHandler(ABC, Generic[T]):
    """命令处理器接口"""
    
    @abstractmethod
    async def handle(self, command: Command) -> CommandResult[T]:
        """处理命令并返回结果"""
        pass


class QueryHandler(ABC, Generic[T]):
    """查询处理器接口"""
    
    @abstractmethod
    async def handle(self, query: Query) -> T:
        """处理查询并返回数据"""
        pass


# ============== 命令总线 ==============


class CommandBus:
    """
    命令总线 - 命令分发和执行的中心
    
    特性:
    - 命令验证
    - 事务管理
    - 命令追踪
    - 幂等性检查
    """
    
    def __init__(self):
        self._handlers: Dict[type, CommandHandler] = {}
        self._middleware: List[CommandMiddleware] = []
        self._pending_commands: Dict[str, Command] = {}
    
    def register(self, command_type: type, handler: CommandHandler):
        """注册命令处理器"""
        self._handlers[command_type] = handler
    
    def add_middleware(self, middleware: CommandMiddleware):
        """添加中间件"""
        self._middleware.append(middleware)
    
    async def dispatch(self, command: Command) -> CommandResult[Any]:
        """分发并执行命令"""
        # 生成 correlation_id
        if not command.correlation_id:
            object.__setattr__(command, 'correlation_id', command.command_id)
        
        # 执行中间件
        for mw in self._middleware:
            should_continue = await mw.before_execute(command)
            if not should_continue:
                return CommandResult.fail("Command rejected by middleware", "MIDDLEWARE_REJECTED")
        
        # 查找处理器
        handler = self._handlers.get(type(command))
        if not handler:
            return CommandResult.fail(f"No handler for command: {type(command).__name__}", "NO_HANDLER")
        
        try:
            # 执行命令
            result = await handler.handle(command)
            
            # 执行后置中间件
            for mw in reversed(self._middleware):
                await mw.after_execute(command, result)
            
            return result
        except Exception as e:
            # 执行异常中间件
            for mw in reversed(self._middleware):
                await mw.on_error(command, e)
            
            return CommandResult.fail(str(e), "EXECUTION_ERROR")


class CommandMiddleware(ABC):
    """命令中间件基类"""
    
    async def before_execute(self, command: Command) -> bool:
        """命令执行前"""
        return True
    
    async def after_execute(self, command: Command, result: CommandResult):
        """命令执行后"""
        pass
    
    async def on_error(self, command: Command, error: Exception):
        """发生错误时"""
        pass


class TransactionMiddleware(CommandMiddleware):
    """
    事务中间件 - 确保命令执行的原子性
    """
    
    def __init__(self, transaction_manager: TransactionManager):
        self._transaction_manager = transaction_manager
    
    async def before_execute(self, command: Command) -> bool:
        # 开始事务
        await self._transaction_manager.begin()
        return True
    
    async def after_execute(self, command: Command, result: CommandResult):
        if result.success:
            await self._transaction_manager.commit()
        else:
            await self._transaction_manager.rollback()
    
    async def on_error(self, command: Command, error: Exception):
        await self._transaction_manager.rollback()


# ============== 查询总线 ==============


class QueryBus:
    """
    查询总线 - 查询分发和执行的中心
    
    特性:
    - 查询缓存
    - 读写分离
    - 查询优化
    """
    
    def __init__(self):
        self._handlers: Dict[type, QueryHandler] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 60  # 缓存 TTL (秒)
    
    def register(self, query_type: type, handler: QueryHandler):
        """注册查询处理器"""
        self._handlers[query_type] = handler
    
    async def dispatch(self, query: Query) -> Any:
        """分发并执行查询"""
        # 检查缓存 (简单实现，可扩展)
        cache_key = f"{type(query).__name__}:{str(query)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 查找处理器
        handler = self._handlers.get(type(query))
        if not handler:
            raise ValueError(f"No handler for query: {type(query).__name__}")
        
        # 执行查询
        result = await handler.handle(query)
        
        # 缓存结果 (可选)
        # self._cache[cache_key] = result
        
        return result


# ============== 事务管理器 ==============


class TransactionManager:
    """
    事务管理器 - 管理数据库事务边界
    
    确保:
    - ACID 属性
    - 嵌套事务支持
    - 事务超时
    """
    
    def __init__(self, db_session_factory):
        self._db_session_factory = db_session_factory
        self._current_transaction: Optional[Transaction] = None
        self._lock = asyncio.Lock()
    
    async def begin(self, isolation_level: str = "READ COMMITTED") -> Transaction:
        """开始新事务"""
        async with self._lock:
            if self._current_transaction:
                # 嵌套事务
                self._current_transaction = Transaction(
                    parent=self._current_transaction,
                    db_session_factory=self._db_session_factory,
                )
            else:
                self._current_transaction = Transaction(
                    db_session_factory=self._db_session_factory,
                )
            
            await self._current_transaction.begin()
            return self._current_transaction
    
    async def commit(self):
        """提交当前事务"""
        if not self._current_transaction:
            raise RuntimeError("No active transaction")
        
        await self._current_transaction.commit()
        
        if self._current_transaction.parent:
            self._current_transaction = self._current_transaction.parent
        else:
            self._current_transaction = None
    
    async def rollback(self):
        """回滚当前事务"""
        if not self._current_transaction:
            return
        
        await self._current_transaction.rollback()
        
        if self._current_transaction.parent:
            self._current_transaction = self._current_transaction.parent
        else:
            self._current_transaction = None
    
    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        tx = await self.begin()
        try:
            yield tx
            await self.commit()
        except Exception:
            await self.rollback()
            raise
    
    def get_session(self):
        """获取当前事务的数据库会话"""
        if not self._current_transaction:
            raise RuntimeError("No active transaction")
        return self._current_transaction.session


@dataclass
class Transaction:
    """事务对象"""
    db_session_factory: Any
    parent: Optional[Transaction] = None
    session: Optional[Any] = None
    _active: bool = False
    
    async def begin(self):
        """开始事务"""
        if self.parent:
            # 嵌套事务使用父事务的 session
            self.session = self.parent.session
        else:
            self.session = await self.db_session_factory()
            await self.session.begin()
        self._active = True
    
    async def commit(self):
        """提交事务"""
        if not self._active:
            return
        
        if not self.parent:
            await self.session.commit()
        self._active = False
    
    async def rollback(self):
        """回滚事务"""
        if not self._active:
            return
        
        if not self.parent:
            await self.session.rollback()
        self._active = False


# 需要导入 asynccontextmanager
from contextlib import asynccontextmanager
import asyncio
