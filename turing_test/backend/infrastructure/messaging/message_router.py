"""
消息路由中心 - 统一消息分发

设计原则:
1. 集中式路由 - 所有消息通过路由中心分发
2. 类型安全 - 消息类型和处理器强类型
3. 可扩展 - 支持中间件和插件
4. 背压处理 - 消息队列溢出保护
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Deque, Dict, List, Optional, Set, Tuple, Union
import uuid

from turing_test.backend.infrastructure.events.event_bus import (
    EventBus, EventType, EventBuilder, event_bus,
)

logger = logging.getLogger(__name__)


# ============== 消息类型定义 ==============


class MessageType(Enum):
    """消息类型"""
    # 客户端 -> 服务器
    CHAT = "chat"
    MESSAGE = "message"
    MID_GAME_JUDGMENT = "mid_game_judgment"
    END_SESSION = "end_session"
    CLAIM_BONUS = "claim_bonus"
    PING = "ping"
    PONG = "pong"
    
    # 服务器 -> 客户端
    CONNECTED = "connected"
    CHAT_RESPONSE = "chat"
    TYPING = "typing"
    STOP_TYPING = "stop_typing"
    MID_GAME_SUBMITTED = "mid_game_submitted"
    SESSION_ENDED = "session_ended"
    OPPONENT_ENDED = "opponent_ended"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class Message:
    """
    消息对象
    
    统一的消息格式，用于内部和外部通信
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # 路由信息
    from_user_id: Optional[int] = None
    to_user_id: Optional[int] = None
    session_id: Optional[int] = None
    
    # 元数据
    correlation_id: Optional[str] = None  # 关联请求 ID
    reply_to: Optional[str] = None  # 回复的消息 ID
    priority: int = 0  # 优先级 (越高越优先)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """从字典反序列化"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=data.get("type", ""),
            data=data.get("data", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            session_id=data.get("session_id"),
        )
    
    @classmethod
    def chat(cls, content: str, from_user_id: int, session_id: int) -> Message:
        """创建聊天消息"""
        return cls(
            type=MessageType.CHAT.value,
            data={"content": content},
            from_user_id=from_user_id,
            session_id=session_id,
        )
    
    @classmethod
    def error(cls, message: str, code: str, session_id: Optional[int] = None) -> Message:
        """创建错误消息"""
        return cls(
            type=MessageType.ERROR.value,
            data={"message": message, "code": code},
            session_id=session_id,
        )
    
    @classmethod
    def typing(cls, session_id: int, is_typing: bool = True) -> Message:
        """创建打字提示消息"""
        return cls(
            type=MessageType.TYPING.value if is_typing else MessageType.STOP_TYPING.value,
            data={},
            session_id=session_id,
        )


# ============== 连接状态 ==============


@dataclass
class ConnectionState:
    """
    WebSocket 连接状态
    """
    user_id: int
    session_id: Optional[int]
    websocket: Any  # WebSocket 对象
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    
    def touch(self):
        """更新活动时间"""
        self.last_activity = datetime.utcnow()
        self.message_count += 1


# ============== 消息处理器接口 ==============


class MessageHandler:
    """消息处理器接口"""
    
    async def handle(self, message: Message, context: MessageContext) -> Optional[Message]:
        """
        处理消息
        
        Args:
            message: 输入消息
            context: 消息上下文
        
        Returns:
            响应消息 (如果有)
        """
        raise NotImplementedError


@dataclass
class MessageContext:
    """消息处理上下文"""
    user_id: int
    session_id: Optional[int]
    db_session: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============== 消息路由器 ==============


