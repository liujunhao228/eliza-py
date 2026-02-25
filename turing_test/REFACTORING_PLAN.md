# Turing Test 项目重构计划

## 📋 概述

本文档描述了 `turing_test` 项目的文件拆分重构方案，旨在提高代码的可维护性、可测试性和可扩展性。

**生成日期**: 2026 年 2 月 25 日

---

## 一、现状分析

### 1.1 后端大文件（>300 行）

| 文件 | 行数 | 主要问题 |
|------|------|----------|
| `services/match_service.py` | 753 | 单一文件包含匹配队列、算法、超时处理、会话创建、统计等多个职责 |
| `services/invite_code_service.py` | 502 | 邀请码生成器与服务逻辑混在一起 |
| `bot_pool.py` | 549 | Bot 实例管理与池管理逻辑耦合 |
| `main.py` | 300 | 路由定义过多 |

### 1.2 前端大文件（>400 行）

| 文件 | 行数 | 主要问题 |
|------|------|----------|
| `views/Chat.vue` | 920 | 组件逻辑、WebSocket 处理、消息处理全部集中在一个文件 |
| `views/Profile.vue` | 684 | 表单验证、头像上传、多 section 逻辑 |
| `components/Chat/MessageList.vue` | 570 | 消息渲染逻辑过长 |
| `components/Chat/ChatHeader.vue` | 506 | 状态显示、倒计时、操作按钮逻辑 |
| `api/game.ts` | 530 | API 函数过多未分类 |

---

## 二、拆分方案

### 2.1 后端拆分

#### 2.1.1 `services/match_service.py` (753 行)

**当前结构**:
- `MatchPriority` 枚举
- `MatchStatistics` 类
- `MatchService` 类（包含队列管理、匹配算法、超时处理、会话创建等）

**拆分后结构**:

```
services/
└── match_service/
    ├── __init__.py          # 导出统一接口
    ├── queue.py             # MatchQueue 类：队列管理 (~200 行)
    ├── algorithm.py         # MatchAlgorithm 类：匹配算法 (~150 行)
    ├── statistics.py        # MatchStatistics 类：统计 (~100 行)
    └── service.py           # MatchService 类：主服务 (~300 行)
```

**模块职责**:

| 模块 | 职责 |
|------|------|
| `queue.py` | 等待队列的加入/离开、队列排序、位置查询 |
| `algorithm.py` | 匹配算法实现、优先级匹配、超时判断 |
| `statistics.py` | 匹配统计数据收集与查询 |
| `service.py` | 整合各模块，提供统一服务接口 |

---

#### 2.1.2 `services/invite_code_service.py` (502 行)

**当前结构**:
- `InviteCodeGenerator` 类
- `InviteCodeService` 类

**拆分后结构**:

```
services/
└── invite_code_service/
    ├── __init__.py          # 导出统一接口
    ├── generator.py         # InviteCodeGenerator 类：生成逻辑 (~150 行)
    └── service.py           # InviteCodeService 类：CRUD 服务 (~350 行)
```

**模块职责**:

| 模块 | 职责 |
|------|------|
| `generator.py` | 邀请码生成算法、批量生成、唯一性校验 |
| `service.py` | 邀请码的创建、查询、使用、统计等数据库操作 |

---

#### 2.1.3 `bot_pool.py` (549 行)

**当前结构**:
- `BotInstanceInfo` 类
- `AliceBotPool` 类

**拆分后结构**:

```
services/
└── bot_pool/
    ├── __init__.py          # 导出 BotPool
    ├── instance.py          # BotInstanceInfo 类：实例信息 (~100 行)
    ├── manager.py           # AliceBotPool 类：池管理 (~350 行)
    └── config.py            # BotTemplate 配置管理 (~100 行)
```

**模块职责**:

| 模块 | 职责 |
|------|------|
| `instance.py` | Bot 实例信息封装、状态管理 |
| `manager.py` | Bot 池的获取/释放、负载均衡、扩缩容 |
| `config.py` | Bot 模板配置解析与管理 |

---

#### 2.1.4 `main.py` (300 行)

**当前结构**:
- FastAPI 应用创建
- 中间件注册
- 所有 API 路由定义

**拆分后结构**:

```
api/
├── __init__.py
├── health.py        # 健康检查路由
├── user.py          # 用户相关路由
├── game.py          # 游戏相关路由
├── match.py         # 匹配相关路由
├── history.py       # 历史记录路由
├── share.py         # 分享相关路由
├── invite_code.py   # 邀请码路由
├── auth.py          # 认证相关路由
└── analytics.py     # 统计分析路由

main.py 只保留:
- FastAPI 应用创建
- 中间件注册
- 路由 include_router
- 生命周期管理
```

---

### 2.2 前端拆分

