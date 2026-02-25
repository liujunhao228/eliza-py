# 配置管理模块重构文档

## 重构概述

本次重构优化了配置管理模块，支持使用 YAML 文件配置 Bot，提升用户体验。

## 重构日期
2026-02-23

## 主要变更

### 1. 配置文件结构优化

**重构前：**
- 所有配置集中在 `config.yaml` 一个文件中（约 200 行）
- Alice 和 Turing 配置混在一起，难以维护
- Bot 配置内联在 `config.yaml` 中

**重构后：**
```
F:\eliza-py\
├── config.yaml               # 主配置（仅通用配置和模块引用）
├── config.alice.yaml         # Alice 模块专属配置
├── config.turing.yaml        # Turing 模块专属配置
├── bots/                     # Bot 配置目录
│   ├── default.yaml          # 默认 Bot
│   ├── honeypot.yaml         # 钓鱼机器人
│   ├── slow.yaml             # 慢速 Bot
│   └── fast.yaml             # 快速 Bot
└── config/                   # 配置模块
    ├── __init__.py
    ├── loader.py             # 配置加载器
    ├── manager.py            # 配置管理器
    ├── types.py              # 类型定义
    ├── validator.py          # 配置验证器
    ├── sources.py            # 配置源抽象
    └── bot_loader.py         # Bot 配置加载器（新增）
```

### 2. 代码架构精简

**删除的冗余文件：**
- `turing_test/backend/config.py` - 已废弃，使用统一的 `config` 模块
- `turing_test/backend/config_manager.py` - 功能已整合到 `config/manager.py`

**精简的类型定义：**
- 移除了 `types.py` 中冗余的 `AiBotTemplate`（与 `BotTemplate` 功能重复）
- 新增 `BotConfig` 类型用于 Bot 配置文件
- 新增模块引用配置类型 `ModulesConfig`, `ModuleRefConfig` 等

**新增功能模块：**
- `config/bot_loader.py` - 专门用于从 bots/ 目录加载 Bot 配置

### 3. 配置加载流程

```
1. 加载 config.yaml（主配置）
       ↓
2. 加载 config.alice.yaml 和 config.turing.yaml（模块配置）
       ↓
3. 加载环境变量覆盖（.env 文件）
       ↓
4. 应用运行时内存覆盖
       ↓
5. 验证配置完整性
       ↓
6. 加载 bots/*.yaml 文件（Bot 配置）
       ↓
7. 构建类型化 Settings 对象
```

## 配置示例

### 主配置 (config.yaml)

```yaml
debug: false
log_level: INFO

paths:
  project_root: .
  alice_dir: alice
  turing_dir: turing_test
  log_dir: logs
  data_dir: data
  bots_dir: bots

modules:
  alice:
    config_file: config.alice.yaml
  turing:
    config_file: config.turing.yaml
    bot_pool:
      config_dir: bots
      default_template: default
```

### Bot 配置 (bots/default.yaml)

```yaml
id: default
name: 小图
description: 默认 AI Bot，用于常规对话

script_file: alice/scripts/demo.yaml
rules_file: alice/scripts/rules/mapping.yaml
enable_plugins: true

cache_size: 50
typing_delay_base: 1.0
typing_delay_per_char: 0.05

meta:
  is_honeypot: false
  aggressive_meta: false
  personality: friendly
```

## 使用方式

### 基本用法

```python
from config import settings

# 访问 Alice 配置
if settings.alice.enable_ltp:
    ...

# 访问 Turing 配置
port = settings.turing.server.port

# 访问 Bot 配置目录
bots_dir = settings.paths.bots_dir
```

### 配置管理器

```python
from config import get_config_manager

config_mgr = get_config_manager()

# 获取配置值
port = config_mgr.get('turing.server.port')

# 获取 Bot 配置
bot_config = config_mgr.get_bot_config("default")

# 运行时覆盖
config_mgr.set('turing.server.port', 9000)

# 列出所有 Bot 配置
bot_ids = config_mgr.list_bot_configs()
```

### Bot 配置加载器

```python
from config import BotConfigLoader
from pathlib import Path

loader = BotConfigLoader(project_root)
configs = loader.load_all("bots")

for config in configs:
    print(f"Bot: {config.name} (ID: {config.id})")
```

## 环境变量覆盖

支持使用环境变量覆盖配置文件：

```bash
# 设置服务器端口
CONFIG_TURING_SERVER_PORT=9000 python main.py

# 启用调试模式
CONFIG_DEBUG=true python main.py

# 修改 Bot 池配置
CONFIG_TURING_BOT_POOL_MIN_INSTANCES=5 python start_backend.py
```

## 配置验证

配置系统会自动验证配置完整性和正确性：

```python
from config.validator import build_default_validator

validator = build_default_validator()
errors = validator.validate(config_dict)

for error in errors:
    print(f"[{error.severity}] {error.path}: {error.message}")
```

## 迁移指南

### 从旧配置迁移

1. **备份现有配置**
   ```bash
   cp config.yaml config.yaml.backup
   ```

2. **拆分配置文件**
   - 将 Alice 相关配置移动到 `config.alice.yaml`
   - 将 Turing 相关配置移动到 `config.turing.yaml`
   - 将 Bot 模板配置移动到 `bots/*.yaml`

3. **更新代码引用**
   ```python
   # 旧代码
   from turing_test.backend.config import settings
   
   # 新代码
   from config import settings
   ```

4. **测试验证**
   ```bash
   python test_config.py
   ```

## 测试

运行配置测试：
```bash
python test_config.py
```

测试覆盖：
- ✅ 统一配置系统
- ✅ 配置管理器
- ✅ Alice 模块导入
- ✅ Bot 配置加载器
- ✅ 环境变量覆盖

## 优势总结

### 用户体验
- ✅ 配置文件更清晰，每个模块独立管理
- ✅ Bot 配置独立文件，方便自定义和扩展
- ✅ 配置验证错误提示更友好
- ✅ 完善的示例文件

### 代码质量
- ✅ 消除冗余代码（约 300 行）
- ✅ 配置加载逻辑更集中
- ✅ 类型定义更清晰
- ✅ 易于扩展和维护

### 功能增强
- ✅ 支持模块专属配置文件
- ✅ 支持 Bot 配置目录
- ✅ 增强的配置验证
- ✅ 配置变更监听器

## 注意事项

1. **生产环境配置**
   - 务必修改 `config.turing.yaml` 中的 `auth.secret_key`
   - 建议使用环境变量管理敏感配置

2. **Bot 配置**
   - Bot 配置文件必须以 `.yaml` 结尾
   - `id` 字段是必填的，用于标识 Bot 模板

3. **向后兼容**
   - 本次重构不向后兼容，需要更新所有配置引用
   - 旧的 `turing_test.backend.config` 模块已删除

## 后续计划

- [ ] 添加配置热更新支持（文件变更自动重载）
- [ ] 支持配置加密（敏感配置项）
- [ ] 添加配置管理 GUI 工具
- [ ] 支持远程配置中心
