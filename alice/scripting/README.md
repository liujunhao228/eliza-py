# Alice Scripting Package

统一脚本引擎架构 - 支持 Lua 和 YAML 脚本的对话系统。

## 快速开始

```python
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

## 安装

```bash
# 核心依赖
uv add pyyaml

# Lua 支持（可选）
uv add lupa
```

## 使用

### 导入方式

```python
# 推荐：从 alice 包直接导入
from alice import DialogueEngine, ScriptContext, ScriptMatcher

# 或从 scripting 包导入
from alice.scripting import (
    LuaScriptEngine,
    YAMLScriptEngine,
    ScriptMatcher,
    ScriptContext,
)
```

### 创建脚本

**Lua 脚本** (`scripts/lua/greeting.lua`):
```lua
function match(context)
    local text = context.text or ""
    if string.find(text, "你好") then
        return { matched = true, priority = 90, confidence = 0.9 }
    end
    return false
end

function generate_response(context)
    return "你好！很高兴见到你。"
end

return { match = match, generate_response = generate_response }
```

**YAML 脚本** (`scripts/demo.yaml`):
```yaml
- intent: greeting
  priority: 90
  condition:
    keywords: ["你好", "您好"]
  templates:
    - "你好！很高兴见到你。"
    - "您好！有什么可以帮您的吗？"
```

## 文档

详细文档请参阅 [UNIFIED_SCRIPT_ENGINE.md](UNIFIED_SCRIPT_ENGINE.md)

## 测试

```bash
uv run pytest tests/scripting/ -v
```

## 架构

```
alice/
├── scripting/          # 独立脚本引擎包
│   ├── base.py        # 基类和数据结构
│   ├── context.py     # ScriptContext
│   ├── config.py      # 配置加载器
│   ├── matcher.py     # ScriptMatcher
│   ├── lua/           # Lua 引擎
│   └── yaml/          # YAML 引擎
├── core/              # 核心对话引擎
└── scripts/           # 脚本文件
```

## 特性

- ✅ **独立包设计**: `scripting` 包无 `alice` 内部依赖
- ✅ **统一接口**: Lua 和 YAML 使用相同接口
- ✅ **优先级调度**: 统一优先级体系 (0-100)
- ✅ **完整上下文**: `ScriptContext` 管理对话状态
- ✅ **安全沙箱**: Lua 脚本隔离执行
- ✅ **配置管理**: 支持 YAML/JSON/目录扫描
- ✅ **热重载**: 支持脚本自动重载