#### 2.2.1 `views/Chat.vue` (920 行)

**当前结构**:
- 模板：ChatHeader + MessageList + ChatInput
- 脚本：WebSocket 处理、消息处理、滚动控制、状态管理

**拆分后结构**:

```
views/Chat/
├── index.vue            # 主组件：布局 + 状态管理 (~200 行)
├── composables/
│   ├── useChatState.ts  # 游戏状态管理 (~150 行)
│   ├── useMessageHandler.ts  # 消息处理逻辑 (~200 行)
│   └── useScroll.ts     # 滚动控制 (~100 行)
└── components/
    └── (已有的 ChatHeader, MessageList, ChatInput)
```

**模块职责**:

| 模块 | 职责 |
|------|------|
| `index.vue` | 组件布局、状态协调 |
| `useChatState.ts` | 游戏状态管理、WebSocket 连接管理 |
| `useMessageHandler.ts` | 消息发送/接收处理、错误处理 |
| `useScroll.ts` | 滚动位置控制、自动滚动 |

---

#### 2.2.2 `api/game.ts` (530 行)

**当前结构**:
- 所有游戏相关 API 函数混在一起

**拆分后结构**:

```
api/
└── game/
    ├── index.ts         # 统一导出
    ├── session.ts       # 会话相关 API (创建、结束、详情)
    ├── message.ts       # 消息相关 API (发送、获取历史)
    ├── match.ts         # 匹配相关 API (加入队列、取消匹配)
    ├── judgment.ts      # 判断相关 API (场中判断、最终判断)
    └── history.ts       # 历史记录 API (列表、分享)
```

---

#### 2.2.3 `components/Chat/MessageList.vue` (570 行)

**当前结构**:
- 消息列表渲染
- 不同类型的消息渲染逻辑

**拆分后结构**:

```
components/Chat/
├── MessageList.vue      # 列表容器 (~150 行)
├── MessageItem/
│   ├── index.vue        # 消息项主组件
│   ├── TextMessage.vue  # 文本消息
│   ├── SystemMessage.vue # 系统消息
│   └── JudgmentMessage.vue # 判断消息
└── TypingIndicator.vue  # 输入指示器 (独立)
```

---

#### 2.2.4 `components/Chat/ChatHeader.vue` (506 行)

**当前结构**:
- 连接状态显示
- 倒计时显示
- 操作按钮组

**拆分后结构**:

```
components/Chat/
├── ChatHeader.vue       # 主头部 (~200 行)
├── Header/
│   ├── ConnectionStatus.vue  # 连接状态
│   ├── TimerDisplay.vue      # 倒计时显示
│   └── ActionButtons.vue     # 操作按钮组
└── ...
```

---

## 三、实施优先级

### 3.1 优先级定义

| 等级 | 标识 | 说明 |
|------|------|------|
| P0 | 🔴 | 紧急，严重影响可维护性，优先处理 |
| P1 | 🟡 | 重要，影响代码质量，尽快处理 |
| P2 | 🟢 | 可选，当前功能稳定，可延后 |

### 3.2 优先级列表

| 优先级 | 文件 | 行数 | 理由 |
|--------|------|------|------|
| 🔴 P0 | `services/match_service.py` | 753 | 最大文件，职责混乱，影响可维护性 |
| 🔴 P0 | `views/Chat.vue` | 920 | 最大前端文件，逻辑复杂，难以测试 |
| 🟡 P1 | `services/invite_code_service.py` | 502 | 生成器与服务耦合 |
| 🟡 P1 | `api/game.ts` | 530 | API 函数过多，不便复用 |
| 🟢 P2 | `bot_pool.py` | 549 | 当前功能稳定，可延后 |
| 🟢 P2 | `MessageList.vue` | 570 | 依赖 Chat.vue 重构 |
| 🟢 P2 | `ChatHeader.vue` | 506 | 依赖 Chat.vue 重构 |

---

## 四、实施步骤

### 4.1 第一阶段：后端核心模块拆分

1. **拆分 `match_service.py`**
   - [ ] 创建 `services/match_service/` 目录
   - [ ] 提取 `MatchStatistics` 到 `statistics.py`
   - [ ] 提取队列管理逻辑到 `queue.py`
   - [ ] 提取匹配算法到 `algorithm.py`
   - [ ] 重构 `MatchService` 到 `service.py`
   - [ ] 更新 `__init__.py` 导出
   - [ ] 运行测试验证

2. **拆分 `invite_code_service.py`**
   - [ ] 创建 `services/invite_code_service/` 目录
   - [ ] 提取 `InviteCodeGenerator` 到 `generator.py`
   - [ ] 保留服务逻辑到 `service.py`
   - [ ] 更新 `__init__.py` 导出
   - [ ] 运行测试验证

