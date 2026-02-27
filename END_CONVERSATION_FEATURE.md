# Bot 主动结束对话功能实现报告

**日期**: 2026 年 2 月 27 日  
**状态**: ✅ 完成
**修复**: 时间条件检查（2026-02-27 08:50）

---

## 概述

实现了 Bot 主动结束对话的功能，使 Bot 能够更拟人化地在适当时机结束对话，降低被识破的风险。

---

## 设计原则

1. **真人拟态**: 大多数情况下直接离开（不告别），偶尔告别后离开
2. **向后兼容**: 现有脚本无需修改，`end_action` 默认为 `"none"`
3. **脚本引擎无关**: Lua 和 YAML 引擎使用相同接口

---

## 结束动作类型

| 动作类型 | 说明 | 使用场景 |
|----------|------|----------|
| `none` | 不结束对话（默认） | 正常对话 |
| `direct` | 直接结束，不发送响应 | 达到最大轮数、被怀疑、用户敷衍 |
| `farewell` | 先发送告别语，再结束 | 用户说再见、深夜/清晨 |

---

## 结束原因分类

| 原因 | 触发条件 | 结束动作 |
|------|----------|----------|
| `max_turns` | 达到最大轮数 (15 轮) | direct |
| `suspicion` | 检测到用户怀疑 | direct |
| `timeout` | 用户多轮无实质内容 | direct |
| `user_farewell` | 用户先说再见 | farewell |
| `custom` | 自定义原因 | farewell |

---

## 修改文件列表

### 核心模块

| 文件 | 修改内容 |
|------|----------|
| `alice/scripting/base.py` | `ScriptResponse` 添加 `end_action`, `end_reason` 字段 |
| `alice/scripting/end_action.py` | 新建 `EndAction` 数据类 |
| `alice/scripting/__init__.py` | 导出 `EndAction` |
| `alice/scripting/yaml/parser.py` | `ScriptIntent` 添加 `end_action`, `end_reason` 字段 |
| `alice/scripting/yaml/engine.py` | `generate_response` 传递 `end_action` |
| `alice/scripting/lua/engine.py` | 支持返回 `end_action` |
| `alice/scripting/yaml/condition_checker.py` | **新增 `_check_time` 方法（时间条件检查）** |
| `alice/core/dialogue_engine.py` | `respond` 返回 `(str, Optional[EndAction])` |
| `alice/bots/lightweight_alice_bot.py` | 新增 `respond_with_end_action` 方法 |

### 后端服务

| 文件 | 修改内容 |
|------|----------|
| `turing_test/backend/services/ai_bot_service.py` | `get_response` 返回 `end_action` |
| `turing_test/backend/services/message_service.py` | 处理 `end_action` 并发送结束信号 |

### 脚本配置

| 文件 | 说明 |
|------|------|
| `scripts/end_conversation.yaml` | 新建结束对话脚本（10 种策略） |

### 测试

| 文件 | 说明 |
|------|------|
| `tests/scripting/test_end_conversation.py` | 新建测试（20 个测试用例，全部通过） |

---

## YAML 脚本格式

```yaml
# 直接结束（不发送消息）
- intent: max_turns_end
  priority: 85
  condition:
    min_turns: 15
  end_action: direct
  end_reason: max_turns
  templates:
    - ""  # 占位，direct 模式不发送

# 告别后结束
- intent: user_farewell
  priority: 95
  condition:
    keywords: ["再见", "拜拜", "88"]
  end_action: farewell
  end_reason: user_farewell
  templates:
    - "嗯。"
    - "好。"
    - "行。"
```

---

## 数据流

```
用户输入
    │
    ▼
LightweightAliceBot.respond_with_end_action()
    │
    ▼
DialogueEngine.respond() → (response, EndAction)
    │
    ▼
MessageService._trigger_ai_response()
    │
    ├─► end_action = "direct" ──► 发送 conversation_end ──► 关闭会话
    │
    ├─► end_action = "farewell" ──► 发送告别消息 ──► 发送 conversation_end ──► 关闭会话
    │
    └─► end_action = "none" ──► 正常发送响应 ──► 继续对话
```

