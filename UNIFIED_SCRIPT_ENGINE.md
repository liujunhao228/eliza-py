# 统一脚本引擎架构文档

## 概述

统一脚本引擎架构将 Lua 和 YAML 脚本引擎整合到独立的 `scripting` 包中，实现：
- **独立包设计**: `scripting` 包完全独立，不依赖 `alice` 其他模块
- **统一接口**: 所有脚本引擎实现相同的基类接口
- **优先级调度**: Lua 和 YAML 脚本在同一优先级体系下竞争
- **完整上下文管理**: 使用 `ScriptContext` 统一管理对话上下文
- **热重载支持**: 支持 Lua 和 YAML 脚本的自动热重载
- **安全沙箱**: Lua 脚本执行在隔离的沙箱环境中
- **配置管理**: 统一的配置加载器支持多种配置来源

## 快速开始

```python
# 最简单的使用方式
from alice import DialogueEngine

engine = DialogueEngine(
    yaml_script_file="alice/scripts/demo.yaml",
    lua_script_dir="scripts/lua",
    enable_lua=True,
    enable_yaml=True,
)
engine.initialize()

response = engine.respond("你好")
print(response)
```

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    DialogueEngine                           │
│                     (对话引擎)                               │
│                  依赖 alice.scripting                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              alice.scripting (独立包)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  base.py                                              │  │
│  │  - ScriptConfig (配置数据类)                           │  │
│  │  - ScriptMatchResult (匹配结果)                        │  │
│  │  - ScriptResponse (响应结果)                           │  │
│  │  - BaseScriptEngine (抽象基类)                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  context.py                                           │  │
│  │  - ScriptContext (统一上下文)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  config.py                                            │  │
│  │  - ScriptConfigLoader (配置加载器)                     │  │
│  │  - load_scripts() (便捷函数)                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  matcher.py                                           │  │
│  │  - ScriptMatcher (统一匹配器)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────┐    ┌───────────────────────────┐    │
│  │  lua/             │    │  yaml/                    │    │
│  │  - engine.py      │    │  - engine.py              │    │
│  │  - sandbox.py     │    │                           │    │
│  └───────────────────┘    └───────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
alice/
├── scripting/                    # 【核心】独立脚本引擎包
│   ├── __init__.py               # 包导出
│   ├── base.py                   # 基类 + 数据结构（无外部依赖）
│   ├── context.py                # ScriptContext（无外部依赖）
│   ├── config.py                 # 配置加载器（仅依赖 PyYAML）
│   ├── matcher.py                # ScriptMatcher（仅依赖 scripting）
│   ├── lua/
│   │   ├── __init__.py
│   │   ├── engine.py             # LuaScriptEngine
│   │   └── sandbox.py            # LuaSandbox
│   └── yaml/
│       ├── __init__.py
│       └── engine.py             # YAMLScriptEngine
│
├── core/                         # 核心对话引擎
│   ├── __init__.py
│   ├── dialogue_engine.py        # 对话主引擎（使用 scripting）
│   ├── intent_matcher.py         # 意图匹配器
│   ├── response_generator.py     # 响应生成器
│   └── context_manager.py        # 上下文管理器
│
├── managers/                     # 管理器（向后兼容）
│   └── context_manager.py        # 指向 core.context_manager
│
└── scripts/                      # 脚本文件
    ├── lua/                      # Lua 脚本
    └── yaml/                     # YAML 脚本
```

## 依赖关系

```
scripting  →  (无 alice 内部依赖，仅依赖标准库和 PyYAML/lupa)
core       →  scripting
managers   →  core (向后兼容)
其他模块   →  core / scripting
```

## 安装依赖

```bash
# 安装核心依赖
uv add pyyaml

# 安装 Lua 支持（可选）
uv add lupa

# 注意：lupa 需要 LuaJIT 或 Lua 5.1/5.2
```

## 使用示例

### 1. 使用 DialogueEngine（推荐）

```python
from alice import DialogueEngine

# 创建对话引擎
engine = DialogueEngine(
    yaml_script_file="alice/scripts/demo.yaml",
    lua_script_dir="scripts/lua",
    lua_metadata_file="scripts/lua/metadata.yaml",
    enable_lua=True,
    enable_yaml=True,
    enable_plugins=True,
    use_ltp=True,
)

# 初始化
engine.initialize()

