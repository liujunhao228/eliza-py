# WebSocket 心跳检测统一重构报告

**日期**: 2026 年 2 月 26 日  
**方案**: 方案 A（单向心跳）

---

## 一、重构目标

统一前后端 WebSocket 心跳检测机制，消除双向心跳造成的冗余和职责不清。

---

## 二、设计方案

### 架构

```
┌─────────────┐                    ┌─────────────┐
│   前端       │                    │   后端       │
│             │                    │             │
│             │ ◄───── ping ─────  │  每 30s 发送  │
│             │                    │             │
│   pong ─────► │                    │  更新心跳   │
│             │                    │             │
│             │                    │  90s 超时断开│
└─────────────┘                    └─────────────┘
```

### 原则

- **后端主动**: 后端每 30 秒主动向所有活跃连接发送 `ping`
- **前端被动**: 前端仅在收到 `ping` 时响应 `pong`，不主动发起心跳
- **超时断开**: 后端 90 秒未收到 `pong` 则强制断开连接

---

## 三、变更清单

### 前端 (`turing_test/frontend/src/api/game/websocket.ts`)

| 变更 | 说明 |
|------|------|
| ❌ 移除 `heartbeatTimer` 属性 | 不再需要客户端心跳定时器 |
| ❌ 移除 `startHeartbeat()` 方法 | 移除主动心跳逻辑 |
| ❌ 移除 `stopHeartbeat()` 方法 | 移除停止心跳逻辑 |
| ❌ 移除 `onopen` 中的 `this.startHeartbeat()` | 连接成功后不再启动心跳 |
| ❌ 移除 `onclose` 中的 `this.stopHeartbeat()` | 断开时不再停止心跳 |
| ❌ 移除 `disconnect()` 中的 `this.stopHeartbeat()` | 断开时不再停止心跳 |
| ✅ 保留 `ping` 响应逻辑 | 收到 `ping` 时响应 `pong` |
| ✅ 更新注释 | `heartbeatInterval: 0` 注释改为"由后端单向发起心跳" |

### 后端 (`turing_test/backend/websocket/manager.py`)

| 变更 | 说明 |
|------|------|
| ✅ `ConnectionManager.__init__` 新增参数 | `heartbeat_interval` (默认 30s)、`heartbeat_timeout` (默认 90s) |
| ✅ 新增统计字段 | `heartbeat_sent_count`、`heartbeat_timeout_count` |
| ✅ `_heartbeat_loop` 增加计数 | 发送心跳和超时断开时累加统计 |
| ✅ `get_statistics()` 新增字段 | 返回心跳统计数据 |
| ✅ 全局实例配置化 | `manager = ConnectionManager(heartbeat_interval=30, heartbeat_timeout=90)` |

### 类型定义 (`turing_test/frontend/src/types/game.ts`)

| 变更 | 说明 |
|------|------|
| ✅ 更新 `WebSocketConfig.heartbeatInterval` 注释 | "0 表示由后端单向发起心跳" |

---

## 四、配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `heartbeat_interval` | 30 秒 | 后端发送 ping 的间隔 |
| `heartbeat_timeout` | 90 秒 | 未收到 pong 的超时阈值（3 次心跳间隔） |

---

## 五、消息协议

| 消息类型 | 方向 | 触发条件 | 响应 |
|----------|------|----------|------|
| `ping` | 后端→前端 | 每 30 秒 | `pong` |
| `pong` | 前端→后端 | 收到 `ping` | 无 |

---

## 六、监控指标

后端 `get_statistics()` 新增字段：

```json
{
  "heartbeat_sent_count": 0,      // 累计发送心跳次数
  "heartbeat_timeout_count": 0    // 累计心跳超时断开次数
}
```

---

## 七、测试建议

1. **连接保持测试**: 验证连接在空闲状态下能保持活跃
2. **超时断开测试**: 验证前端不响应 pong 时后端 90 秒后断开
3. **重连测试**: 验证心跳超时断开后重连机制正常
4. **并发测试**: 验证多连接场景下心跳监控正常

---

## 八、优势

| 优势 | 说明 |
|------|------|
| **职责清晰** | 后端统一管理连接健康状态 |
| **减少冗余** | 消息量减少 50%（仅单向 ping） |
| **易于调试** | 单一心跳源便于问题定位 |
| **配置灵活** | 后端可统一调整心跳参数 |

---

## 九、文件清单

| 文件 | 变更类型 |
|------|----------|
| `turing_test/frontend/src/api/game/websocket.ts` | 修改 |
| `turing_test/backend/websocket/manager.py` | 修改 |
| `turing_test/frontend/src/types/game.ts` | 修改 |

---

**重构完成** ✅
