# 三层分离架构重构进度报告

**日期**: 2026 年 3 月 1 日  
**状态**: ✅ 核心架构完成，待集成测试

---

## 一、已完成的工作

### 1. 数据库层 (✅ 完成)

#### 新建 8 张表
| 表名 | 说明 | 所属层 |
|------|------|--------|
| `bot_configs` | Bot 配置元数据 | 匹配层 |
| `matches` | 匹配记录 | 匹配层 |
| `rooms` | 对话空间 | 对话层 |
| `room_participants` | 对话参与者 | 对话层 |
| `messages` | 消息（关联 room_id） | 对话层 |
| `user_sessions` | 用户会话（个人视角） | 用户会话层 |
| `session_scores` | 会话积分 | 用户会话层 |
| `score_breakdown_items` | 积分明细分项 | 用户会话层 |

#### 文件
- `turing_test/backend/models/domain_models.py` - SQLAlchemy ORM 模型
- `turing_test/backend/scripts/init_domain_db.py` - 数据库初始化脚本

### 2. 领域模型层 (✅ 完成)

#### 值对象
- `MatchId`, `RoomId`, `SessionId`, `UserId`, `MessageId`
- `MatchRequest`, `MatchResult`
- `ParticipantInfo`, `MessageContent`
- `Judgment`, `TurnState`
- `ScoreBreakdown`, `ScoreSettlement`

#### 聚合根
- `MatchAggregate` - 匹配聚合根
- `RoomAggregate` - 对话聚合根
- `UserSessionAggregate` - 用户会话聚合根
- `ScoreAggregate` - 积分聚合根

#### 枚举
- `MatchStatus`, `OpponentType`
- `RoomType`, `RoomStatus`, `ParticipantRole`
- `SessionStatus`

#### 文件
- `turing_test/backend/domain/models.py` - 值对象、枚举、领域事件
- `turing_test/backend/domain/services.py` - 聚合根业务逻辑（含工厂方法）
- `turing_test/backend/domain/repositories.py` - Repository 接口

### 3. Repository 实现层 (✅ 完成)

#### 实现类
- `MatchRepositoryImpl` - Match 聚合根持久化
- `RoomRepositoryImpl` - Room 聚合根持久化
- `UserSessionRepositoryImpl` - UserSession 聚合根持久化
- `ScoreRepositoryImpl` - Score 聚合根持久化

#### 功能
- 领域模型 ↔ ORM 模型转换
- 异步数据访问
- 工作单元模式支持

#### 文件
- `turing_test/backend/infrastructure/repositories/repository_impl.py`

### 4. 应用服务层 (✅ 完成)

#### 应用服务
- `MatchApplicationService` - 匹配应用服务
  - `request_match()` - 请求匹配
  - `cancel_match()` - 取消匹配
  - `complete_match()` - 完成匹配
  - `fail_match()` - 失败处理

- `RoomApplicationService` - 对话应用服务
  - `create_room()` - 创建对话
  - `add_participant()` - 添加参与者
  - `send_message()` - 发送消息
  - `end_room()` - 结束对话

- `SessionApplicationService` - 用户会话应用服务
  - `create_session()` - 创建会话
  - `update_turn()` - 更新回合
  - `submit_judgment()` - 提交判断
  - `settle_score()` - 积分结算
  - `claim_bonus()` - 申领奖励

#### 文件
- `turing_test/backend/application/match_service.py`
- `turing_test/backend/application/room_service.py`
- `turing_test/backend/application/session_service.py`

### 5. 事件驱动层 (✅ 完成)

#### 事件处理器
- `MatchEventHandler` - 匹配领域事件处理
- `RoomEventHandler` - 对话领域事件处理
- `ScoreEventHandler` - 积分领域事件处理

#### 支持的事件类型
- `MATCH_REQUESTED`, `MATCH_COMPLETED`, `MATCH_FAILED`, `MATCH_CANCELLED`
- `SESSION_CREATED`, `SESSION_MESSAGE_SENT`, `SESSION_ENDED`
- `SCORE_SETTLED`, `SCORE_BONUS_CLAIMED`

#### 文件
- `turing_test/backend/infrastructure/events/event_handlers.py`

### 6. 依赖注入容器 (✅ 完成)

#### 注册的服务
- 基础设施服务（EventBus, MessageQueue, ConnectionManager）
- Repository 接口到实现的映射
- 应用服务类型注册
- 添加 `register_async_factory()` 方法

#### 文件
- `turing_test/backend/infrastructure/di/container.py`

### 7. WebSocket 层 (✅ 完成)

#### 重构内容
- `websocket/match.py` - 基于新领域模型的匹配 WebSocket
  - 支持 `join`/`cancel` 操作
  - 使用 `MatchApplicationService` 处理业务
  - 通过领域事件推送结果

#### 文件
- `turing_test/backend/websocket/match.py`

### 8. API 层 (✅ 完成)

#### 新 API 端点
- `POST /room/{room_id}/message` - 发送消息
- `GET /room/{room_id}/messages` - 获取对话消息
- `POST /session/{session_id}/end` - 结束会话
- `POST /session/{session_id}/judgment` - 提交判断
- `GET /session/{session_id}/result` - 获取会话结果

#### 文件
- `turing_test/backend/api/game_new.py`

### 9. 消息服务 (✅ 完成)

#### 新服务
- `NewMessageService` - 基于领域模型的消息处理
  - 使用 `Room.send_message()` 发送
  - 使用 `UserSession` 管理回合