# 对话
response = engine.respond("你好，很高兴见到你")
print(f"机器人：{response}")

# 查看统计
stats = engine.get_stats()
print(f"统计：{stats}")

# 清理
engine.cleanup()
```

### 2. 直接使用 scripting 包

```python
from alice.scripting import (
    ScriptMatcher,
    ScriptContext,
    LuaScriptEngine,
    YAMLScriptEngine,
    ScriptConfig,
)
from pathlib import Path

# 创建匹配器
matcher = ScriptMatcher()

# 创建并注册 Lua 引擎
lua_engine = LuaScriptEngine(sandbox_mode=True)
matcher.register_engine('lua', lua_engine)

# 创建并注册 YAML 引擎
yaml_engine = YAMLScriptEngine()
matcher.register_engine('yaml', yaml_engine)

# 加载脚本
lua_engine.load_from_directory(
    Path("scripts/lua"),
    metadata_file="metadata.yaml",
)

yaml_engine.load_script(ScriptConfig(
    script_id="demo",
    name="Demo 脚本",
    script_type="yaml",
    script_path=Path("scripts/demo.yaml"),
))

# 创建上下文并匹配
context = ScriptContext(
    text="你好",
    tokens=["你好"],
    turn_count=1,
)

match = matcher.match(context)
if match:
    print(f"匹配：{match.script_id} (priority={match.priority})")
    response = matcher.generate_response(match, context)
    print(f"响应：{response.text}")
```

### 3. 配置管理

```python
from alice.scripting import ScriptConfigLoader, load_scripts

loader = ScriptConfigLoader()

# 从 YAML 配置文件加载
configs = loader.load_from_yaml("scripts/config.yaml")

# 从 Lua 元数据加载
configs = loader.load_lua_metadata("scripts/lua/metadata.yaml")

# 从目录扫描
configs = loader.scan_directory("scripts/lua", script_type="lua")

# 便捷函数：从多个来源加载
all_configs = load_scripts(
    config_path="scripts/config.yaml",
    script_dir="scripts/lua",
    metadata_file="metadata.yaml",
)
```

## 核心组件 API

### ScriptContext

统一上下文对象，封装所有脚本执行所需的数据。

```python
from alice.scripting import ScriptContext

context = ScriptContext(
    text="你好，我叫小明",
    tokens=["你好", "，", "我", "叫", "小明"],
    entities=[("PERSON", "小明")],
    turn_count=5,
    time_context={"hour": 10, "category_time": "早晨"},
    user_profile={"name": "张三"},
)

# 访问数据
print(context.text)                    # "你好，我叫小明"
print(context.get("entities"))         # [("PERSON", "小明")]
print(context.get_first_entity("PERSON"))  # "小明"
print(context.get_subject())           # None（需要 syntax）

# 设置脚本变量（脚本间共享）
context.set_variable("mood", "happy")

# 创建只读副本（安全传递给脚本）
frozen = context.freeze()
```

**主要方法:**

| 方法 | 说明 |
|------|------|
| `to_dict()` | 转换为字典 |
| `get(key, default)` | 获取值 |
| `has(key)` | 检查键是否存在 |
| `set_variable(key, value)` | 设置脚本变量 |
| `get_variable(key, default)` | 获取脚本变量 |
| `freeze()` | 创建只读副本 |
| `get_entity_by_type(type)` | 根据类型获取实体 |
| `get_first_entity(type)` | 获取第一个实体 |
| `get_subject()` | 获取主语 |
| `get_predicate()` | 获取谓语 |
| `get_object()` | 获取宾语 |
| `get_time(key)` | 获取时间上下文 |
| `get_user_info(key)` | 获取用户信息 |

### ScriptMatcher

统一脚本匹配器，协调多个脚本引擎。

```python
from alice.scripting import ScriptMatcher, LuaScriptEngine, YAMLScriptEngine

matcher = ScriptMatcher()

# 注册引擎
matcher.register_engine('lua', LuaScriptEngine())
matcher.register_engine('yaml', YAMLScriptEngine())

# 匹配
context = ScriptContext(text="你好")
match = matcher.match(context)

if match:
    print(f"匹配：{match.script_id}")
    print(f"类型：{match.script_type}")
    print(f"优先级：{match.priority}")
    print(f"置信度：{match.confidence}")
    
    # 生成响应
    response = matcher.generate_response(match, context)
    print(f"响应：{response.text}")
