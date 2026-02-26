# 随机延迟增强实现报告

## 实现概述

本次增强解决了 Bot 发送回复和开场白时没有延迟、容易被识破的问题。通过多层延迟配置和拟真行为模拟，使 Bot 行为更接近真实人类。

---

## 实现层级

### 1. 配置层 (`config.turing.yaml`)

新增了完整的延迟配置参数：

```yaml
ai_bot:
  name: 小图
  
  # === 基础延迟 (向后兼容) ===
  typing_delay_base: 1.0              # 基础延迟 (秒)
  
  # === 回复延迟配置（随机范围）===
  reply_delay_min: 1.0                # 最小延迟（秒）
  reply_delay_max: 3.0                # 最大延迟（秒）
  
  # === 开场白延迟配置（随机范围）===
  opening_delay_min: 2.0              # 最小延迟（秒）
  opening_delay_max: 5.0              # 最大延迟（秒）
  
  # === 每字符延迟 ===
  typing_delay_per_char: 0.05         # 每字符额外延迟（秒）
  
  # === 钓鱼机器人延迟配置 ===
  honeypot:
    reply_delay_min: 2.0              # 钓鱼机器人回复更慢
    reply_delay_max: 8.0
    opening_delay_min: 5.0            # 开场白也更慢
    opening_delay_max: 15.0
    
    # 拟真行为：偶尔出现超长延迟（模拟人类分心）
    occasional_long_delay_probability: 0.1
    occasional_long_delay_min: 15.0
    occasional_long_delay_max: 60.0
    
    # 元对话时延迟乘数（模拟思考）
    meta_delay_multiplier: 1.5
    
    # 会话早期延迟乘数（建立人设）
    early_session_delay_multiplier: 1.3
```

---

### 2. AI Bot 服务层 (`turing_test/backend/services/ai_bot_service.py`)

**新增功能：**
- `_load_delay_config()` - 加载延迟配置
- `_calculate_typing_delay()` - 增强的延迟计算方法，支持：
  - 开场白/回复区分
  - 钓鱼机器人拟真行为
  - 元对话延迟加成
  - 会话早期延迟加成

**修改的方法：**
- `get_response()` - 新增参数：`is_opening`, `is_honeypot`, `session_turn_count`, `is_meta`
- `get_bot_response()` - 便捷函数，支持传递新参数

---

### 3. WebSocket 层 (`turing_test/backend/websocket/chat.py`)

**修改的方法：**
- `handle_ai_response()` - 新增开场白检测逻辑：
  - 检测是否为会话第一条消息 (`is_opening = session.turn_count == 0`)
  - 传递延迟参数给 AI Bot 服务
  - 在发送响应前等待延迟 (`await asyncio.sleep(ai_delay)`)

---

### 4. 钓鱼机器人服务层 (`turing_test/backend/services/honeypot_service.py`)

**新增功能：**
- `_calculate_delay_with_config()` - 根据配置计算延迟
- `_get_delay_config()` - 获取延迟配置
- `_get_profile_delay_multiplier()` - 根据行为模式获取延迟乘数

**修改的方法：**
- `get_response_with_delay()` - 新增 `session_turn_count` 参数

**拟真行为特性：**
1. **超长延迟**：10% 概率触发 15-60 秒延迟（模拟人类分心）
2. **元对话延迟**：1.5 倍乘数（模拟思考）
3. **会话早期延迟**：前 5 轮对话 1.3 倍乘数（建立人设）
4. **行为模式乘数**：根据打字速度调整延迟

---

## 延迟计算逻辑

### 普通 AI Bot

```
总延迟 = 基础延迟 + 长度延迟 + 随机波动

基础延迟 = random.uniform(reply_delay_min, reply_delay_max)
长度延迟 = 响应长度 × typing_delay_per_char
随机波动 = random.uniform(-0.2, 0.2) × 总延迟
```

### 钓鱼机器人

