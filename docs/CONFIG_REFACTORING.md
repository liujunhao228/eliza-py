# 配置系统重构说明

## 概述

本次重构统一了 Alice 和 Turing Test 两个模块的配置系统，消除了重复配置，实现了单一数据源。

## 配置结构

```
config/
├── __init__.py      # 导出 settings 和类型
├── types.py         # 配置类型定义
└── loader.py        # 配置加载器
```

## 配置层次

```yaml
# config.yaml
debug: false                    # 通用配置
log_level: INFO

paths:                          # 路径配置
  project_root: .
  alice_dir: alice
  turing_dir: turing_test
  ...

alice:                          # Alice 模块配置
  enable_ltp: true
  enable_ner: true
  ...
  ltp:                          # LTP 引擎配置 (共享)
    enable_cws: true
    enable_pos: true
    ...

turing:                         # Turing 模块配置
  database:
    url: sqlite:///data/turing.db
  auth:
    invite_code_length: 6
  server:
    host: 0.0.0.0
    port: 8000
  nlp_service:                  # NLP 服务配置
    enable_ltp: false           # 使用共享 LTP 配置
  websocket:                    # WebSocket 配置
    ping_interval: 20
    ping_timeout: 30
  log:                          # 日志配置 (共享)
    level: INFO
    file: logs/turing.log
```

## 使用方式

### 推荐方式（统一配置）

```python
from config import settings

# 访问 Alice 配置
if settings.alice.enable_ltp:
    ...

# 访问 Turing 配置
port = settings.turing.server.port
db_url = settings.turing.database.url

# 访问共享 LTP 配置
enable_cws = settings.shared_ltp.enable_cws

# 访问路径配置
log_dir = settings.paths.log_dir
```

### 向后兼容方式（Turing 模块）

```python
# 旧代码仍然可用
from turing_test.backend.config import settings, PORT, HOST

print(settings.APP_NAME)  # Turing Test Backend
print(settings.PORT)      # 8000
```

## 配置优先级

1. **环境变量** (最高优先级)
   - 格式：`CONFIG_<路径>`，如 `CONFIG_TURING_SERVER_PORT=9000`
   - 支持嵌套：`CONFIG_ALICE_ENABLE_LTP=true`

2. **.env 文件**
   - `.env` 或 `.env.local`

3. **模块专属配置** (可选)
   - `config.alice.yaml`
   - `config.turing.yaml`

4. **主配置文件**
   - `config.yaml`

## 配置项映射

### 共享配置

| 配置项 | Alice 路径 | Turing 路径 | 说明 |
|--------|-----------|-------------|------|
| LTP 引擎 | `alice.ltp.*` | `shared_ltp.*` | 词分词、词性标注等 |
| 日志 | `alice.log_*` | `turing.log.*` | 日志级别、文件等 |
| 最大输入长度 | `alice.max_input_length` | `turing.performance.max_input_length` | 输入长度限制 |

### 独立配置

| 模块 | 配置路径 | 说明 |
|------|---------|------|
| Alice | `alice.*` | Alice 聊天机器人配置 |
| Turing | `turing.*` | Turing 测试平台配置 |
| 路径 | `paths.*` | 项目路径配置 |

## 迁移指南

### 从旧配置迁移

#### Alice 模块

旧代码：
```python
from config import settings
settings.alice.enable_ltp  # 保持不变
```

#### Turing 模块

旧代码：
```python
from turing_test.backend.config import settings
settings.PORT  # 仍然可用
```

新代码推荐：
```python
from config import settings
settings.turing.server.port  # 推荐方式
```

### 环境变量迁移

旧格式：
```bash
CONFIG_TURING_SERVER_PORT=8000
```

新格式（相同，保持不变）：
```bash
CONFIG_TURING_SERVER_PORT=9000
```

## 配置管理器

`turing_test/backend/config_manager.py` 提供运行时配置热更新：

```python
from turing_test.backend.config_manager import get_config_manager

config = get_config_manager()

# 获取配置
port = config.get('turing.server.port')

# 设置配置（仅当前会话有效）
config.set('turing.server.port', 9000)

# 批量更新
config.update({
    'turing': {
        'server': {'port': 9000}
    }
})
```

**注意**：运行时修改仅在当前会话有效，持久化修改需要更新 `config.yaml`。

## 类型定义

所有配置类型定义在 `config/types.py`：

- `Settings` - 根配置
- `PathsConfig` - 路径配置
- `LtpConfig` - LTP 引擎配置（共享）
- `AliceConfig` - Alice 配置
- `TuringConfig` - Turing 配置
- `DatabaseConfig`, `AuthConfig`, `ServerConfig` 等子配置

## 常见问题

### Q: 如何添加新配置项？

1. 在 `config/types.py` 添加类型定义
2. 在 `config/loader.py` 添加加载逻辑
3. 在 `config.yaml` 添加配置项

### Q: 如何覆盖默认配置？

创建 `.env.local` 文件：
```bash
CONFIG_TURING_SERVER_PORT=9000
CONFIG_ALICE_ENABLE_LTP=false
```

### Q: 如何为不同环境使用不同配置？

使用不同的 `.env` 文件：
- `.env.development` - 开发环境
- `.env.production` - 生产环境

复制为 `.env` 或 `.env.local` 使用。

## 废弃项

以下配置方式已废弃：

- ❌ `turing_test/backend/config.py` 中的 `Settings` 类（使用 Pydantic）
- ❌ 独立的 JSON 配置文件
- ❌ 硬编码默认值

所有配置应通过 `config.yaml` 和 `.env` 管理。