```

**主要方法:**

| 方法 | 说明 |
|------|------|
| `register_engine(name, engine)` | 注册引擎 |
| `unregister_engine(name)` | 注销引擎 |
| `match(context)` | 匹配脚本 |
| `match_all(context)` | 匹配所有引擎 |
| `generate_response(match, context)` | 生成响应 |
| `reload_script(engine_name, script_id)` | 重载脚本 |
| `list_scripts()` | 列出所有脚本 |
| `get_stats()` | 获取统计信息 |

### ScriptConfig

脚本配置数据类。

```python
from alice.scripting import ScriptConfig
from pathlib import Path

config = ScriptConfig(
    script_id="greeting",
    name="问候脚本",
    script_type="lua",
    priority=90,
    script_path=Path("scripts/lua/greeting.lua"),
    enabled=True,
    variables={"threshold": 0.8},
    max_execution_time=1.0,
    sandbox_mode=True,
)
```

**字段:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `script_id` | str | 脚本唯一标识 |
| `name` | str | 脚本名称 |
| `script_type` | str | 脚本类型 ("lua" \| "yaml") |
| `priority` | int | 优先级 (0-100) |
| `enabled` | bool | 是否启用 |
| `description` | str | 脚本描述 |
| `variables` | dict | 全局变量 |
| `max_execution_time` | float | 最大执行时间 (秒) |
| `sandbox_mode` | bool | 是否启用沙箱 |
| `script_path` | Path | 脚本文件路径 |

### ScriptConfigLoader

配置加载器，支持多种配置来源。

```python
from alice.scripting import ScriptConfigLoader

loader = ScriptConfigLoader()

# 从 YAML 文件加载
configs = loader.load_from_yaml("scripts/config.yaml")

# 从 Lua 元数据加载
configs = loader.load_lua_metadata("scripts/lua/metadata.yaml")

# 从目录扫描
configs = loader.scan_directory("scripts/lua", script_type="lua")

# 从字典创建
config = loader.from_dict({
    'id': 'custom',
    'name': '自定义脚本',
    'type': 'lua',
    'priority': 75,
})

# 从 JSON 文件加载
configs = loader.from_json("scripts/config.json")
```

### LuaScriptEngine

Lua 脚本引擎。

```python
from alice.scripting import LuaScriptEngine, ScriptConfig
from pathlib import Path

engine = LuaScriptEngine(
    sandbox_mode=True,
    max_execution_time=1.0,
)

# 从目录加载
engine.load_from_directory(
    Path("scripts/lua"),
    metadata_file="metadata.yaml",
)

# 或手动加载
config = ScriptConfig(
    script_id="greeting",
    script_type="lua",
    script_path=Path("scripts/lua/greeting.lua"),
)
engine.load_script(config)

# 匹配和响应
context = ScriptContext(text="你好")
match = engine.match(context)
if match:
    response = engine.generate_response(match.script_id, context)
```

### YAMLScriptEngine

YAML 脚本引擎。

```python
from alice.scripting import YAMLScriptEngine, ScriptConfig
from pathlib import Path

# 使用默认脚本文件
engine = YAMLScriptEngine(default_script_file=Path("scripts/demo.yaml"))

# 或从配置文件加载
engine.load_from_config_file(Path("scripts/config.yaml"))

# 匹配和响应
context = ScriptContext(text="你好")
match = engine.match(context)
if match:
    response = engine.generate_response(match.script_id, context)
```

## 脚本编写指南

### Lua 脚本

```lua
-- scripts/lua/greeting.lua

-- 主匹配函数
function match(context)
    local text = context.text or ""
    
    -- 检查问候关键词
    local greeting_keywords = {"你好", "您好", "嗨", "早上好"}
    for _, keyword in ipairs(greeting_keywords) do
        if string.find(text, keyword) then
            return {
                matched = true,
                priority = 90,
                confidence = 0.9
            }
        end
    end
    
    return false
end

-- 响应生成函数
function generate_response(context)
    local hour = context.time_context.hour or 12
    
    if hour < 12 then
        return "早上好！今天过得怎么样？"
    elseif hour < 18 then
        return "下午好！有什么新鲜事吗？"
    else
        return "晚上好！今天辛苦了。"
    end
end

-- 返回模块
return { match = match, generate_response = generate_response }
```

### YAML 脚本

```yaml
# scripts/demo.yaml

