# 架构重构文档

## 概述

本次重构基于以下核心设计原则：
1. **单一状态源** - 所有状态只在一个地方维护
2. **事务边界清晰** - 匹配和会话创建在同一事务内完成
3. **事件驱动** - 组件间通过事件通信，解耦依赖
4. **CQRS 模式** - 读写分离，查询和命令使用不同模型

## 新架构模块

### 1. 基础设施层 (infrastructure/)

```
turing_test/backend/infrastructure/
├── events/              # 事件总线
│   ├── event_bus.py     # EventBus, Event, EventType, EventBuilder
│   └── __init__.py
├── cqrs/                # CQRS 模式
│   ├── cqrs.py          # CommandBus, QueryBus, CommandHandler, QueryHandler
│   └── __init__.py
├── messaging/           # 消息路由
│   ├── message_router.py # MessageRouter, MessageQueue, ConnectionManager
│   └── __init__.py
├── transaction/         # 事务管理
│   ├── transaction_manager.py # TransactionManager, Saga, TransactionalCoordinator
│   └── __init__.py
├── di/                  # 依赖注入
│   ├── container.py     # AsyncServiceContainer, ServiceScope
│   └── __init__.py
└── __init__.py
```

### 2. 领域层 (domains/)

```
turing_test/backend/domains/
├── match/               # 匹配领域
│   ├── match_service.py # MatchService, Match, MatchRepository
│   └── __init__.py
├── session/             # 会话领域
│   ├── session_service.py # SessionManager, Session, SessionRepository
│   └── __init__.py
├── score/               # 积分领域
│   ├── score_service.py # ScoreService, ScoreCalculator, ScoreRepository
│   └── __init__.py
└── __init__.py
```

## 核心设计

### 事件驱动架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Event Bus                               │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │Publisher │───▶│  Event   │───▶│Subscriber│              │
│  └──────────┘    │  Bus     │    └──────────┘              │
│                  └──────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

**事件类型**:
- `MATCH_REQUESTED` - 匹配请求
- `MATCH_FOUND` - 找到匹配
- `SESSION_CREATED` - 会话创建
- `SESSION_MESSAGE_RECEIVED` - 收到消息
- `SCORE_SETTLED` - 积分结算

**使用示例**:
```python
from turing_test.backend.infrastructure.events import EventBuilder, EventType, event_bus

# 发布事件
await EventBuilder(EventType.MATCH_REQUESTED)\
    .aggregate(str(user_id), "user")\
    .with_data(user_score=100)\
    .publish(event_bus)

# 订阅事件
event_bus.subscribe(EventType.SESSION_CREATED, handle_session_created)
```

### CQRS 模式

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│  Command Bus  │              │   Query Bus   │
│  (Write)      │              │   (Read)      │
└───────┬───────┘              └───────┬───────┘
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│ Command       │              │ Query         │
│ Handlers      │              │ Handlers      │
└───────┬───────┘              └───────┬───────┘
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│ Domain        │              │ Read          │
│ Services      │              │ Models (DTO)  │
└───────┬───────┘              └───────────────┘
        │
        ▼
┌───────────────┐
│ Write         │
│ Database      │
└───────────────┘
```

**命令示例**:
```python
from turing_test.backend.infrastructure.cqrs import (
    RequestMatchCommand, CommandBus, CommandResult
)

# 发送命令
command = RequestMatchCommand(user_id=123, user_score=100)
result = await command_bus.dispatch(command)

if result.success:
    session_id = result.data.session_id
else:
    print(f"Error: {result.error}")
```

**查询示例**:
```python
from turing_test.backend.infrastructure.cqrs import GetSessionQuery, QueryBus

# 发送查询
query = GetSessionQuery(session_id=1)
session = await query_bus.dispatch(query)
```

### 事务管理

```python
from turing_test.backend.infrastructure.transaction import (
    TransactionManager, TransactionalCoordinator
)

# 使用事务管理器
async with tx_manager.transaction() as tx:
    # 数据库操作
    session = await create_session(tx.context)
    tx.context.set("session_id", session.id)
    
    # 发布事件
    await event_bus.publish(...)
    
    # 自动提交或回滚

# 使用协调器确保跨域操作原子性
await coordinator.match_and_create_session(
    user_id=user_id,
    match_result=match_result,
    create_session_func=create_session,
)
```

### Saga 模式 (长运行事务)

```python
from turing_test.backend.infrastructure.transaction import Saga

# 创建 Saga
saga = Saga("match_session", event_bus)

# 添加步骤和补偿操作
saga.add_step(
    "request_match",
    action=request_match,
    compensation=cleanup_match,
)
saga.add_step(
    "create_session",
    action=create_session,
    compensation=delete_session,
)

# 执行 Saga
await saga.execute(initial_data={"user_id": 123})
```

### 依赖注入

```python
from turing_test.backend.infrastructure.di import (
    create_container, AsyncServiceContainer, ServiceScope
)

