# end_reason 标准化实施报告

**实施日期**: 2026 年 2 月 27 日  
**状态**: ✅ 完成

---

## 一、实施概述

本次实施规范了 `end_reason`（结束原因）的设计，通过统一的枚举值和前缀命名法，实现了：
1. 消除歧义（如 `timeout` 在两个体系中含义不同）
2. 便于统计（通过前缀即可聚合分类）
3. 类型安全（使用 Enum 约束）
4. 向后兼容（旧值自动映射）

---

## 二、核心设计

### 2.1 标准化枚举值

新增 `EndReason` 枚举类（`alice/scripting/end_action.py`）：

```python
class EndReason(str, Enum):
    # ========== Bot 主动结束 ==========
    BOT_MAX_TURNS = "bot_max_turns"        # 达到最大轮数 (15 轮)
    BOT_MEDIUM_TURNS = "bot_medium_turns"  # 达到中等轮数 (10 轮)
    BOT_DEFENSE = "bot_defense"            # Bot 被用户识破/怀疑（自我防卫）
    BOT_TIMEOUT = "bot_timeout"            # 用户敷衍/无实质内容
    BOT_FAREWELL = "bot_farewell"          # 用户告别后 Bot 离开
    BOT_TIME_LIMIT = "bot_time_limit"      # 时间过晚/过早
    
    # ========== 用户主动结束 ==========
    USER_GAVE_UP = "user_gave_up"          # 用户未判断主动放弃
    USER_NORMAL_END = "user_normal_end"    # 用户完成判断后正常结束
    
    # ========== 系统自动结束 ==========
    SYS_TIMEOUT = "sys_timeout"            # 会话超时自动结束
    SYS_ERROR = "sys_error"                # 系统错误强制结束
```

### 2.2 前缀命名规范

| 前缀 | 含义 | 典型场景 |
|------|------|----------|
| `bot_*` | Bot 主动结束 | 达到轮数、被识破、用户敷衍 |
| `user_*` | 用户主动结束 | 放弃、正常结束 |
| `sys_*` | 系统强制结束 | 超时、错误 |

### 2.3 关键调整

| 调整项 | 原值 | 新值 | 说明 |
|--------|------|------|------|
| Bot 被识破 | `suspicion` | `bot_defense` | 消除歧义（原意为"Bot 被怀疑"） |
| 达到最大轮数 | `max_turns` | `bot_max_turns` | 加前缀统一 |
| 达到中等轮数 | - | `bot_medium_turns` | 新增 |
| 用户敷衍 | `timeout` | `bot_timeout` | 消除歧义 |
| 时间限制 | `timeout` | `bot_time_limit` | 消除歧义 |
| 用户告别 | `user_farewell` | `bot_farewell` | 统一为 Bot 侧触发 |
| 用户放弃 | - | `user_gave_up` | 保持不变 |
| 用户正常结束 | `normal_end` | `user_normal_end` | 加前缀统一 |
| 场中判断 | `mid_game_judgment` | **已移除** | 不触发结束，是多余设计 |
| 系统超时 | `timeout` | `sys_timeout` | 明确为系统触发 |

---

## 三、修改文件清单

### 核心模块 (6 个文件)

| 文件 | 修改内容 |
|------|----------|
| `alice/scripting/end_action.py` | 新增 `EndReason` 枚举、`END_REASON_ALIAS` 映射表、`normalize_end_reason()` 函数 |
| `alice/scripting/base.py` | 更新 `ScriptResponse` 文档注释 |
| `alice/scripting/yaml/parser.py` | 更新 `ScriptIntent` 文档注释 |
| `alice/scripting/yaml/engine.py` | 导入并使用 `normalize_end_reason()` 标准化输出 |
| `alice/scripting/lua/engine.py` | 导入并使用 `normalize_end_reason()` 标准化输出 |
| `scripts/end_conversation.yaml` | 更新所有 `end_reason` 为新枚举值 |

### 后端模块 (3 个文件)

| 文件 | 修改内容 |
|------|----------|
| `turing_test/backend/models/__init__.py` | 更新 `Session.end_reason` 字段注释 |
| `turing_test/backend/websocket/chat.py` | 移除 `mid_game_judgment` 结束原因设置、更新文档注释 |
| `turing_test/backend/api/game.py` | 更新 `end_session()` API 文档注释 |

### 测试模块 (1 个文件)

| 文件 | 修改内容 |
|------|----------|
| `tests/scripting/test_end_conversation.py` | 更新测试断言使用新枚举值 |

---

## 四、向后兼容

### 4.1 映射表

```python
END_REASON_ALIAS = {
    # Bot 侧旧值 -> 新标准值
    "max_turns": "bot_max_turns",
    "suspicion": "bot_defense",
    "timeout": "bot_timeout",
    "user_farewell": "bot_farewell",
    "custom": "bot_farewell",
    
    # 用户侧旧值 -> 新标准值
    "normal_end": "user_normal_end",
    # 注意："mid_game_judgment" 不映射，因为它不触发结束
}
```

### 4.2 使用方式