#### 文件
- `turing_test/backend/services/new_message_service.py`

### 10. 测试 (✅ 完成)

#### 端到端测试
- 测试完整流程：匹配 → 对话 → 消息 → 判断 → 结算
- 9 个测试用例覆盖各层功能

#### 文件
- `turing_test/backend/tests/integration/test_domain_flow.py`

---

## 二、架构设计原则

### 三层分离
```
┌─────────────────────────────────────────────────────────┐
│                    匹配层 (Match)                        │
│  一次性事件记录：用户请求匹配 → 匹配成功/失败             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   对话层 (Room)                          │
│  共享对话空间：多人消息记录、参与者管理                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                用户会话层 (UserSession)                   │
│  个人视角状态：回合、判断、积分结算                       │
└─────────────────────────────────────────────────────────┘
```

### 领域驱动设计
- **聚合根**: 管理业务逻辑和状态流转
- **值对象**: 不可变的业务概念
- **领域事件**: 记录发生的重要业务事件
- **Repository**: 数据访问接口，分离领域模型和 ORM

### CQRS 模式
- **命令**: 应用服务处理写操作
- **查询**: 可直接使用 Repository 读取
- **事件**: 领域事件驱动跨聚合根操作

---

## 三、待完成的工作

### 1. 重构匹配 WebSocket (优先级：高)

**文件**: `turing_test/backend/websocket/match.py`

**任务**:
- 使用 `MatchApplicationService` 替代现有匹配逻辑
- 集成匹配池系统
- 事件驱动匹配结果通知

### 2. 重构游戏 API (优先级：高)

**文件**: `turing_test/backend/api/game.py`

**任务**:
- 使用 `SessionApplicationService` 处理问卷提交
- 使用 `RoomApplicationService` 发送消息
- 使用 `ScoreAggregate` 计算积分

### 3. 重构消息服务 (优先级：中)

**文件**: `turing_test/backend/services/message_service.py`

**任务**:
- 迁移到 `NewMessageService`（基于领域模型）
- 移除对旧 `Session` 模型的依赖
- 使用 `Room.send_message()` 发送消息

### 4. 端到端测试 (优先级：中)

**任务**:
- 创建集成测试用例
- 测试匹配 → 对话 → 结算完整流程
- 验证领域事件正确触发

---

## 四、使用示例

### 1. 请求匹配

```python
from turing_test.backend.application.match_service import MatchApplicationService
from turing_test.backend.domain.repositories import AbstractUnitOfWork

async def request_match(uow: AbstractUnitOfWork, user_id: int, user_score: int):
    service = MatchApplicationService(uow, event_bus)
    
    # 请求匹配
    match = await service.request_match(
        user_id=user_id,
        user_score=user_score,
        preferences={"bot_type": "normal"}
    )
    
    return match
```

### 2. 发送消息

```python
from turing_test.backend.application.room_service import RoomApplicationService

async def send_message(
    room_service: RoomApplicationService,
    room_id: str,
    user_id: int,
    content: str
):
    message = await room_service.send_message(
        room_id=room_id,
        sender_id=user_id,
        sender_type="user",
        content=content,
        is_meta=False
    )
    return message
```

### 3. 积分结算

```python
from turing_test.backend.application.session_service import SessionApplicationService

async def settle_score(
    session_service: SessionApplicationService,
    session_id: str,
    base_score: int = 10,
    confidence: str = "mid",
    meta_count: int = 0,
    is_mid_game: bool = False,
):
    await session_service.settle_score(
        session_id=session_id,
        base_score=base_score,
        confidence_multiplier=2.5 if confidence == "mid" else 1.0,
        meta_multiplier=1.0 + meta_count,
        mid_game_multiplier=2.0 if is_mid_game else 1.0,
        entry_fee=2,
        turn_penalty=0,
        opponent_bonus=0
    )
```

---

## 五、迁移策略

### 阶段 1: 双轨运行 (当前阶段)
- 新表已创建，旧表保持不变
- 新功能使用新领域模型
- 旧功能继续使用旧模型

### 阶段 2: 逐步迁移
1. 迁移匹配流程 → 使用 `MatchAggregate`
2. 迁移消息发送 → 使用 `RoomAggregate`
3. 迁移积分结算 → 使用 `ScoreAggregate`

### 阶段 3: 清理旧代码
- 移除旧 `Session` 表相关代码
- 移除旧 `Message` 表相关代码
- 清理内存状态管理器

---

## 六、技术债务

### 已知问题
1. **Repository 层转换逻辑重复**: ORM ↔ 领域模型转换代码较多，可考虑使用映射库
2. **事件处理器依赖注入**: 需要改进容器注册方式
3. **单元测试覆盖率**: 应用服务层缺少测试

### 改进建议
1. 引入 `mapper` 库简化对象转换
2. 使用工厂模式创建事件处理器
3. 为每个应用服务创建测试用例

---

## 七、下一步行动

1. **立即**: 更新 `websocket/match.py` 使用新 `MatchApplicationService`
2. **本周**: 更新 `api/game.py` 使用新领域模型
3. **下周**: 编写集成测试验证完整流程
4. **月底**: 完成所有旧代码迁移

---

**文档**: `ARCHITECTURE_REBUILD.md` - 详细架构设计  
**实施报告**: `DATA_RESTRUCTURE_IMPLEMENTATION.md` - 数据结构说明