class MessageRouter:
    """
    消息路由器 - 消息分发中心
    
    职责:
    1. 消息类型路由
    2. 中间件执行
    3. 错误处理
    4. 消息追踪
    """
    
    def __init__(self, event_bus: EventBus = None):
        self._event_bus = event_bus or event_bus
        self._handlers: Dict[str, MessageHandler] = {}
        self._middleware: List[MessageMiddleware] = []
        self._stats = {
            "received": 0,
            "processed": 0,
            "errors": 0,
        }
    
    def register(self, message_type: str, handler: MessageHandler):
        """注册消息处理器"""
        self._handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    def add_middleware(self, middleware: MessageMiddleware):
        """添加中间件"""
        self._middleware.append(middleware)
    
    async def route(self, message: Message, context: MessageContext) -> Optional[Message]:
        """
        路由消息到对应处理器
        
        流程:
        1. 执行前置中间件
        2. 查找处理器
        3. 执行处理
        4. 执行后置中间件
        5. 返回响应
        """
        self._stats["received"] += 1
        
        try:
            # 前置中间件
            for mw in self._middleware:
                should_continue = await mw.before_handle(message, context)
                if not should_continue:
                    logger.debug(f"Message processing stopped by middleware: {mw.__class__.__name__}")
                    return None
            
            # 查找处理器
            handler = self._handlers.get(message.type)
            if not handler:
                logger.warning(f"No handler for message type: {message.type}")
                return Message.error(f"Unknown message type: {message.type}", "UNKNOWN_TYPE", message.session_id)
            
            # 执行处理
            response = await handler.handle(message, context)
            
            # 后置中间件
            for mw in reversed(self._middleware):
                response = await mw.after_handle(message, response, context)
            
            self._stats["processed"] += 1
            return response
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.exception(f"Error routing message: {e}")
            
            # 发布错误事件
            await EventBuilder(EventType.SESSION_ERROR)\
                .aggregate(str(context.session_id), "session")\
                .with_data(error=str(e), message_type=message.type)\
                .publish(self._event_bus)
            
            return Message.error(str(e), "HANDLER_ERROR", message.session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "handler_count": len(self._handlers),
        }


class MessageMiddleware:
    """消息中间件基类"""
    
    async def before_handle(self, message: Message, context: MessageContext) -> bool:
        """消息处理前"""
        return True
    
    async def after_handle(self, message: Message, response: Optional[Message], context: MessageContext) -> Optional[Message]:
        """消息处理后"""
        return response


# ============== 消息队列 ==============


@dataclass
class QueuedMessage:
    """队列中的消息"""
    message: Message
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    max_retries: int = 3


class MessageQueue:
    """
    消息队列 - 背压处理和重试
    
    特性:
    1. 每用户独立队列
    2. 消息去重
    3. 失败重试
    4. 队列溢出保护
    """
    
    def __init__(self, max_size: int = 100, max_retries: int = 3):
        self._max_size = max_size
        self._max_retries = max_retries
        self._queues: Dict[int, Deque[QueuedMessage]] = {}
        self._processing: Dict[int, bool] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
    
    async def enqueue(self, user_id: int, message: Message) -> bool:
        """
        加入消息队列
        
        Returns:
            True 如果成功，False 如果队列已满
        """
        if user_id not in self._queues:
            self._queues[user_id] = deque(maxlen=self._max_size)
            self._locks[user_id] = asyncio.Lock()
        
        async with self._locks[user_id]:
            queue = self._queues[user_id]
            
            if len(queue) >= self._max_size:
                logger.warning(f"Message queue full for user {user_id}, dropping message")
                return False
            
            queue.append(QueuedMessage(message=message, max_retries=self._max_retries))
            return True
    
    async def dequeue(self, user_id: int) -> Optional[QueuedMessage]:
        """取出消息"""
        if user_id not in self._queues:
            return None
        
        async with self._locks.get(user_id, asyncio.Lock()):
            queue = self._queues.get(user_id)
            if not queue:
                return None
            return queue.popleft()
    
    async def requeue(self, user_id: int, message: Message, retry_count: int) -> bool:
        """重新加入队列 (失败重试)"""
        if retry_count >= self._max_retries:
            logger.warning(f"Message max retries reached for user {user_id}")
            return False
        
        return await self.enqueue(user_id, message)
    
    def get_queue_size(self, user_id: int) -> int:
        """获取队列大小"""
        if user_id not in self._queues:
            return 0
        return len(self._queues[user_id])


