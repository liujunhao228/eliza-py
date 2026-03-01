# 数据结构重构实施报告

## 实施概述

本次重构实现了**三层分离架构**，解决了原有数据结构中职责混杂、状态分散、循环依赖等问题。

---

## 已创建文件清单

### 1. 领域模型层 (`turing_test/backend/domain/`)

| 文件 | 说明 |
|------|------|
| `__init__.py` | 包导出 |
| `models.py` | 值对象、领域事件、枚举类型 |
| `services.py` | 聚合根业务逻辑 |
| `repositories.py` | Repository 层、工作单元模式 |
| `tests/test_domain_models.py` | 领域模型单元测试 |

### 2. SQLAlchemy ORM 模型 (`turing_test/backend/models/`)

| 文件 | 说明 |
|------|------|
| `domain_models.py` | 新表结构的 ORM 映射 |

### 3. 数据库迁移 (`turing_test/backend/migrations/`)

| 文件 | 说明 |
|------|------|
| `create_domain_models.py` | 创建所有新表的迁移脚本 |

---

## 新表结构

### 匹配层

| 表名 | 说明 |
|------|------|
| `bot_configs` | Bot 配置元数据 (YAML+Lua 文件路径) |
| `matches` | 匹配记录 (一次性事件) |

### 对话层

| 表名 | 说明 |
|------|------|
| `rooms` | 对话空间 (多人共享) |
| `room_participants` | 对话参与者 |
| `messages` | 消息 (属于 Room) |

### 用户会话层

| 表名 | 说明 |
|------|------|
| `user_sessions` | 用户会话 (个人视角状态) |

### 积分领域

| 表名 | 说明 |
|------|------|
| `session_scores` | 会话积分记录 |
| `score_breakdown_items` | 积分明细分项 (替代 JSON) |

---

## 核心设计特性

### 1. 领域驱动设计 (DDD)

```
值对象 (不可变)     聚合根 (业务逻辑)    领域事件
    ↓                    ↓                   ↓
MatchId            MatchAggregate      MatchCompleted
RoomId             RoomAggregate       MessageAdded
UserId             UserSessionAggregate JudgmentSubmitted
ScoreBreakdown     ScoreAggregate      ScoreSettled
```

### 2. Repository 模式

```python
# 使用示例
async with SqlAlchemyUnitOfWork(session) as uow:
    # 获取聚合根
    match = await uow.matches.get(match_id)
    
    # 修改状态
    match.complete(room_id, result)
    
    # 持久化
    await uow.matches.update(match)
    await uow.commit()
```

### 3. 工作单元 (Unit of Work)

```python
class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    matches: MatchRepository
    rooms: RoomRepository
    user_sessions: UserSessionRepository
    scores: ScoreRepository
```

### 4. 领域事件

```python
# 事件示例
@dataclass
class MatchCompleted(DomainEvent):
    match_id: str
    user_id: int
    room_id: str
    opponent_type: str
```

---

## 单元测试覆盖

运行测试:
```bash
pytest turing_test/backend/domain/tests/test_domain_models.py -v
```

### 测试覆盖

| 类别 | 测试项 |
|------|--------|
| 值对象 | ID 生成、不可变性、序列化 |
| Match 聚合根 | 创建、完成、失败、超时、事件 |
| Room 聚合根 | 创建、参与者、消息、离开、结束 |
| UserSession 聚合根 | 创建、发送消息、提交判断、结束 |
| Score 聚合根 | 计算、结算、奖励领取 |
| 集成测试 | 完整人机匹配流程 |

---

## 使用示例

### 1. 创建匹配

```python
from turing_test.backend.domain import (
    MatchAggregate, MatchId, UserId, MatchStatus,
    MatchResult, OpponentType, RoomId,
)

# 创建匹配
match = MatchAggregate(
    id=MatchId("match-1"),
    user_id=UserId(100),
    status=MatchStatus.PENDING,
)

# 完成匹配 (Bot)
result = MatchResult(
    opponent_type=OpponentType.BOT,
    opponent_user_id=None,
    bot_config_id="bot-1",
    bot_level="lv1_newbie",
    is_honeypot=False,
)

match.complete(RoomId("room-1"), result)

# 获取发布的事件
events = match.pop_events()  # [MatchCompleted]
```

### 2. 创建对话和参与者

```python
from turing_test.backend.domain import (
    RoomAggregate, ParticipantInfo, ParticipantRole,
)

room = RoomAggregate(
    id=RoomId("room-1"),
    type=RoomType.HUMAN_VS_BOT,
)

# 添加参与者
room.add_participant(ParticipantInfo(
    user_id=UserId(100),
    role=ParticipantRole.USER,
    bot_config_id="bot-1",
    bot_level="lv1_newbie",
    is_honeypot=False,
    joined_at=datetime.utcnow(),
))
```