# 创建容器
container = create_container()

# 注册服务
container.register_singleton(EventBus)
container.register_scoped(SessionManager)
container.register_transient(MessageRouter)

# 解析服务
event_bus = await container.resolve(EventBus)

# 创建作用域
async with request_scope(container) as scope:
    service = await scope.resolve(ServiceType)
```

## 模块间通信

### 事件驱动解耦

```
┌─────────────┐      Event       ┌─────────────┐
│MatchService │─────────────────▶│SessionService│
└─────────────┘                  └─────────────┘
       │                                │
       │ EventType.MATCH_FOUND          │ EventType.SESSION_CREATED
       ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│                        Event Bus                             │
└─────────────────────────────────────────────────────────────┘
```

### 消息路由

```
WebSocket → ConnectionManager → MessageRouter → MessageHandler → Response
                                    │
                                    ▼
                              MessageQueue (背压处理)
```

## 数据一致性保证

### 匹配 - 会话创建流程

```
1. 用户请求匹配
   └─> RequestMatchCommand
   └─> MatchService.request_match()
   └─> MATCH_REQUESTED 事件

2. 匹配成功
   └─> MATCH_FOUND 事件
   └─> TransactionalCoordinator.match_and_create_session()
       ├─> 开始事务
       ├─> 创建会话
       ├─> 更新匹配状态
       ├─> SESSION_CREATED 事件
       ├─> MATCH_COMPLETED 事件
       └─> 提交事务

3. 会话激活
   └─> SessionManager.activate()
   └─> SESSION_STARTED 事件
   └─> 发送开场白
```

### 积分结算流程

```
1. 用户提交判断
   └─> SubmitJudgmentCommand
   └─> ScoreService.submit_judgment()

2. 计算积分
   └─> ScoreCalculator.calculate_final_score()
   └─> SCORE_CALCULATING 事件

3. 更新积分
   └─> 开始事务
   ├─> 更新用户积分
   ├─> 记录 ScoreHistory
   ├─> 标记会话已结算
   └─> SCORE_SETTLED 事件

4. 检查对方猜错奖励
   └─> 如果有奖励 → 标记待领取
   └─> 用户可调用 /claim-opponent-bonus
```

## 迁移指南

### 从旧架构迁移

#### 1. 替换全局单例

**旧代码**:
```python
from turing_test.backend.websocket.manager import manager
from turing_test.backend.services.session_state import session_state_manager
```

**新代码**:
```python
from turing_test.backend.infrastructure.di import get_current_container

container = get_current_container()
connection_manager = await container.resolve(ConnectionManager)
session_manager = await container.resolve(SessionManager)
```

#### 2. 替换直接服务调用

**旧代码**:
```python
from turing_test.backend.services.match_service import match_service

result = await match_service.join_queue(user_id, score)
```

**新代码**:
```python
from turing_test.backend.infrastructure.cqrs import RequestMatchCommand, CommandBus

command = RequestMatchCommand(user_id=user_id, user_score=score)
result = await command_bus.dispatch(command)
```

#### 3. 添加事件监听

**旧代码**:
```python
# 直接调用
await session_service.create_session(user_id, opponent_type)
```

**新代码**:
```python
# 发布事件，由监听器处理
await EventBuilder(EventType.MATCH_FOUND)\
    .aggregate(match_id, "match")\
    .with_data(opponent_type=opponent_type)\
    .publish(event_bus)

# 在别处订阅
event_bus.subscribe(EventType.MATCH_FOUND, handle_match_found)
```

## 测试

运行集成测试:
```bash
pytest tests/test_architecture.py -v --asyncio-mode=auto
```

## 性能考虑

1. **事件总线**: 异步非阻塞，支持高并发
2. **CQRS**: 读写分离，查询可缓存
3. **依赖注入**: 单例缓存，减少创建开销
4. **消息队列**: 背压处理，防止系统过载

## 后续工作

1. **数据库集成** - 实现 Repository 接口的数据库版本
2. **Redis 缓存** - 使用 Redis 共享状态，支持多实例部署
3. **监控和日志** - 添加事件追踪和性能监控
4. **API 适配层** - 创建兼容旧 API 的适配层
5. **逐步迁移** - 分模块迁移现有代码

## 架构优势

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| 状态管理 | 分散 (内存 +DB) | 统一 (聚合根) |
| 组件耦合 | 紧耦合 | 事件驱动解耦 |
| 事务边界 | 模糊 | 清晰 |
| 测试性 | 困难 (全局单例) | 容易 (依赖注入) |
| 扩展性 | 单实例 | 支持多实例 |
| 可维护性 | 中等 | 高 |

## 参考资源

- [CQRS Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)
- [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Domain-Driven Design](https://domainlanguage.com/ddd/)
