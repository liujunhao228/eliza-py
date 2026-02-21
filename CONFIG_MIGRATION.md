# 配置管理模块重构说明

## 概述

已完成配置管理模块的统一重构，移除了分散在 `alice/` 和 `turing_test/` 中的多个配置文件，改为统一的 YAML 配置 + 环境变量管理。

## 变更内容

### 新增文件

```
config/
├── __init__.py          # 统一导出：from config import settings
├── loader.py            # 配置加载器
└── types.py             # 配置类型定义

config.yaml              # 主配置文件
config.yaml.example      # 配置文件示例
.env.example             # 环境变量示例
```

### 删除文件

- `alice/config.py`
- `alice/managers/config_manager.py`
- `turing_test/backend/config.py`
- `turing_test/backend/config_manager.py`
- `alice/nlp/engines/ltp/config.py`

### 配置迁移

所有配置项已迁移到 `config.yaml`，包括：

| 原配置模块 | 新配置路径 |
|-----------|-----------|
| `alice.config.ENABLE_LTP_BY_DEFAULT` | `settings.alice.enable_ltp` |
| `alice.config.HOT_RELOAD_MODE` | `settings.alice.hot_reload_mode` |
| `alice.config.CONTEXT_MAX_ITEMS` | `settings.alice.context_max_items` |
| `turing_test.backend.config.DATABASE_URL` | `settings.turing.database.url` |
| `turing_test.backend.config.MATCH_TIMEOUT` | `settings.turing.match.timeout` |
| `turing_test.backend.config.PORT` | `settings.turing.server.port` |

## 使用方式

### 基本用法

```python
from config import settings

# Alice 配置
if settings.alice.enable_ltp:
    ...

# Turing 配置
port = settings.turing.server.port

# 路径配置
log_dir = settings.paths.log_dir
```

### 环境变量覆盖

在 `.env` 文件中使用 `CONFIG_` 前缀覆盖配置：

```bash
# 启用调试模式
DEBUG=true

# 覆盖 Alice 配置
CONFIG_ALICE_ENABLE_LTP=false

# 覆盖 Turing 配置
CONFIG_TURING_SERVER_PORT=9000
```

## 配置层级

加载优先级（从高到低）：

1. 环境变量（`CONFIG_*` 前缀）
2. `.env` 文件
3. `.env.local` 文件（本地开发覆盖）
4. `config.alice.yaml` / `config.turing.yaml`（模块专属配置）
5. `config.yaml`（主配置）

## 迁移检查清单

- [x] 创建 `config/` 模块
- [x] 迁移所有配置项到 `config.yaml`
- [x] 更新所有导入语句
- [x] 删除旧配置文件
- [x] 测试验证通过

## 注意事项

1. **首次运行前**：复制 `config.yaml.example` 为 `config.yaml`
2. **数据库目录**：确保 `data/` 目录存在（Turing 测试需要）
3. **日志目录**：确保 `logs/` 目录存在（可选，会自动创建）