### 3. 创建用户会话

```python
from turing_test.backend.domain import UserSessionAggregate

session = UserSessionAggregate(
    id=SessionId("session-1"),
    user_id=UserId(100),
    room_id=RoomId("room-1"),
)
```

### 4. 发送消息

```python
# Room 添加消息
room.add_message(
    sender_id=UserId(100),
    sender_type="user",
    content="你好",
)

# Session 同步
session.send_message(message_id=1)
```

### 5. 提交判断和结算

```python
# 提交判断
session.submit_judgment(
    guess="ai",
    confidence="high",
)

# 计算积分
score = ScoreAggregate(
    session_id=SessionId("session-1"),
    user_id=UserId(100),
    room_id=RoomId("room-1"),
)

score.calculate(
    user_guess="ai",
    opponent_type="bot",
    confidence="high",
    turn_count=5,
    meta_count=0,
)

# 结算
score.settle_base()
```

---

## 数据库迁移

### 执行迁移

```bash
# 如果有 Alembic 配置
alembic upgrade head

# 或者手动执行
python -m turing_test.backend.scripts.migrate
```

### 回滚

```bash
alembic downgrade -1
```

---

## 与现有代码集成

### 1. 更新 User 模型关系

在 `models/__init__.py` 的 `User` 类中添加:

```python
# 新增关系
matches: Mapped[List["Match"]] = relationship(
    "Match",
    back_populates="user",
    foreign_keys="Match.user_id",
)

user_sessions: Mapped[List["UserSession"]] = relationship(
    "UserSession",
    back_populates="user",
    foreign_keys="UserSession.user_id",
)

session_scores: Mapped[List["SessionScore"]] = relationship(
    "SessionScore",
    back_populates="user",
    foreign_keys="SessionScore.user_id",
)

room_participations: Mapped[List["RoomParticipant"]] = relationship(
    "RoomParticipant",
    back_populates="user",
)

messages: Mapped[List["Message"]] = relationship(
    "Message",
    back_populates="sender",
    foreign_keys="Message.sender_id",
)
```

### 2. 导入新模型

```python
# 在 models/__init__.py 中
from turing_test.backend.models.domain_models import (
    BotConfig, Match, Room, RoomParticipant, Message,
    UserSession, SessionScore, ScoreBreakdownItem,
)
```

---

## 下一步工作

### 1. 服务层实现

创建应用服务，组合领域模型和 Repository:

```python
class MatchService:
    def __init__(self, uow: AbstractUnitOfWork, event_bus: EventBus):
        self.uow = uow
        self.event_bus = event_bus
    
    async def request_match(self, user_id: int, user_score: int):
        # 创建 Match
        match = MatchAggregate(...)
        
        # 执行匹配策略
        result = await self.find_opponent(...)
        
        # 创建 Room 和 UserSession
        ...
        
        # 发布事件
        await self.event_bus.publish(...)
```

### 2. API 适配层

更新现有 API 使用新领域模型:

```python
@router.post("/match/join")
async def join_match(user_id: int, db: AsyncSession = Depends(get_db)):
    async with SqlAlchemyUnitOfWork(db) as uow:
        service = MatchService(uow, event_bus)
        result = await service.request_match(user_id, score=100)
        return result
```

### 3. 事件处理器

实现领域事件的监听和处理:

```python
@event_bus.subscribe(MatchCompleted)
async def handle_match_completed(event: MatchCompleted):
    # 创建 Room 和 UserSession
    ...
```

### 4. 消息服务

集成消息路由和领域模型:

```python
class MessageService:
    async def send_message(self, room_id: int, user_id: int, content: str):
        async with self.uow as uow:
            room = await uow.rooms.get(RoomId(room_id))
            room.add_message(...)
            await uow.rooms.update(room)
```

---

## 架构优势

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| 职责分离 | 单表 40+ 字段 | 三层分离 |
| 状态管理 | 分散 | 聚合根统一 |
| 真人对战支持 | 复杂 | 原生支持 |
| 积分结算 | 耦合 | 独立领域 |
| 可测试性 | 困难 | 领域模型纯函数 |
| 扩展性 | 低 | 高 |

---

## 风险与注意事项

1. **数据一致性** - 新表未包含历史数据，需要时单独迁移
2. **性能** - 表连接增多，注意索引优化
3. **学习曲线** - 团队需要熟悉 DDD 概念
4. **过度设计** - 评估是否所有场景都需要聚合根

---

## 参考文档

- [ARCHITECTURE_REBUILD.md](../ARCHITECTURE_REBUILD.md) - 架构重构设计文档
- [domain/models.py](./turing_test/backend/domain/models.py) - 领域模型定义
- [domain/services.py](./turing_test/backend/domain/services.py) - 聚合根实现
