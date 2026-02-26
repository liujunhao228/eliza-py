# 随机延迟增强方案

## 问题分析

### 当前问题
1. **Bot 发送回复时没有延迟**，容易被识破为机器
2. **Bot 发送开场白时也没有延迟**，同样的问题
3. 延迟配置分散，缺乏统一管理

### 延迟配置层级分析

| 层级 | 当前配置位置 | 延迟类型 |
|------|-------------|---------|
| **配置层** | `config.turing.yaml` → `ai_bot.typing_delay_*` | 基础延迟参数 |
| **Bot 模板层** | `BotTemplate.typing_delay_*` | 每个 Bot 模板的延迟参数 |
| **服务层** | `AIBotService._calculate_typing_delay()` | 响应延迟计算 |
| **WebSocket 层** | `chat.py::handle_ai_response()` | 开场白延迟、钓鱼机器人延迟 |
| **钓鱼机器人层** | `HoneypotService.get_response_with_delay()` | 拟真延迟 |

---

## 增强方案设计

### 1. 配置层（`config.turing.yaml`）

新增统一的延迟配置参数：

```yaml
ai_bot:
  name: 小图
  
  # === 回复延迟配置（随机范围）===
  reply_delay_min: 1.0          # 最小延迟（秒）
  reply_delay_max: 3.0          # 最大延迟（秒）
  
  # === 开场白延迟配置（随机范围）===
  opening_delay_min: 2.0        # 最小延迟（秒）
  opening_delay_max: 5.0        # 最大延迟（秒）
  
  # === 钓鱼机器人延迟配置（更拟真）===
  honeypot:
    reply_delay_min: 2.0        # 钓鱼机器人回复更慢
    reply_delay_max: 8.0
    opening_delay_min: 5.0      # 开场白也更慢
    opening_delay_max: 15.0
    # 拟真行为：偶尔出现超长延迟（模拟人类分心）
    occasional_long_delay_probability: 0.1
    occasional_long_delay_min: 15.0
    occasional_long_delay_max: 60.0
```

### 2. Bot 模板层（`config/bot_registry.py`）

在 `BotTemplate` 中增加延迟配置字段：

```python
@dataclass
class BotTemplate:
    # ... 现有字段 ...
    
    # 回复延迟配置
    reply_delay_min: float = 1.0
    reply_delay_max: float = 3.0
    
    # 开场白延迟配置
    opening_delay_min: float = 2.0
    opening_delay_max: float = 5.0
```

### 3. 服务层（`ai_bot_service.py`）

增强 `AIBotService` 的延迟计算：

```python
def _calculate_typing_delay(
    self, 
    response: str, 
    is_opening: bool = False,
    is_honeypot: bool = False,
) -> float:
    """
    计算打字延迟，模拟人类打字行为
    
    Args:
        response: AI 响应内容
        is_opening: 是否为开场白
        is_honeypot: 是否为钓鱼机器人
    
    Returns:
        打字延迟（秒）
    """
    # 根据类型选择延迟范围
    if is_honeypot:
        delay_min = self.config.honeypot.reply_delay_min
        delay_max = self.config.honeypot.reply_delay_max
        if is_opening:
            delay_min = self.config.honeypot.opening_delay_min
            delay_max = self.config.honeypot.opening_delay_max
    else:
        delay_min = self.config.reply_delay_min if is_opening else self.config.opening_delay_min
        delay_max = self.config.reply_delay_max if is_opening else self.config.opening_delay_max
    
    # 基础延迟（随机均匀分布）
    base_delay = random.uniform(delay_min, delay_max)
    
    # 根据响应长度增加延迟
    length_delay = len(response) * self.config.typing_delay_per_char
    
    # 钓鱼机器人拟真行为：偶尔超长延迟
    if is_honeypot and random.random() < self.config.honeypot.occasional_long_delay_probability:
        long_delay = random.uniform(
            self.config.honeypot.occasional_long_delay_min,
            self.config.honeypot.occasional_long_delay_max
        )
        base_delay += long_delay
    
    # 总延迟
    total_delay = base_delay + length_delay
    
    # 添加随机波动（±20%）
    jitter = random.uniform(-0.2, 0.2) * total_delay
    total_delay += jitter
    
    # 确保最小延迟
    return max(0.5, total_delay)
```

### 4. WebSocket 层（`chat.py`）

在 `handle_ai_response()` 中增加开场白延迟：

```python
async def handle_ai_response(
    session_id: int,
    user_message: str,
    db: AsyncSession,
):
    """处理 AI 响应"""
    # ... 现有代码 ...
    
    # 获取会话中的用户 ID
    session_users = manager.session_users.get(session_id, set())
    user_ids = list(session_users)
    
    # 检查是否还有在线用户
    if not user_ids or not any(manager.is_user_connected(uid) for uid in user_ids):
        logger.warning(f"会话 {session_id} 中没有在线用户，跳过 AI 响应")
        return
    
    # === 新增：开场白延迟 ===
    # 检测是否为开场白（会话的第一条消息）
    is_opening = session.turn_count == 0
    
    # 发送打字提示
    typing_sent = await manager.send_to_session(session_id, {
        "type": "typing",
        "data": {
            "sender": "opponent",
            "is_typing": True,
        }
    })
    
    # ... 获取 AI 响应 ...
    
    # === 新增：应用延迟 ===
    # 计算延迟（包括开场白延迟）
    ai_delay = self._calculate_typing_delay(
        ai_response,
        is_opening=is_opening,
        is_honeypot=session.is_honeypot,
    )
    
    # 等待延迟
    await asyncio.sleep(ai_delay)
    
    # 发送停止打字提示
    await manager.send_to_session(session_id, {
        "type": "stop_typing",
        "data": {
            "sender": "opponent",
            "is_typing": False,
        }
    })
    
    # 发送 AI 响应
    await manager.send_to_session(session_id, {
        "type": "chat",
        "data": {
            "id": message_id,
            "sender": "opponent",
            "content": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    })
```

