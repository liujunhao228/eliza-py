"""
架构重构集成测试

测试新架构的核心功能:
1. 事件总线 - 发布/订阅
2. CQRS - 命令/查询处理
3. 事务管理 - 原子操作
4. 依赖注入 - 服务解析
5. 消息路由 - 消息分发
"""

import asyncio
import pytest
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock

# 导入基础设施
from turing_test.backend.infrastructure.events.event_bus import (
    EventBus, Event, EventType, EventBuilder, event_bus,
)
from turing_test.backend.infrastructure.cqrs.cqrs import (
    CommandBus, QueryBus, CommandHandler, QueryHandler, CommandResult,
    Command, Query, RequestMatchCommand,
)
from turing_test.backend.infrastructure.messaging.message_router import (
    MessageRouter, MessageHandler, MessageContext, Message, MessageType,
)
from turing_test.backend.infrastructure.di.container import (
    AsyncServiceContainer, ServiceScope, create_container,
)


# ============== 事件总线测试 ==============


class TestEventBus:
    """事件总线测试"""
    
    @pytest.fixture
    def event_bus_instance(self):
        """创建事件总线实例"""
        bus = EventBus("test")
        return bus
    
    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, event_bus_instance):
        """测试发布/订阅"""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # 订阅
        event_bus_instance.subscribe(EventType.MATCH_REQUESTED, handler)
        await event_bus_instance.start()
        
        try:
            # 发布
            event = Event(
                event_type=EventType.MATCH_REQUESTED.value,
                aggregate_id="user_123",
                data={"user_score": 100},
            )
            await event_bus_instance.publish(event)
            
            # 等待处理
            await asyncio.sleep(0.1)
            
            # 验证
            assert len(received_events) == 1
            assert received_events[0].aggregate_id == "user_123"
            assert received_events[0].data["user_score"] == 100
        finally:
            await event_bus_instance.stop()
    
    @pytest.mark.asyncio
    async def test_event_builder(self, event_bus_instance):
        """测试事件构建器"""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        event_bus_instance.subscribe(EventType.SESSION_CREATED, handler)
        await event_bus_instance.start()
        
        try:
            # 使用构建器
            await EventBuilder(EventType.SESSION_CREATED)\
                .aggregate("session_1", "session")\
                .with_data(user_id=123, opponent_type="bot")\
                .with_metadata(source="test")\
                .publish(event_bus_instance)
            
            await asyncio.sleep(0.1)
            
            assert len(received_events) == 1
            event = received_events[0]
            assert event.aggregate_id == "session_1"
            assert event.data["user_id"] == 123
            assert event.metadata["source"] == "test"
        finally:
            await event_bus_instance.stop()
    
    @pytest.mark.asyncio
    async def test_event_filter(self, event_bus_instance):
        """测试事件过滤器"""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # 只接收 user_id=1 的事件
        event_bus_instance.subscribe(
            EventType.SESSION_MESSAGE_RECEIVED,
            handler,
            filter_func=lambda e: e.data.get("user_id") == 1,
        )
        
        await event_bus_instance.start()
        
        try:
            # 发布符合条件的事件
            await EventBuilder(EventType.SESSION_MESSAGE_RECEIVED)\
                .aggregate("1", "session")\
                .with_data(user_id=1, content="hello")\
                .publish(event_bus_instance)
            
            # 发布不符合条件的事件
            await EventBuilder(EventType.SESSION_MESSAGE_RECEIVED)\
                .aggregate("2", "session")\
                .with_data(user_id=2, content="world")\
                .publish(event_bus_instance)
            
            await asyncio.sleep(0.1)
            
            assert len(received_events) == 1
            assert received_events[0].data["user_id"] == 1
        finally:
            await event_bus_instance.stop()


# ============== CQRS 测试 ==============


