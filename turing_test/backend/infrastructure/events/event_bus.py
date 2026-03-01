"""
事件总线模块 - 组件间解耦通信的核心基础设施

设计原则:
1. 发布/订阅模式 - 组件间零直接依赖
2. 异步事件处理 - 非阻塞事件传播
3. 事件持久化 - 关键事件记录到数据库
4. 重试机制 - 失败事件自动重试
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar
from contextlib import asynccontextmanager
import json
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EventType(Enum):
    """
    系统事件类型定义
    
    命名约定:
    - {Domain}.{Action}.{Result}
    - 使用过去时态表示已发生的事件
    """
    # 匹配领域事件
    MATCH_REQUESTED = "match.requested"
    MATCH_QUEUED = "match.queued"
    MATCH_FOUND = "match.found"
    MATCH_COMPLETED = "match.completed"
    MATCH_FAILED = "match.failed"
    MATCH_TIMEOUT = "match.timeout"
    MATCH_CANCELLED = "match.cancelled"
    
    # 会话领域事件
    SESSION_CREATING = "session.creating"
    SESSION_CREATED = "session.created"
    SESSION_STARTED = "session.started"
    SESSION_MESSAGE_RECEIVED = "session.message.received"
    SESSION_MESSAGE_SENT = "session.message.sent"
    SESSION_TURN_CHANGED = "session.turn.changed"
    SESSION_ENDED = "session.ended"
    SESSION_TIMEOUT = "session.timeout"
    SESSION_ERROR = "session.error"
    
    # 积分领域事件
    SCORE_CALCULATING = "score.calculating"
    SCORE_SETTLED = "score.settled"
    SCORE_BONUS_CLAIMED = "score.bonus.claimed"
    SCORE_ERROR = "score.error"
    
    # 用户领域事件
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"
    USER_ONLINE_STATUS_CHANGED = "user.online_status.changed"


@dataclass(frozen=True)
class Event:
    """
    不可变事件基类
    
    所有事件必须包含的元数据:
    - event_id: 全局唯一事件 ID
    - event_type: 事件类型
    - timestamp: 事件发生时间
    - aggregate_id: 聚合根 ID (如 session_id, user_id)
    - aggregate_type: 聚合根类型
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "data": self.data,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Event:
        """从字典反序列化"""
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=data.get("event_type", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            aggregate_id=data.get("aggregate_id"),
            aggregate_type=data.get("aggregate_type"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EventSubscription:
    """事件订阅配置"""
    event_type: EventType
    handler: Callable[[Event], Coroutine[Any, Any, None]]
    group: Optional[str] = None  # 消费者组，用于负载均衡
    retry_count: int = 3  # 重试次数
    retry_delay: float = 1.0  # 重试延迟 (秒)
    filter_func: Optional[Callable[[Event], bool]] = None  # 事件过滤器
    
    def matches(self, event: Event) -> bool:
        """检查事件是否匹配此订阅"""
        if self.filter_func is None:
            return True
        return self.filter_func(event)


class EventBus:
    """
    事件总线实现
    
    特性:
    - 异步事件分发
    - 订阅者组管理
    - 失败重试机制
    - 事件追踪
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._subscriptions: Dict[EventType, List[EventSubscription]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000  # 最大事件历史记录
        self._running = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._stats = {
            "published": 0,
            "delivered": 0,
            "failed": 0,
        }
    
    async def start(self):
        """启动事件总线"""
        if self._running:
            return
        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info(f"EventBus '{self.name}' started")
    
    async def stop(self):
        """停止事件总线"""
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info(f"EventBus '{self.name}' stopped")
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
        group: Optional[str] = None,
        retry_count: int = 3,
        filter_func: Optional[Callable[[Event], bool]] = None,
    ):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 异步事件处理函数
            group: 消费者组 (同组内事件只发送给一个订阅者)
            retry_count: 失败重试次数
            filter_func: 事件过滤函数
        """
        subscription = EventSubscription(
            event_type=event_type,
            handler=handler,
            group=group,
            retry_count=retry_count,
            filter_func=filter_func,
        )
        
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
        self._subscriptions[event_type].append(subscription)
        
        logger.debug(f"Subscribed to {event_type.value} (group={group})")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
    ):
        """取消订阅"""
        if event_type not in self._subscriptions:
            return
        
        self._subscriptions[event_type] = [
            sub for sub in self._subscriptions[event_type]
            if sub.handler != handler
        ]
    
    async def publish(self, event: Event):
        """
        发布事件
        
        Args:
            event: 要发布的事件
        """
        # 添加到事件历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # 加入处理队列
        await self._event_queue.put(event)
        self._stats["published"] += 1
        
        logger.debug(f"Published event {event.event_type} (id={event.event_id})")
    
    async def _process_events(self):
        """事件处理循环"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._dispatch_event(event)
                self._event_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error processing event: {e}")
    
    async def _dispatch_event(self, event: Event):
        """分发事件到所有订阅者"""
        event_type = EventType(event.event_type) if event.event_type in [e.value for e in EventType] else None
        
        if event_type is None:
            logger.warning(f"Unknown event type: {event.event_type}")
            return
        
        subscriptions = self._subscriptions.get(event_type, [])
        
        if not subscriptions:
            logger.debug(f"No subscribers for {event_type.value}")
            return
        
        # 按消费者组分组
        group_tasks = []
        grouped_subs: Dict[Optional[str], List[EventSubscription]] = {}
        
        for sub in subscriptions:
            if not sub.matches(event):
                continue
            
            key = sub.group or sub.handler.__name__
            if key not in grouped_subs:
                grouped_subs[key] = []
            grouped_subs[key].append(sub)
        
        # 每组只执行一个订阅者 (负载均衡)
        for group_key, subs in grouped_subs.items():
            sub = subs[0]  # 简单策略：选第一个
            task = asyncio.create_task(self._invoke_handler(sub, event))
            group_tasks.append(task)
        
        if group_tasks:
            results = await asyncio.gather(*group_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self._stats["failed"] += 1
                    logger.error(f"Event handler failed: {result}")
                else:
                    self._stats["delivered"] += 1
    
    async def _invoke_handler(self, subscription: EventSubscription, event: Event):
        """调用处理器，带重试机制"""
        last_error = None
        
        for attempt in range(subscription.retry_count + 1):
            try:
                await subscription.handler(event)
                return
            except Exception as e:
                last_error = e
                if attempt < subscription.retry_count:
                    logger.warning(
                        f"Event handler failed (attempt {attempt + 1}/{subscription.retry_count}): {e}"
                    )
                    await asyncio.sleep(subscription.retry_delay * (attempt + 1))
        
        logger.error(f"Event handler failed after {subscription.retry_count} retries: {last_error}")
        raise last_error
    
    def get_stats(self) -> Dict[str, Any]:
        """获取总线统计信息"""
        return {
            **self._stats,
            "queue_size": self._event_queue.qsize(),
            "subscription_count": sum(len(subs) for subs in self._subscriptions.values()),
        }
    
    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        aggregate_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """查询事件历史"""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type.value]
        
        if aggregate_id:
            events = [e for e in events if e.aggregate_id == aggregate_id]
        
        return events[-limit:]


# 全局事件总线实例 (通过依赖注入使用)
event_bus = EventBus("global")


@dataclass
class EventRecord:
    """事件记录 - 用于持久化"""
    id: int
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    processed: bool = False
    retry_count: int = 0
    
    def to_event(self) -> Event:
        """转换为 Event 对象"""
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            timestamp=self.created_at,
            aggregate_id=self.aggregate_id,
            aggregate_type=self.aggregate_type,
            data=self.data,
            metadata=self.metadata,
        )


class EventStore:
    """
    事件存储 - 持久化关键事件
    
    支持:
    - 事件追加
    - 按聚合根查询
    - 事件重放
    """
    
    def __init__(self, db_session_factory):
        self._db_session_factory = db_session_factory
        self._pending_events: List[Event] = []
        self._lock = asyncio.Lock()
    
    async def append(self, event: Event):
        """追加事件到存储"""
        async with self._lock:
            self._pending_events.append(event)
            
            # 批量写入优化
            if len(self._pending_events) >= 10:
                await self._flush()
    
    async def _flush(self):
        """批量刷新到数据库"""
        if not self._pending_events:
            return
        
        # TODO: 实现数据库写入
        # async with self._db_session_factory() as session:
        #     for event in self._pending_events:
        #         record = EventRecord(...)
        #         session.add(record)
        #     await session.commit()
        
        self._pending_events.clear()
    
    async def get_events(
        self,
        aggregate_id: str,
        since_id: Optional[int] = None,
    ) -> List[EventRecord]:
        """获取聚合根的事件流"""
        # TODO: 实现数据库查询
        return []
    
    async def replay(
        self,
        aggregate_id: str,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
    ):
        """重放聚合根的事件"""
        events = await self.get_events(aggregate_id)
        for record in events:
            await handler(record.to_event())


# 事件构建器 - 简化事件创建
class EventBuilder:
    """流式事件构建器"""
    
    def __init__(self, event_type: EventType):
        self._event_type = event_type
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}
        self._aggregate_id: Optional[str] = None
        self._aggregate_type: Optional[str] = None
    
    def aggregate(self, id: str, type: str) -> EventBuilder:
        """设置聚合根"""
        self._aggregate_id = id
        self._aggregate_type = type
        return self
    
    def with_data(self, **kwargs) -> EventBuilder:
        """添加事件数据"""
        self._data.update(kwargs)
        return self
    
    def with_metadata(self, **kwargs) -> EventBuilder:
        """添加元数据"""
        self._metadata.update(kwargs)
        return self
    
    def build(self) -> Event:
        """构建事件"""
        return Event(
            event_type=self._event_type.value,
            aggregate_id=self._aggregate_id,
            aggregate_type=self._aggregate_type,
            data=self._data,
            metadata=self._metadata,
        )
    
    async def publish(self, bus: EventBus = event_bus):
        """构建并发布事件"""
        event = self.build()
        await bus.publish(event)
        return event