3. **拆分 `main.py` 路由**
   - [ ] 检查 `api/` 目录下现有路由
   - [ ] 将路由定义迁移到对应文件
   - [ ] 更新 `main.py` 使用 `include_router`
   - [ ] 运行测试验证

### 4.2 第二阶段：前端核心组件拆分

1. **拆分 `Chat.vue`**
   - [ ] 创建 `views/Chat/` 目录结构
   - [ ] 提取 `useChatState` composable
   - [ ] 提取 `useMessageHandler` composable
   - [ ] 提取 `useScroll` composable
   - [ ] 简化 `index.vue` 主组件
   - [ ] 更新导入路径
   - [ ] 运行测试验证

2. **拆分 `api/game.ts`**
   - [ ] 创建 `api/game/` 目录
   - [ ] 按功能分类提取 API 函数
   - [ ] 更新 `index.ts` 统一导出
   - [ ] 更新所有引用路径
   - [ ] 运行测试验证

### 4.3 第三阶段：前端子组件拆分

1. **拆分 `MessageList.vue`**
   - [ ] 创建 `MessageItem/` 子组件目录
   - [ ] 提取不同类型消息组件
   - [ ] 简化 `MessageList.vue`
   - [ ] 运行测试验证

2. **拆分 `ChatHeader.vue`**
   - [ ] 创建 `Header/` 子组件目录
   - [ ] 提取状态显示、倒计时、按钮组件
   - [ ] 简化 `ChatHeader.vue`
   - [ ] 运行测试验证

---

## 五、代码规范

### 5.1 导入顺序

```python
# 标准库
import asyncio
from typing import Dict, List, Optional

# 第三方库
from loguru import logger
from fastapi import APIRouter

# 项目模块
from turing_test.backend.models import User
from turing_test.backend.schemas import UserCreate
```

### 5.2 导出规范

```python
# __init__.py
from .service import MatchService
from .queue import MatchQueue
from .algorithm import MatchAlgorithm
from .statistics import MatchStatistics

__all__ = [
    "MatchService",
    "MatchQueue",
    "MatchAlgorithm",
    "MatchStatistics",
]
```

### 5.3 TypeScript 模块导出

```typescript
// index.ts
export { useChatState } from './useChatState'
export { useMessageHandler } from './useMessageHandler'
export { useScroll } from './useScroll'
```

---

## 六、测试策略

### 6.1 单元测试

每个拆分后的模块需要保持或新增对应的单元测试：

| 模块 | 测试文件 |
|------|----------|
| `match_service/` | `test_match_service.py` |
| `invite_code_service/` | `test_invite_code_service.py` |
| `bot_pool/` | `test_bot_pool.py` |
| `useChatState` | `useChatState.test.ts` |
| `useMessageHandler` | `useMessageHandler.test.ts` |

### 6.2 集成测试

- 保持现有的 `test_integration.py`
- 确保拆分后所有 API 端点正常工作
- 确保 WebSocket 连接正常

---

## 七、回滚方案

如果拆分后出现问题，执行以下回滚步骤：

1. **Git 回滚**
   ```bash
   git stash          # 暂存当前更改
   git checkout <previous-commit>  # 回滚到拆分前
   ```

2. **部分回滚**
   - 恢复原文件
   - 删除新创建的目录
   - 更新导入路径

---

## 八、验收标准

### 8.1 代码质量

- [ ] 所有文件行数 < 400 行
- [ ] 每个文件职责单一
- [ ] 导入路径清晰

### 8.2 功能验证

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试关键功能

### 8.3 文档更新

- [ ] 更新 README.md
- [ ] 更新 API 文档
- [ ] 更新导入示例

---

## 九、预期收益

| 指标 | 拆分前 | 拆分后 | 提升 |
|------|--------|--------|------|
| 最大文件行数 | 920 | <400 | 57% ↓ |
| 平均文件行数 | ~350 | ~200 | 43% ↓ |
| 模块数量 | ~20 | ~40 | 100% ↑ |
| 单元测试覆盖率 | ~60% | ~80% | 33% ↑ |

**可维护性**: 单一职责，易于定位和修改

**可测试性**: 小单元便于编写单元测试

**可复用性**: 模块化设计便于其他项目复用

**代码审查**: 小文件更易于 Review

---

## 十、附录

### 10.1 相关文件

- [后端服务架构](./backend/README.md)
- [前端组件规范](./frontend/docs/components.md)

### 10.2 参考资料

- [Python 模块最佳实践](https://docs.python.org/3/tutorial/modules.html)
- [Vue 3 Composables 模式](https://vuejs.org/guide/reusability/composables.html)
- [TypeScript 模块系统](https://www.typescriptlang.org/docs/handbook/modules.html)