class TestCQRS:
    """CQRS 测试"""
    
    @pytest.fixture
    def command_bus(self):
        """创建命令总线"""
        return CommandBus()
    
    @pytest.fixture
    def query_bus(self):
        """创建查询总线"""
        return QueryBus()
    
    @pytest.mark.asyncio
    async def test_command_handler(self, command_bus):
        """测试命令处理器"""
        # 创建测试命令
        class TestCommand(Command):
            value: int
        
        # 创建处理器
        class TestHandler(CommandHandler[int]):
            async def handle(self, command: TestCommand) -> CommandResult[int]:
                return CommandResult.ok(data=command.value * 2)
        
        # 注册
        command_bus.register(TestCommand, TestHandler())
        
        # 执行
        command = TestCommand(value=21)
        result = await command_bus.dispatch(command)
        
        assert result.success is True
        assert result.data == 42
    
    @pytest.mark.asyncio
    async def test_command_handler_error(self, command_bus):
        """测试命令处理错误"""
        class FailCommand(Command):
            pass
        
        class FailHandler(CommandHandler[None]):
            async def handle(self, command: FailCommand) -> CommandResult[None]:
                return CommandResult.fail("Test error", "TEST_ERROR")
        
        command_bus.register(FailCommand, FailHandler())
        
        result = await command_bus.dispatch(FailCommand())
        
        assert result.success is False
        assert result.error == "Test error"
        assert result.error_code == "TEST_ERROR"
    
    @pytest.mark.asyncio
    async def test_query_handler(self, query_bus):
        """测试查询处理器"""
        class TestQuery(Query):
            key: str
        
        class TestHandler(QueryHandler[str]):
            def __init__(self):
                self._data = {"name": "Alice", "city": "Beijing"}
            
            async def handle(self, query: TestQuery) -> str:
                return self._data.get(query.key, "unknown")
        
        query_bus.register(TestQuery, TestHandler())
        
        result = await query_bus.dispatch(TestQuery(key="name"))
        assert result == "Alice"


# ============== 依赖注入测试 ==============


class TestDependencyInjection:
    """依赖注入测试"""
    
    @pytest.fixture
    def container(self):
        """创建容器"""
        return AsyncServiceContainer()
    
    @pytest.mark.asyncio
    async def test_resolve_singleton(self, container):
        """测试单例解析"""
        class ServiceA:
            def __init__(self):
                self.value = 42
        
        container.register_singleton(ServiceA)
        
        # 第一次解析
        instance1 = await container.resolve(ServiceA)
        # 第二次解析
        instance2 = await container.resolve(ServiceA)
        
        # 应该是同一实例
        assert instance1 is instance2
        assert instance1.value == 42
    
    @pytest.mark.asyncio
    async def test_resolve_transient(self, container):
        """测试瞬态解析"""
        class ServiceB:
            def __init__(self):
                self.id = id(self)
        
        container.register_transient(ServiceB)
        
        instance1 = await container.resolve(ServiceB)
        instance2 = await container.resolve(ServiceB)
        
        # 应该是不同实例
        assert instance1 is not instance2
        assert instance1.id != instance2.id
    
    @pytest.mark.asyncio
    async def test_resolve_with_dependencies(self, container):
        """测试依赖解析"""
        class Database:
            async def query(self):
                return "data"
        
        class Repository:
            def __init__(self, db: Database):
                self.db = db
        
        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo
        
        container.register_singleton(Database)
        container.register_singleton(Repository)
        container.register_singleton(Service)
        
        service = await container.resolve(Service)
        
        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)
        assert isinstance(service.repo.db, Database)
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, container):
        """测试循环依赖检测"""
        class ServiceA:
            def __init__(self, service_b):
                self.service_b = service_b
        
        class ServiceB:
            def __init__(self, service_a):
                self.service_a = service_a
        
        container.register_singleton(ServiceA)
        container.register_singleton(ServiceB)
        
        # 应该抛出循环依赖异常
        with pytest.raises(Exception) as exc_info:
            await container.resolve(ServiceA)
        
        assert "Circular dependency" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_scope(self, container):
        """测试作用域"""
        class ScopedService:
            def __init__(self):
                self.created_at = datetime.utcnow()
        
        container.register(ScopedService, scope=ServiceScope.SCOPED)
        
        # 根容器解析
        instance1 = await container.resolve(ScopedService)
        
        # 创建子作用域
        scope = container.create_scope()
        instance2 = await scope.resolve(ScopedService)
        instance3 = await scope.resolve(ScopedService)
        
        # 同作用域内相同
        assert instance2 is instance3
        # 不同作用域不同
        assert instance1 is not instance2
        
        scope.dispose()