- intent: greeting
  priority: 90
  condition:
    keywords: ["你好", "您好", "嗨"]
  templates:
    - "你好！很高兴见到你。"
    - "您好！有什么可以帮您的吗？"

- intent: entity_query
  priority: 75
  condition:
    entities: ["PERSON", "LOCATION"]
  templates:
    - "你在问关于{entity_PERSON}的事情吗？"
    - "{entity_LOCATION}是个好地方。"

- intent: thanks
  priority: 80
  condition:
    keywords: ["谢谢", "感谢"]
  templates:
    - "不客气！"
    - "这是我应该做的。"
  keyword_only: true
```

### 配置文件

```yaml
# scripts/config.yaml

scripts:
  # Lua 脚本
  - id: greeting
    name: 问候脚本
    type: lua
    priority: 90
    path: scripts/lua/greeting.lua
    enabled: true
    variables:
      greeting_threshold: 0.8
    max_execution_time: 1.0
    sandbox_mode: true

  - id: entity_analysis
    name: 实体分析脚本
    type: lua
    priority: 85
    path: scripts/lua/entity_analysis.lua
    enabled: true

  # YAML 脚本
  - id: demo
    name: Demo 脚本
    type: yaml
    priority: 50
    path: scripts/demo.yaml
    enabled: true
```

## 脚本优先级

Lua 和 YAML 脚本使用相同的优先级范围（0-100）：

| 级别 | 范围 | 说明 | 示例 |
|------|------|------|------|
| P0 | 90-100 | 非常重要 | 问候、告别、紧急 |
| P1 | 70-89 | 实体挖掘 | 实体查询、深度对话 |
| P2 | 40-69 | 叙事助推 | 话题扩展、引导 |
| P3 | 0-39 | 万能回复 | 回退响应、通用 |

## 测试

运行单元测试：

```bash
cd F:\eliza-py
uv run pytest tests/scripting/ -v
```

运行单个测试文件：

```bash
uv run pytest tests/scripting/test_context.py -v
uv run pytest tests/scripting/test_matcher.py -v
uv run pytest tests/scripting/test_yaml_engine.py -v
```

## 迁移指南

### 从旧版 engines/目录迁移

旧版：
```python
from engines.lua.lua_script_engine import LuaScriptEngine
```

新版：
```python
from alice.scripting import LuaScriptEngine
```

### 从旧版 YAML 引擎迁移

旧版：
```python
from alice.scripts.yaml_script_engine import YAMLScriptEngine
engine = YAMLScriptEngine(script_file="demo.yaml")
```

新版：
```python
from alice.scripting import YAMLScriptEngine
from pathlib import Path
engine = YAMLScriptEngine(default_script_file=Path("demo.yaml"))
```

### 使用统一对话引擎

旧版：
```python
from alice.core.dialogue_engine import DialogueEngine
```

新版（推荐）：
```python
from alice import DialogueEngine
# 已自动使用 scripting 包
```

## 故障排除

### 常见问题

1. **Lua 引擎无法初始化**
   - 确保已安装 lupa: `uv add lupa`
   - 确保系统有 LuaJIT 或 Lua 5.1/5.2

2. **脚本匹配不到**
   - 检查脚本优先级设置
   - 检查条件是否满足
   - 查看日志输出

3. **循环导入错误**
   - 确保从 `alice.scripting` 导入，而不是旧路径
   - `scripting` 包不依赖 `alice` 其他模块

4. **ImportError: cannot import name XXX**
   - 检查导入路径是否正确
   - 使用 `from alice.scripting import XXX`

### 日志配置

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('alice.scripting')
logger.setLevel(logging.DEBUG)
```

## 版本历史

- **v3.0** (2026-02-25): 统一脚本引擎架构重构
  - 创建独立 `scripting` 包
  - 消除循环导入问题
  - 统一 Lua 和 YAML 引擎接口
  - 新增 `ScriptConfigLoader` 配置管理
  - 新增 `ScriptContext` 统一上下文
  - 新增 `ScriptMatcher` 统一匹配器
  - 完善 Lua 沙箱安全机制
  - 所有 29 个单元测试通过

## 相关文档

- [SCRIPT_WRITING_GUIDE.md](SCRIPT_WRITING_GUIDE.md) - 脚本编写指南（模板变量详解）
- [alice/scripting/README.md](alice/scripting/README.md) - 快速参考