---

## WebSocket 消息格式

### 服务器 → 客户端

```json
{
  "type": "conversation_end",
  "data": {
    "action": "direct",
    "reason": "max_turns",
    "session_id": 123
  }
}
```

---

## 结束对话策略（scripts/end_conversation.yaml）

| 策略 | 优先级 | 触发条件 | 动作 |
|------|--------|----------|------|
| `max_turns_end` | 85 | ≥15 轮 | direct |
| `medium_turns_end` | 75 | ≥10 轮 | direct |
| `suspicion_detected` | 90 | 用户怀疑 | direct |
| `user_farewell` | 95 | 用户告别 | farewell |
| `user_timeout` | 70 | 用户敷衍 5 轮 | direct |
| `nonsense_detected` | 65 | 乱打字 3 轮 | direct |
| `late_night_end` | 80 | ≥23 点 | farewell |
| `early_morning_end` | 75 | <6 点 | farewell |
| `user_busy` | 90 | 用户说去忙 | farewell |
| `natural_end` | 60 | 话题结束 | farewell |

---

## 测试结果

```
============================= 17 passed in 11.95s =============================
tests/scripting/test_end_conversation.py::TestScriptResponse::test_default_end_action PASSED
tests/scripting/test_end_conversation.py::TestScriptResponse::test_custom_end_action PASSED
tests/scripting/test_end_conversation.py::TestScriptResponse::test_direct_end_action PASSED
tests/scripting/test_end_conversation.py::TestEndAction::test_default_action PASSED
tests/scripting/test_end_conversation.py::TestEndAction::test_direct_action PASSED
tests/scripting/test_end_conversation.py::TestEndAction::test_farewell_action PASSED
tests/scripting/test_end_conversation.py::TestEndAction::test_from_response PASSED
tests/scripting/test_end_conversation.py::TestEndAction::test_to_dict PASSED
tests/scripting/test_end_conversation.py::TestScriptIntent::test_default_end_action PASSED
tests/scripting/test_end_conversation.py::TestScriptIntent::test_custom_end_action PASSED
tests/scripting/test_end_conversation.py::TestYAMLScriptEngine::test_load_end_conversation_script PASSED
tests/scripting/test_end_conversation.py::TestYAMLScriptEngine::test_parse_max_turns_end_intent PASSED
tests/scripting/test_end_conversation.py::TestYAMLScriptEngine::test_parse_farewell_intent PASSED
tests/scripting/test_end_conversation.py::TestYAMLScriptEngine::test_generate_response_with_end_action PASSED
tests/scripting/test_end_conversation.py::TestDialogueEngineEndAction::test_respond_returns_end_action PASSED
tests/scripting/test_end_conversation.py::TestEndActionScenarios::test_suspicion_detected_end_action PASSED
tests/scripting/test_end_conversation.py::TestEndActionScenarios::test_max_turns_end_action PASSED
```

现有测试（`tests/scripting/test_yaml_engine.py`）：**16 个测试全部通过**

---

## 兼容性说明

### 向后兼容
- 现有 YAML 脚本无需修改，`end_action` 默认为 `"none"`
- `ScriptResponse.text` 有默认值 `""`
- `DialogueEngine.respond()` 旧调用方式仍然有效（返回元组）

### 前端适配
前端需要监听 `conversation_end` 消息类型并处理：
- `action = "direct"`: 直接显示对话结束
- `action = "farewell"`: 先显示告别消息，再显示对话结束

---

## 后续优化建议

1. **动态轮数调整**: 根据对话质量动态调整结束轮数
2. **情绪检测**: 检测用户情绪，在用户不耐烦时主动结束
3. **话题完整性**: 检测话题是否自然结束
4. **个性化**: 不同 Bot 有不同的结束策略配置