```
总延迟 = (基础延迟 + 超长延迟) × 元对话乘数 × 早期乘数 × 行为模式乘数 + 长度延迟 + 随机波动

基础延迟 = random.uniform(reply_delay_min, reply_delay_max)
超长延迟 = 10% 概率触发 random.uniform(15, 60)
元对话乘数 = 1.5 (如果是元对话)
早期乘数 = 1.3 (如果 session_turn_count < 5)
行为模式乘数 = 5.0 / typing_speed_avg (限制在 0.5-2.0)
```

---

## 延迟配置层级

| 层级 | 配置位置 | 优先级 |
|------|---------|--------|
| Bot 模板层 | `BotTemplate.typing_delay_*` | 最高 |
| 全局配置层 | `config.turing.yaml` → `ai_bot.*` | 中等 |
| 默认值 | 代码中硬编码默认值 | 最低 |

---

## 预期效果

| 场景 | 延迟范围 | 说明 |
|------|---------|------|
| 普通 AI 回复 | 1-3 秒 | 基础随机延迟 |
| 普通 AI 开场白 | 2-5 秒 | 稍长延迟避免秒回 |
| 钓鱼机器人回复 | 2-8 秒 | 更长的基础延迟 |
| 钓鱼机器人开场白 | 5-15 秒 | 显著延迟建立人设 |
| 元对话响应 | ×1.5 | 模拟思考时间 |
| 会话早期 (前 5 轮) | ×1.3 | 建立人设 |
| 超长延迟 (10% 概率) | +15-60 秒 | 模拟人类分心 |

---

## 测试覆盖

测试文件：`tests/unit/test_delay_enhancement.py`

**测试覆盖：**
- ✅ 回复延迟范围测试
- ✅ 开场白延迟范围测试
- ✅ 钓鱼机器人延迟更长测试
- ✅ 元对话延迟乘数测试
- ✅ 会话早期延迟乘数测试
- ✅ 长度延迟计算测试
- ✅ 随机波动计算测试
- ✅ 最小延迟边界测试
- ✅ 超长延迟概率测试
- ✅ 行为模式延迟乘数测试
- ✅ 配置加载测试
- ✅ 完整延迟计算流程集成测试

**测试结果：** 16 项测试全部通过

---

## 使用示例

### 在 WebSocket 中调用

```python
from turing_test.backend.services.ai_bot_service import get_bot_response

# 获取 AI 响应（带延迟）
base_response, base_delay = await get_bot_response(
    user_message,
    is_opening=is_opening,          # 是否为开场白
    is_honeypot=session.is_honeypot, # 是否为钓鱼机器人
    session_turn_count=session.turn_count, # 会话轮数
)

# 等待延迟（模拟打字）
await asyncio.sleep(ai_delay)
```

### 在钓鱼机器人服务中调用

```python
from turing_test.backend.services.honeypot_service import get_honeypot_service

honeypot_service = get_honeypot_service()

# 生成带拟真延迟的响应
ai_response, ai_delay = honeypot_service.get_response_with_delay(
    base_response=base_response,
    session_id=session_id,
    is_meta=is_meta,
    user_message=user_message,
    session_turn_count=session.turn_count,
)
```

---

## 配置调整建议

### 调整延迟范围

编辑 `config.turing.yaml`：

```yaml
ai_bot:
  reply_delay_min: 1.5    # 增加最小延迟
  reply_delay_max: 4.0    # 增加最大延迟
```

### 调整钓鱼机器人行为

```yaml
ai_bot:
  honeypot:
    occasional_long_delay_probability: 0.15  # 增加超长延迟概率
    meta_delay_multiplier: 2.0               # 增加元对话延迟
```

### 禁用超长延迟

```yaml
ai_bot:
  honeypot:
    occasional_long_delay_probability: 0.0   # 禁用超长延迟
```

---

## 向后兼容性

- 保留了 `typing_delay_base` 配置项以兼容旧代码
- 新增配置项都有默认值，不影响现有配置
- 配置构建器会检查必填字段，确保配置完整

---

## 下一步优化建议

1. **动态延迟调整**：根据用户行为动态调整延迟
2. **延迟统计分析**：记录延迟分布用于分析优化
3. **A/B 测试支持**：支持不同延迟配置的对比测试
4. **用户反馈集成**：根据用户判断结果调整延迟策略
