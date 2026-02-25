# 配置快速入门指南

## 配置文件结构

```
F:\eliza-py\
├── config.yaml               # 主配置（通用配置 + 模块引用）
├── config.alice.yaml         # Alice 模块配置
├── config.turing.yaml        # Turing 模块配置
├── .env                      # 环境变量覆盖（可选）
└── bots/                     # Bot 配置目录
    ├── default.yaml          # 默认 Bot
    ├── honeypot.yaml         # 钓鱼机器人
    ├── slow.yaml             # 慢速 Bot
    └── fast.yaml             # 快速 Bot
```

## 快速开始

### 1. 复制示例配置

```bash
# 主配置
cp config.yaml.example config.yaml

# Alice 配置
cp config.alice.yaml.example config.alice.yaml

# Turing 配置
cp config.turing.yaml.example config.turing.yaml

# 环境变量（可选）
cp .env.example .env
```

### 2. 修改关键配置

#### 生产环境必须修改

编辑 `config.turing.yaml`：

```yaml
auth:
  # ⚠️ 必须修改为至少 32 字符的随机字符串
  secret_key: "your-super-secret-key-change-in-production"
```

#### 常用配置项

**修改服务器端口：**
```yaml
# config.turing.yaml
server:
  port: 8080  # 默认 8000
```

**修改 Bot 配置：**
```yaml
# config.turing.yaml
bot_pool:
  default_template: "default"  # 可选：default, fast, slow, honeypot
```

**启用/禁用功能：**
```yaml
# config.alice.yaml
enable_ltp: true      # 启用 LTP 句法分析
enable_ner: true      # 启用实体识别
hot_reload: true      # 启用热重载
```

### 3. 自定义 Bot

在 `bots/` 目录下创建新的 Bot 配置文件：

```yaml
# bots/my_bot.yaml
id: my_bot
name: 小明
description: 我的自定义 Bot

script_file: alice/scripts/demo.yaml
rules_file: alice/scripts/rules/mapping.yaml
enable_plugins: true

cache_size: 50
typing_delay_base: 1.5
typing_delay_per_char: 0.06

meta:
  personality: friendly
```

然后在 `config.turing.yaml` 中设置：
```yaml
bot_pool:
  default_template: "my_bot"
```

### 4. 使用环境变量

创建 `.env` 文件：

```bash
# 启用调试模式
DEBUG=true

# 修改服务器端口
CONFIG_TURING_SERVER_PORT=9000

# 修改 Bot 池配置
CONFIG_TURING_BOT_POOL_MIN_INSTANCES=5
```

## 配置验证

运行测试验证配置是否正确：

```bash
python test_config.py
```

## 配置说明

### 主配置 (config.yaml)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `debug` | 调试模式 | `false` |
| `log_level` | 日志级别 | `INFO` |
| `paths.project_root` | 项目根目录 | `.` |
| `paths.bots_dir` | Bot 配置目录 | `bots` |

### Alice 配置 (config.alice.yaml)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enable_ltp` | 启用 LTP 句法分析 | `true` |
| `enable_ner` | 启用实体识别 | `true` |
| `hot_reload` | 启用热重载 | `true` |
| `script_file` | 脚本文件路径 | `alice/scripts/demo.yaml` |

### Turing 配置 (config.turing.yaml)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `server.port` | 服务器端口 | `8000` |
| `auth.secret_key` | JWT 密钥 | ⚠️ 必须修改 |
| `match.timeout` | 匹配超时（秒） | `30` |
| `bot_pool.default_template` | 默认 Bot 模板 | `default` |

### Bot 配置 (bots/*.yaml)

| 配置项 | 说明 | 必填 |
|--------|------|------|
| `id` | Bot 唯一标识 | ✅ |
| `name` | Bot 显示名称 | ✅ |
| `script_file` | 脚本文件路径 | ✅ |
| `rules_file` | 规则文件路径 | ✅ |
| `typing_delay_base` | 基础延迟（秒） | ❌ |
| `typing_delay_per_char` | 每字符延迟（秒） | ❌ |

## 常见问题

### Q: 如何切换 Bot 模板？

A: 修改 `config.turing.yaml` 中的 `bot_pool.default_template`：

```yaml
bot_pool:
  default_template: "fast"  # 可选：default, fast, slow, honeypot
```

### Q: 如何禁用 LTP 以加快响应速度？

A: 修改 `config.alice.yaml`：

```yaml
enable_ltp: false
```

### Q: 如何调整匹配超时时间？

A: 修改 `config.turing.yaml`：

```yaml
match:
  timeout: 60  # 60 秒
```

### Q: 配置修改后需要重启吗？

A: 
- 使用热重载功能时，修改 Alice 配置会自动重载
- 其他配置修改需要重启应用

### Q: 如何添加新的 Bot 模板？

A: 在 `bots/` 目录创建新的 YAML 文件：

```yaml
# bots/custom.yaml
id: custom
name: 自定义 Bot
script_file: alice/scripts/demo.yaml
rules_file: alice/scripts/rules/mapping.yaml
```

## 更多信息

- 详细配置说明：[CONFIG_REFACTORING.md](CONFIG_REFACTORING.md)
- 配置示例文件：`*.example` 文件
- 配置测试脚本：`test_config.py`
