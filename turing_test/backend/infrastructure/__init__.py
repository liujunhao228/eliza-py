"""
基础设施模块 - 提供核心基础设施组件

包括:
- 事件总线 (Event Bus)
- CQRS 模式实现
- 消息路由
- 事务管理
- 依赖注入
"""

from turing_test.backend.infrastructure.events.event_bus import (
    EventBus,
    Event,
    EventType,
    EventBuilder,
    EventStore,
    event_bus,
)

from turing_test.backend.infrastructure.cqrs.cqrs import (
    Command,
    Query,
    CommandHandler,
    QueryHandler,
    CommandResult,
    CommandBus,
    QueryBus,
    CommandMiddleware,
    TransactionMiddleware,
    TransactionManager,
    Transaction,
    RequestMatchCommand,
    CancelMatchCommand,
    CreateSessionCommand,
    EndSessionCommand,
    SubmitJudgmentCommand,
    ClaimBonusCommand,
    GetMatchStatusQuery,
    GetSessionQuery,
    GetUserSessionsQuery,
    GetScoreQuery,
)

from turing_test.backend.infrastructure.messaging.message_router import (
    Message,
    MessageType,
    MessageRouter,
    MessageHandler,
    MessageContext,
    MessageMiddleware,
    MessageQueue,
    ConnectionManager,
    ConnectionState,
)

from turing_test.backend.infrastructure.transaction.transaction_manager import (
    TransactionManager as TxManager,
    TransactionContext,
    TransactionStatus,
    IsolationLevel,
    TransactionalCoordinator,
    Saga,
    SagaOrchestrator,
)

from turing_test.backend.infrastructure.di.container import (
    ServiceContainer,
    AsyncServiceContainer,
    ServiceScope,
    create_container,
    request_scope,
    inject,
    set_current_container,
    get_current_container,
)

__all__ = [
    # Event Bus
    'EventBus',
    'Event',
    'EventType',
    'EventBuilder',
    'EventStore',
    'event_bus',
    
    # CQRS
    'Command',
    'Query',
    'CommandHandler',
    'QueryHandler',
    'CommandResult',
    'CommandBus',
    'QueryBus',
    'CommandMiddleware',
    'TransactionMiddleware',
    'TransactionManager',
    'Transaction',
    'RequestMatchCommand',
    'CancelMatchCommand',
    'CreateSessionCommand',
    'EndSessionCommand',
    'SubmitJudgmentCommand',
    'ClaimBonusCommand',
    'GetMatchStatusQuery',
    'GetSessionQuery',
    'GetUserSessionsQuery',
    'GetScoreQuery',
    
    # Messaging
    'Message',
    'MessageType',
    'MessageRouter',
    'MessageHandler',
    'MessageContext',
    'MessageMiddleware',
    'MessageQueue',
    'ConnectionManager',
    'ConnectionState',
    
    # Transaction
    'TxManager',
    'TransactionContext',
    'TransactionStatus',
    'IsolationLevel',
    'TransactionalCoordinator',
    'Saga',
    'SagaOrchestrator',
    
    # DI
    'ServiceContainer',
    'AsyncServiceContainer',
    'ServiceScope',
    'create_container',
    'request_scope',
    'inject',
    'set_current_container',
    'get_current_container',
]