# ============== 连接管理器 ==============


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    职责:
    1. 连接生命周期管理
    2. 用户 - 会话关联
    3. 消息发送 (带队列)
    4. 心跳监控
    """
    
    def __init__(
        self,
        router: MessageRouter,
        message_queue: MessageQueue,
        event_bus: EventBus,
        rate_limit: int = 60,  # 每分钟最大消息数
        rate_window: int = 60,  # 速率限制窗口 (秒)
    ):
        self._router = router
        self._message_queue = message_queue
        self._event_bus = event_bus
        self._rate_limit = rate_limit
        self._rate_window = rate_window
        
        self._connections: Dict[int, ConnectionState] = {}  # user_id -> state
        self._session_users: Dict[int, Set[int]] = {}  # session_id -> user_ids
        self._rate_counters: Dict[int, List[datetime]] = {}  # user_id -> timestamps
        self._locks: Dict[int, asyncio.Lock] = {}
        
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动连接管理器"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("ConnectionManager started")
    
    async def stop(self):
        """停止连接管理器"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("ConnectionManager stopped")
    
    async def connect(self, user_id: int, session_id: int, websocket: Any) -> bool:
        """
        建立连接
        
        Returns:
            True 如果成功，False 如果速率限制
        """
        # 速率限制检查
        if not self._check_rate_limit(user_id):
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # 创建连接状态
        state = ConnectionState(
            user_id=user_id,
            session_id=session_id,
            websocket=websocket,
        )
        
        # 获取锁
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        
        async with self._locks[user_id]:
            # 关闭旧连接 (如果有)
            if user_id in self._connections:
                old_state = self._connections[user_id]
                await self._disconnect_internal(old_state, "replaced")
            
            # 注册新连接
            self._connections[user_id] = state
            
            # 关联会话
            if session_id not in self._session_users:
                self._session_users[session_id] = set()
            self._session_users[session_id].add(user_id)
        
        # 发布连接事件
        await EventBuilder(EventType.USER_CONNECTED)\
            .aggregate(str(user_id), "user")\
            .with_data(session_id=session_id)\
            .publish(self._event_bus)
        
        logger.info(f"User {user_id} connected to session {session_id}")
        return True
    
    async def disconnect(self, user_id: int, reason: str = "user_disconnected"):
        """断开连接"""
        if user_id not in self._connections:
            return
        
        state = self._connections[user_id]
        await self._disconnect_internal(state, reason)
    
    async def _disconnect_internal(self, state: ConnectionState, reason: str):
        """内部断开连接"""
        user_id = state.user_id
        
        # 从会话移除
        if state.session_id and state.session_id in self._session_users:
            self._session_users[state.session_id].discard(user_id)
        
        # 移除连接
        if user_id in self._connections:
            del self._connections[user_id]
        
        # 关闭 WebSocket
        try:
            await state.websocket.close()
        except Exception:
            pass
        
        # 发布断开事件
        await EventBuilder(EventType.USER_DISCONNECTED)\
            .aggregate(str(user_id), "user")\
            .with_data(reason=reason)\
            .publish(self._event_bus)
        
        logger.info(f"User {user_id} disconnected: {reason}")
    
    async def send_message(self, user_id: int, message: Message) -> bool:
        """
        发送消息到用户
        
        Returns:
            True 如果成功发送
        """
        if user_id not in self._connections:
            logger.debug(f"User {user_id} not connected, queueing message")
            return await self._message_queue.enqueue(user_id, message)
        
        state = self._connections[user_id]
        
        try:
            await state.websocket.send_json(message.to_dict())
            state.touch()
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to user {user_id}: {e}")
            # 加入队列重试
            return await self._message_queue.enqueue(user_id, message)
    
    async def send_to_session(self, session_id: int, message: Message, exclude_user: Optional[int] = None):
        """发送消息到会话的所有用户"""
        if session_id not in self._session_users:
            return
        
        user_ids = list(self._session_users[session_id])
        for user_id in user_ids:
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_message(user_id, message)
    
    async def handle_message(self, user_id: int, raw_data: Dict[str, Any]) -> Optional[Message]:
        """
        处理收到的消息
        
        Returns:
            响应消息 (如果有)
        """
        if user_id not in self._connections:
            return Message.error("Not connected", "NOT_CONNECTED")
        
        state = self._connections[user_id]
        state.touch()
        
        # 解析消息
        try:
            message = Message.from_dict(raw_data)
            message.from_user_id = user_id
        except Exception as e:
            return Message.error(f"Invalid message format: {e}", "INVALID_FORMAT")
        
        # 创建上下文
        context = MessageContext(
            user_id=user_id,
            session_id=state.session_id,
        )
        
        # 路由处理
        response = await self._router.route(message, context)
        
        # 发送响应
        if response:
            await self.send_message(user_id, response)
        
        return response
    
    def get_connection(self, user_id: int) -> Optional[ConnectionState]:
        """获取连接状态"""
        return self._connections.get(user_id)
    
    def get_session_users(self, session_id: int) -> Set[int]:
        """获取会话中的用户 ID 列表"""
        return self._session_users.get(session_id, set())
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """检查速率限制"""
        now = datetime.utcnow()
        cutoff = now.timestamp() - self._rate_window
        
        if user_id not in self._rate_counters:
            self._rate_counters[user_id] = []
        
        # 清理过期记录
        self._rate_counters[user_id] = [
            ts for ts in self._rate_counters[user_id]
            if ts.timestamp() > cutoff
        ]
        
        # 检查是否超限
        if len(self._rate_counters[user_id]) >= self._rate_limit:
            return False
        
        # 记录新消息
        self._rate_counters[user_id].append(now)
        return True
    
    async def _cleanup_loop(self):
        """清理循环 - 清理超时连接"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                
                now = datetime.utcnow()
                timeout_users = []
                
                for user_id, state in list(self._connections.items()):
                    if (now - state.last_activity).total_seconds() > 300:  # 5 分钟超时
                        timeout_users.append((user_id, state))
                
                for user_id, state in timeout_users:
                    await self._disconnect_internal(state, "timeout")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup loop: {e}")


# ============== 内置处理器 ==============


class PingHandler(MessageHandler):
    """Ping 处理器"""
    
    async def handle(self, message: Message, context: MessageContext) -> Optional[Message]:
        return Message(
            type=MessageType.PONG.value,
            data={},
            reply_to=message.id,
        )


class ChatEchoHandler(MessageHandler):
    """
    聊天消息处理器 - 简单回显
    
    TODO: 集成到消息服务
    """
    
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
    
    async def handle(self, message: Message, context: MessageContext) -> Optional[Message]:
        # 发布消息接收事件
        await EventBuilder(EventType.SESSION_MESSAGE_RECEIVED)\
            .aggregate(str(context.session_id), "session")\
            .with_data(
                from_user=message.from_user_id,
                content=message.data.get("content"),
            )\
            .publish(self._event_bus)
        
        # 回显消息 (实际应该由消息服务处理)
        return Message(
            type=MessageType.CHAT_RESPONSE.value,
            data={
                "content": message.data.get("content"),
                "from_user_id": message.from_user_id,
            },
            session_id=context.session_id,
        )


class RateLimitMiddleware(MessageMiddleware):
    """速率限制中间件"""
    
    def __init__(self, max_per_second: int = 10):
        self._max_per_second = max_per_second
        self._counters: Dict[int, int] = {}
        self._last_reset: Dict[int, datetime] = {}
    
    async def before_handle(self, message: Message, context: MessageContext) -> bool:
        user_id = context.user_id
        now = datetime.utcnow()
        
        if user_id not in self._last_reset:
            self._last_reset[user_id] = now
            self._counters[user_id] = 0
        
        # 每秒重置计数器
        if (now - self._last_reset[user_id]).total_seconds() >= 1:
            self._last_reset[user_id] = now
            self._counters[user_id] = 0
        
        # 检查限制
        if self._counters[user_id] >= self._max_per_second:
            return False
        
        self._counters[user_id] += 1
        return True