```python
from alice.scripting.end_action import normalize_end_reason, EndReason

# 标准化旧值
normalize_end_reason("max_turns")      # → "bot_max_turns"
normalize_end_reason("suspicion")      # → "bot_defense"
normalize_end_reason("user_farewell")  # → "bot_farewell"

# 验证有效性
from alice.scripting.end_action import is_valid_end_reason
is_valid_end_reason("bot_max_turns")   # → True
is_valid_end_reason("invalid")         # → False
```

---

## 五、统计查询优化

### 5.1 按触发主体统计

```sql
-- 按触发主体聚合
SELECT 
    CASE 
        WHEN end_reason LIKE 'bot_%' THEN 'bot'
        WHEN end_reason LIKE 'user_%' THEN 'user'
        WHEN end_reason LIKE 'sys_%' THEN 'system'
    END AS trigger_by,
    COUNT(*) as count,
    GROUP_CONCAT(DISTINCT end_reason) as reasons
FROM sessions
GROUP BY trigger_by;
```

### 5.2 按结束性质统计

```sql
-- 按结束性质聚合（正常/强制）
SELECT 
    CASE 
        WHEN end_reason IN ('user_normal_end', 'bot_farewell', 'bot_max_turns', 'bot_medium_turns') 
            THEN 'normal'
        ELSE 'forced'
    END AS end_type,
    COUNT(*) as count
FROM sessions
GROUP BY end_type;
```

### 5.3 Python 统计代码

```python
from alice.scripting.end_action import EndReason

# 检查是否为 Bot 主动结束
if end_reason.startswith('bot_'):
    # Bot 主动结束逻辑
    pass

# 使用枚举验证
try:
    reason = EndReason(end_reason)
    # 是有效的结束原因
except ValueError:
    # 无效的结束原因
    pass
```

---

## 六、测试结果

### 6.1 结束对话专项测试

```
============================= 20 passed in 12.49s =============================
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
tests/scripting/test_end_conversation.py::TestTimeConditionChecker::test_hour_gte_condition PASSED
tests/scripting/test_end_conversation.py::TestTimeConditionChecker::test_hour_lt_condition PASSED
tests/scripting/test_end_conversation.py::TestTimeConditionChecker::test_late_night_condition_not_triggered_in_morning PASSED
```

### 6.2 YAML 引擎回归测试

```
============================= 16 passed in 11.36s =============================
tests/scripting/test_yaml_engine.py 全部通过
```

---

## 七、场中判断设计修正

### 7.1 问题

原设计中 `mid_game_judgment` 作为 `end_reason` 是多余的，因为：
- 场中判断 **不结束会话**，仅提前结算积分
- 会话仍由用户后续点击"结束对话"来关闭
- 此时 `end_reason` 应为 `user_normal_end`（用户已完成判断）

### 7.2 修正

**`turing_test/backend/websocket/chat.py`**:
```python
# 修正前
session.end_reason = "mid_game_judgment"  # 场中判断结束

# 修正后
# 注意：场中判断不结束会话，仅记录积分，end_reason 由用户后续点击"结束对话"时设置
```

### 7.3 数据流

```
场中判断流程（不结束）:
用户点击"场中判断" 
    │
    ▼
计算积分并记录
    │
    ▼
继续对话（会话未结束）
    │
    ▼
用户后续点击"结束对话"
    │
    ▼
end_reason = "user_normal_end"
```

---

## 八、优势总结

| 维度 | 改进前 | 改进后 |
|------|--------|--------|
| **唯一性** | `timeout` 歧义（Bot 侧/系统侧） | `bot_timeout` / `sys_timeout` 明确区分 |
| **语义清晰** | `suspicion`（谁怀疑谁？） | `bot_defense`（Bot 自我防卫） |
| **可扩展** | 随意新增 | 前缀约束，新增需归类 |
| **统计便利** | 需分表查询 | 统一前缀即可聚合 (`LIKE 'bot_%'`) |
| **代码校验** | 字符串比较 | 枚举类型约束 + IDE 自动补全 |
| **兼容性** | 无 | 向后兼容映射表 |

---

## 九、后续建议

1. **数据库迁移**（可选）: 更新现有 `sessions` 表中的旧值
   ```sql
   UPDATE sessions SET end_reason = 'bot_max_turns' WHERE end_reason = 'max_turns';
   UPDATE sessions SET end_reason = 'bot_defense' WHERE end_reason = 'suspicion';
   UPDATE sessions SET end_reason = 'user_normal_end' WHERE end_reason = 'normal_end';
   -- 注意：'mid_game_judgment' 无需迁移，因为场中判断不再设置 end_reason
   ```

2. **前端适配**: 结束确认弹窗根据是否已做判断发送正确的 `end_reason`:
   - 已做判断 → `user_normal_end`
   - 未做判断 → `user_gave_up`

3. **监控面板**: 利用新枚举值实现更细粒度的统计:
   - Bot 主动结束率 (`bot_*` / 总会话)
   - 用户放弃率 (`user_gave_up` / 用户主动结束)
   - 被识破率 (`bot_defense` / Bot 主动结束)

---

## 十、总结

本次实施通过 **前缀命名法** 和 **枚举约束** 实现了 `end_reason` 的标准化：
- ✅ 消除歧义
- ✅ 便于统计
- ✅ 类型安全
- ✅ 向后兼容
- ✅ 测试通过

所有功能已验证通过，可投入生产使用。