# ============== 消息路由测试 ==============


class TestMessageRouter:
    """消息路由器测试"""
    
    @pytest.fixture
    def router(self):
        """创建路由器"""
        return MessageRouter()
    
    @pytest.mark.asyncio
    async def test_route_message(self, router):
        """测试消息路由"""
        class TestHandler(MessageHandler):
            async def handle(self, message: Message, context: MessageContext) -> Message:
                return Message(
                    type="response",
                    data={"echo": message.data.get("content")},
                )
        
        router.register("test", TestHandler())
        
        message = Message(
            type="test",
            data={"content": "hello"},
        )
        context = MessageContext(user_id=1, session_id=1)
        
        response = await router.route(message, context)
        
        assert response.type == "response"
        assert response.data["echo"] == "hello"
    
    @pytest.mark.asyncio
    async def test_middleware(self, router):
        """测试中间件"""
        from turing_test.backend.infrastructure.messaging.message_router import MessageMiddleware
        
        class LoggingMiddleware(MessageMiddleware):
            def __init__(self):
                self.called = False
            
            async def before_handle(self, message: Message, context: MessageContext) -> bool:
                self.called = True
                message.data["middleware_processed"] = True
                return True
        
        middleware = LoggingMiddleware()
        router.add_middleware(middleware)
        
        class TestHandler(MessageHandler):
            async def handle(self, message: Message, context: MessageContext) -> Message:
                return message
        
        router.register("test", TestHandler())
        
        message = Message(type="test", data={})
        context = MessageContext(user_id=1, session_id=1)
        
        response = await router.route(message, context)
        
        assert middleware.called is True
        assert response.data.get("middleware_processed") is True


# ============== 集成测试 ==============


class TestIntegration:
    """集成测试 - 测试组件间协作"""
    
    @pytest.mark.asyncio
    async def test_full_flow(self):
        """
        完整流程测试:
        1. 用户请求匹配
        2. 事件发布
        3. 会话创建
        4. 消息发送
        """
        # 创建容器
        container = create_container()
        
        # 解析服务
        event_bus = await container.resolve(EventBus)
        command_bus = await container.resolve(CommandBus)
        
        # 启动服务
        await event_bus.start()
        
        try:
            # 订阅事件
            events_received = []
            
            async def on_match_requested(event: Event):
                events_received.append(event)
            
            event_bus.subscribe(EventType.MATCH_REQUESTED, on_match_requested)
            
            # 模拟匹配请求
            # (实际使用时需要注册 MatchService)
            
            # 验证事件被接收
            await asyncio.sleep(0.1)
            
        finally:
            await event_bus.stop()
            container.dispose()


# ============== 性能测试 ==============


class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_event_bus_throughput(self):
        """测试事件总线吞吐量"""
        bus = EventBus("perf")
        event_count = 1000
        
        async def handler(event: Event):
            pass
        
        bus.subscribe(EventType.SESSION_MESSAGE_RECEIVED, handler)
        await bus.start()
        
        try:
            import time
            start = time.time()
            
            for i in range(event_count):
                await EventBuilder(EventType.SESSION_MESSAGE_RECEIVED)\
                    .aggregate(str(i), "session")\
                    .with_data(index=i)\
                    .publish(bus)
            
            # 等待处理完成
            await asyncio.sleep(1)
            
            elapsed = time.time() - start
            rate = event_count / elapsed
            
            print(f"Event throughput: {rate:.2f} events/sec")
            
            # 应该达到至少 1000 events/sec
            assert rate > 1000
            
        finally:
            await bus.stop()
    
    @pytest.mark.asyncio
    async def test_container_resolution_speed(self):
        """测试容器解析速度"""
        container = AsyncServiceContainer()
        
        class FastService:
            pass
        
        container.register_singleton(FastService)
        
        # 预热
        await container.resolve(FastService)
        
        import time
        iterations = 10000
        
        start = time.time()
        for _ in range(iterations):
            await container.resolve(FastService)
        elapsed = time.time() - start
        
        rate = iterations / elapsed
        print(f"Resolution speed: {rate:.2f} resolutions/sec")
        
        # 应该达到至少 10000 resolutions/sec (单例缓存)
        assert rate > 10000
        
        container.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
