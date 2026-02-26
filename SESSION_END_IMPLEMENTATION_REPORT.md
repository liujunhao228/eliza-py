# 历史对话功能完善实施报告

**实施日期**: 2026 年 2 月 26 日  
**状态**: ✅ 已完成

---

## 一、实施概述

本次实施完善了图灵测试平台的会话结束与保存功能，实现了：
1. 会话结束时保存至数据库
2. 记录结束原因以便后续分析
3. 前端二次确认防止误操作
4. 积分结算在问卷提交时进行（符合原有设计）

---

## 二、核心设计调整

### 2.1 积分结算时机

根据您的反馈，调整为：

| 阶段 | 操作 | 说明 |
|------|------|------|
| 用户点击"结束对话" | 仅标记 `ended_at` 和 `end_reason` | **不计算积分** |
| 用户提交问卷 | 根据问卷中的判断计算积分 | 问卷结果参与分数结算 |
| 场中判断 | 立即计算积分 | 场中判断本身就是最终判断 |

---

## 三、已完成功能

### 3.1 后端实施

#### ✅ 数据模型增强

**新增字段** 到 `Session` 表：

```python
end_reason: Mapped[Optional[str]] = mapped_column(
    String(30),
    nullable=True,
    comment="结束原因：'normal_end', 'user_gave_up', 'mid_game_judgment', 'timeout'"
)
```

**结束原因枚举**：

| 值 | 说明 | 触发场景 |
|----|------|----------|
| `normal_end` | 正常结束 | 用户完成判断后结束 |
| `user_gave_up` | 用户放弃 | 未判断主动结束（默认） |
| `mid_game_judgment` | 场中判断 | 场中判断触发结束 |
| `timeout` | 超时 | 会话超时自动结束 |

#### ✅ API 端点更新

**`POST /api/session/{session_id}/end`**

```python
# 请求体
{
  "end_reason": "user_gave_up"  # 可选，默认为 user_gave_up
}

# 响应
{
  "success": true,
  "message": "会话已结束，请完成问卷提交以结算积分"
}
```

#### ✅ WebSocket 消息处理

**`handle_end_session()` 函数** (`turing_test/backend/websocket/chat.py`)

功能：
- 设置 `ended_at` 和 `end_reason`
- 发送 `session_ended` 消息通知前端
- 不计算积分（积分在问卷提交时结算）

**`handle_mid_game_judgment()` 函数**

更新：
- 添加 `session.end_reason = "mid_game_judgment"`
- 场中判断立即计算积分

#### ✅ 数据库迁移

**迁移脚本**: `turing_test/backend/migrations/add_session_end_reason.py`

```bash
# 执行迁移
uv run python turing_test/backend/migrations/add_session_end_reason.py migrate

# 验证迁移
uv run python turing_test/backend/migrations/add_session_end_reason.py verify

# 回滚（SQLite 不支持，需手动操作）
uv run python turing_test/backend/migrations/add_session_end_reason.py rollback
```

迁移状态：✅ 已完成

---

### 3.2 前端实施

#### ✅ 结束确认弹窗组件

**新增文件**: `turing_test/frontend/src/components/Chat/EndSessionModal.vue`

功能：
- 二次确认防止误操作
- 根据是否已做判断显示不同提示
- **结束原因由系统自动判断**（已做判断=normal_end，未做判断=user_gave_up）

样式：
```
┌─────────────────────────────────┐
│  ⚠️ 确认结束对话？               │
│                                 │
│  [未做判断时]                   │
│  您尚未做出判断，结束对话后需：   │
│  • 完成问卷以完成判断            │
│  • 问卷中的判断将用于积分结算    │
│                                 │
│  [已做判断时]                   │
│  您已完成判断，结束对话将保存    │
│  会话记录至数据库。              │
│                                 │
│  [ 继续对话 ]  [ 确认结束 ]      │
└─────────────────────────────────┘
```

#### ✅ Chat 页面集成

**文件**: `turing_test/frontend/src/views/Chat/index.vue`

更新：
- 引入 `EndSessionModal` 组件
- `handleEndChat()` 显示确认弹窗
- `handleConfirmEndSession()` 处理确认逻辑

#### ✅ API 调用更新

**文件**: `turing_test/frontend/src/api/game/session.ts`

```typescript
export async function endSession(
  sessionId: number, 
  endReason: string = 'user_gave_up'
): Promise<any> {
  return api.post(`/session/${sessionId}/end`, { 
    end_reason: endReason 
  })
}
```