### 5. 钓鱼机器人层（`honeypot_service.py`）

增强钓鱼机器人的拟真延迟：

```python
def get_response_with_delay(
    self,
    base_response: str,
    session_id: int,
    is_meta: bool,
    user_message: str,
) -> Tuple[str, float]:
    """
    获取带拟真延迟的响应
    
    Args:
        base_response: 基础 AI 响应
        session_id: 会话 ID
        is_meta: 是否为元对话
        user_message: 用户消息
    
    Returns:
        (响应内容，延迟秒数)
    """
    # 获取会话状态
    session = self._get_session(session_id)
    
    # 基础延迟
    delay = self._calculate_base_delay()
    
    # 元对话时增加延迟（模拟思考）
    if is_meta:
        delay *= self.config.meta_delay_multiplier  # 例如 1.5
    
    # 会话早期增加延迟（建立人设）
    if session.turn_count < 5:
        delay *= self.config.early_session_delay_multiplier  # 例如 1.3
    
    # 偶尔超长延迟（模拟人类分心）
    if random.random() < self.config.occasional_long_delay_probability:
        delay += random.uniform(
            self.config.occasional_long_delay_min,
            self.config.occasional_long_delay_max
        )
    
    # 根据响应长度增加延迟
    length_delay = len(base_response) * self.config.typing_delay_per_char
    delay += length_delay
    
    # 添加随机波动
    jitter = random.uniform(-0.2, 0.2) * delay
    delay += jitter
    
    return base_response, max(1.0, delay)
```

---

## 实现步骤

### 第一步：更新配置文件
- [ ] 在 `config.turing.yaml` 中新增延迟配置参数
- [ ] 在 `config.alice.yaml` 中新增延迟配置参数（可选）

### 第二步：更新 Bot 模板
- [ ] 在 `BotTemplate` 数据类中新增延迟字段
- [ ] 更新 Bot 模板加载逻辑

### 第三步：更新 AI Bot 服务
- [ ] 重构 `AIBotService._calculate_typing_delay()` 支持多种延迟类型
- [ ] 增加配置加载逻辑

### 第四步：更新 WebSocket 层
- [ ] 在 `handle_ai_response()` 中增加开场白检测
- [ ] 应用延迟配置

### 第五步：更新钓鱼机器人服务
- [ ] 增强 `HoneypotService.get_response_with_delay()`
- [ ] 增加拟真延迟逻辑

### 第六步：测试验证
- [ ] 单元测试：延迟计算逻辑
- [ ] 集成测试：开场白延迟
- [ ] 集成测试：回复延迟
- [ ] 集成测试：钓鱼机器人延迟

---

## 配置示例

### `config.turing.yaml` 新增配置

```yaml
# -----------------------------------------------------------------------------
# AI Bot 配置
# -----------------------------------------------------------------------------
ai_bot:
  name: 小图
  
  # === 回复延迟配置（随机范围）===
  reply_delay_min: 1.0          # 最小延迟（秒）
  reply_delay_max: 3.0          # 最大延迟（秒）
  
  # === 开场白延迟配置（随机范围）===
  opening_delay_min: 2.0        # 最小延迟（秒）
  opening_delay_max: 5.0        # 最大延迟（秒）
  
  # === 每字符延迟 ===
  typing_delay_per_char: 0.05   # 每字符额外延迟（秒）
  
  # === 钓鱼机器人延迟配置 ===
  honeypot:
    reply_delay_min: 2.0        # 钓鱼机器人回复更慢
    reply_delay_max: 8.0
    opening_delay_min: 5.0      # 开场白也更慢
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

## 预期效果

1. **回复延迟**：Bot 回复前有 1-3 秒随机延迟，模拟人类打字
2. **开场白延迟**：Bot 开场白有 2-5 秒随机延迟，避免秒回
3. **钓鱼机器人延迟**：更长的延迟范围（2-8 秒回复，5-15 秒开场白）
4. **拟真行为**：
   - 偶尔超长延迟（10% 概率，15-60 秒）模拟人类分心
   - 元对话时延迟增加 50% 模拟思考
   - 会话早期延迟增加 30% 建立人设

---

## 技术要点

1. **配置优先级**：Bot 模板配置 > 全局配置 > 默认值
2. **延迟计算**：基础延迟 + 长度延迟 + 随机波动 + 拟真加成
3. **异步支持**：使用 `asyncio.sleep()` 实现非阻塞延迟
4. **可测试性**：延迟计算逻辑独立，便于单元测试
