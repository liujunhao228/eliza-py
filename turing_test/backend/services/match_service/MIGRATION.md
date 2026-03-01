# 匹配机制模块迁移指南

> 从旧版 `match_bot_pool.py` 迁移到新版架构

## 📋 概述

匹配机制模块已完成重构，新架构采用分层设计，职责更清晰、易于测试和扩展。

### 架构对比

| 维度 | 旧版 | 新版 |
|-----|------|------|
| **文件结构** | 单文件 800+ 行 | 模块化分层 |
| **Bot 池位置** | `services/match_bot_pool.py` | `services/match_service/pools/` |
| **配置类** | `MatchServiceConfig` | `MatchConfig` |
| **Bot 抽取方法** | `get_bot()` | `draw()` |

---

## 🔧 迁移步骤

### 1. 导入路径变更

#### Bot 池导入

```python
# ❌ 旧版（已删除）
from turing_test.backend.services.match_bot_pool import (
    BotPool, HoneypotPool,
    create_bot_pool, create_honeypot_pool,
)

# ✅ 新版
from turing_test.backend.services.match_service.pools import (
    BotPool, HoneypotPool,
    BotPoolConfig, HoneypotPoolConfig,
)
```

#### 配置类导入

```python
# ❌ 旧版
from turing_test.backend.services.match_service.service import (
    MatchService, MatchServiceConfig,
)

# ✅ 新版
from turing_test.backend.services.match_service import (
    MatchService, MatchConfig,
)
```

#### 类型导入

```python
# ✅ 保持不变（向后兼容）
from turing_test.backend.services.match_service import (
    MatchType,
    MatchRequest,
    MatchResultData,
    SafeMatchResult,
)
```

---

### 2. API 变更

#### Bot 池使用

```python
# ❌ 旧版
config = {"bots": [...]}
pool = create_bot_pool(config)
bot = pool.get_bot()  # 方法名：get_bot()

# ✅ 新版
config = BotPoolConfig(bots=[...])
pool = BotPool(config)
bot = pool.draw()  # 方法名：draw()
```

#### 配置创建

```python
# ❌ 旧版
config = MatchServiceConfig(
    human_probability=0.30,
    bot_probability=0.70,
)

# ✅ 新版
config = MatchConfig(
    human_probability=0.30,
    bot_probability=0.70,
)
```

#### 服务使用

```python
# ✅ 工厂函数保持兼容
from turing_test.backend.services.match_service import get_match_service
service = get_match_service()  # 仍然可用
```

---

### 3. 内部 API 变更（仅影响测试）

#### 访问协调器

```python
# ❌ 旧版（直接访问内部属性）
service._waiting_queue
service._decide_match_type()

# ✅ 新版（通过协调器）
service.coordinator.queue
service.coordinator.algorithm.decide_match_type()
```

#### 设置 Bot 池

```python
# ❌ 旧版
service.set_bot_pools(bot_pool, honeypot_pool)

# ✅ 新版
service.coordinator.bot_pool = bot_pool
service.coordinator.honeypot_pool = honeypot_pool
```

---

## 📝 完整迁移示例

### 测试代码迁移

```python
#!/usr/bin/env python3
# ❌ 旧版测试
from turing_test.backend.services.match_bot_pool import create_bot_pool
from turing_test.backend.services.match_service.service import MatchServiceConfig

config = MatchServiceConfig(human_probability=0.30)
pool = create_bot_pool({"bots": [...]})
bot = pool.get_bot()
```

```python
#!/usr/bin/env python3
# ✅ 新版测试
from turing_test.backend.services.match_service import MatchConfig
from turing_test.backend.services.match_service.pools import BotPool, BotPoolConfig

config = MatchConfig(human_probability=0.30)
pool = BotPool(BotPoolConfig(bots=[...]))
bot = pool.draw()
```

---

## ⚠️ 废弃说明

以下模块已删除：

| 已删除模块 | 替代模块 |
|-----------|---------|
| `services/match_bot_pool.py` | `services/match_service/pools/` |
| `MatchServiceConfig` | `MatchConfig` |
| `create_bot_pool()` | `BotPool()` 直接实例化 |
| `get_bot_pool()` | `BotPool()` 直接实例化 |

---

## 🧪 验证迁移

运行测试验证迁移是否成功：

```bash
# 运行新测试
python tests/unit/test_match_refactored.py

# 运行旧测试（已迁移）
python tests/unit/test_match_probabilistic.py
```

预期输出：
```
✅ 配置管理
✅ 概率决策算法
✅ Bot 池加权随机
✅ 钓鱼 Bot 池
✅ 队列管理器
✅ 结果管理器
✅ 匹配协调器

总计：7/7 测试通过
```

---

## 📚 新架构文档

### 模块结构

```
turing_test/backend/services/match_service/
├── __init__.py           # 统一导出
├── config.py             # 配置管理
├── types.py              # 类型定义
├── queue.py              # 队列管理器
├── result_manager.py     # 结果管理器
├── matcher.py            # 匹配协调器
├── service.py            # 对外服务
│
├── algorithm/            # 算法模块
│   ├── base.py           # 抽象基类
│   ├── probability.py    # 概率决策
│   └── fifo.py           # FIFO 匹配
│
└── pools/                # Bot 池模块
    ├── base.py           # 池抽象基类
    ├── bot_pool.py       # 普通 Bot 池
    └── honeypot_pool.py  # 钓鱼 Bot 池
```

### 核心类说明

| 类 | 职责 |
|---|------|
| `MatchConfig` | 匹配配置（概率、超时等） |
| `MatchQueue` | 队列管理（加入、移除、快照） |
| `ResultManager` | 结果管理（存储、获取、安全过滤） |
| `MatchCoordinator` | 匹配协调（核心业务逻辑） |
| `MatchService` | 对外服务接口 |
| `ProbabilityAlgorithm` | 概率决策算法 |
| `BotPool` | 普通 Bot 池（加权随机） |
| `HoneypotPool` | 钓鱼 Bot 池 |

---

## 🔍 常见问题

### Q: 旧代码还能用吗？

A: 不能。旧模块 `match_bot_pool.py` 已删除，必须迁移到新 API。

### Q: 如何迁移？

A: 参考本文档的迁移步骤，主要是：
1. 更新导入路径
2. 使用 `BotPoolConfig` 替代字典配置
3. 使用 `draw()` 替代 `get_bot()`

---

## 📞 需要帮助？

如有迁移问题，请查看：
- `tests/unit/test_match_refactored.py` - 新 API 使用示例
- `turing_test/backend/services/match_service/__init__.py` - 导出类型列表