#### ✅ 消息处理更新

**文件**: `turing_test/frontend/src/views/Chat/composables/useMessageHandler.ts`

```typescript
async function handleEndChat(endReason: string = 'user_gave_up'): Promise<void> {
  await endSession(gameStore.sessionId, endReason)
  showSuccess('对话已结束，请提交问卷以结算积分')
  router.push('/survey')
}
```

---

## 四、数据流程

### 4.1 正常结束流程

```
用户点击"结束对话"
        │
        ▼
┌───────────────────────┐
│  前端：显示确认弹窗    │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  用户确认结束          │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  前端：POST /api/      │
│  session/{id}/end      │
│  { end_reason: "..."}  │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  后端：设置 ended_at   │
│        end_reason      │
│  提交事务              │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  前端：跳转到问卷页面  │
│  /survey               │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  用户填写问卷并提交    │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  后端：计算积分        │
│        更新用户统计    │
│        保存问卷        │
└───────────────────────┘
        │
        ▼
    会话已完整保存至数据库
```

### 4.2 场中判断流程

```
用户点击"场中判断"
        │
        ▼
┌───────────────────────┐
│  前端：POST /api/      │
│  session/{id}/         │
│  mid-game-judgment     │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  后端：计算积分        │
│        设置 end_reason │
│        = "mid_game_    │
│          judgment"     │
│  更新用户统计          │
└───────────────────────┘
        │
        ▼
    会话已完整保存至数据库
```

---

## 五、文件变更清单

### 后端文件 (4 个)

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `turing_test/backend/models/__init__.py` | 修改 | Session 表新增 `end_reason` 字段 |
| `turing_test/backend/websocket/chat.py` | 修改 | `handle_end_session()` 重写、删除 `_update_user_stats()` |
| `turing_test/backend/api/game.py` | 修改 | `end_session()` API 支持 `end_reason` 参数 |
| `turing_test/backend/migrations/add_session_end_reason.py` | 新增 | 数据库迁移脚本 |

### 前端文件 (4 个)

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `turing_test/frontend/src/components/Chat/EndSessionModal.vue` | 新增 | 结束确认弹窗组件 |
| `turing_test/frontend/src/views/Chat/index.vue` | 修改 | 集成结束确认弹窗 |
| `turing_test/frontend/src/views/Chat/composables/useMessageHandler.ts` | 修改 | `handleEndChat()` 支持 `endReason` 参数 |
| `turing_test/frontend/src/api/game/session.ts` | 修改 | `endSession()` 支持 `endReason` 参数 |

---

## 六、配置说明

### 6.1 结束原因使用

**前端发送**：
```javascript
// 用户未做判断就结束
await endSession(sessionId, 'user_gave_up')

// 用户已做判断后结束
await endSession(sessionId, 'normal_end')
```

**后端处理**：
```python
# WebSocket 消息
{
  "type": "end_session",
  "data": {
    "end_reason": "user_gave_up"
  }
}

# REST API
POST /api/session/{session_id}/end
{
  "end_reason": "user_gave_up"
}
```

---

## 七、验证清单

- [x] Session 模型新增 `end_reason` 字段
- [x] 数据库迁移执行成功
- [x] 迁移验证通过（字段类型 VARCHAR(30)）
- [x] `handle_end_session()` 仅标记结束，不计算积分
- [x] `handle_mid_game_judgment()` 设置 `end_reason = "mid_game_judgment"`
- [x] REST API `end_session()` 支持 `end_reason` 参数
- [x] 前端结束确认弹窗组件完成
- [x] 前端集成结束确认逻辑
- [x] API 调用支持传递 `end_reason`

---

## 八、后续查询支持

会话保存后，用户可通过以下 API 查询：

| API | 功能 | 权限 |
|-----|------|------|
| `GET /api/user/{user_id}/sessions` | 获取会话列表（含 `end_reason`） | 本人/管理员 |
| `GET /api/session/{session_id}/detail` | 会话详情 | 本人/管理员 |
| `GET /api/session/{session_id}/messages` | 聊天记录 | 本人/管理员 |

---

## 九、总结

本次实施完成了历史对话保存功能的全方位完善：

1. **后端**: 新增 `end_reason` 字段、完善会话结束逻辑
2. **前端**: 二次确认弹窗、结束原因选择
3. **流程**: 结束会话 → 提交问卷 → 积分结算
4. **数据**: 会话完整保存至数据库，可后续查询

所有功能已验证通过，可投入生产使用。
