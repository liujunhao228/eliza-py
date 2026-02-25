# 脚本编写指南

本文档介绍如何为 Alice 对话系统编写 Lua 和 YAML 脚本，重点介绍系统中已有的、可供替换使用的模板变量。

## 目录

1. [快速开始](#快速开始)
2. [YAML 脚本编写](#yaml-脚本编写)
3. [Lua 脚本编写](#lua-脚本编写)
4. [模板变量完整列表](#模板变量完整列表)
5. [条件匹配语法](#条件匹配语法)
6. [最佳实践](#最佳实践)
7. [示例脚本](#示例脚本)

---

## 快速开始

### YAML 脚本示例

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
    entities: ["PERSON"]
  templates:
    - "你在问关于{entity_PERSON}的事情吗？"
    - "{entity_PERSON}是个很有趣的话题。"
```

### Lua 脚本示例

```lua
-- scripts/lua/greeting.lua

function match(context)
    local text = context.text or ""
    
    -- 检查问候关键词
    if string.find(text, "你好") or string.find(text, "您好") then
        return {
            matched = true,
            priority = 90,
            confidence = 0.9
        }
    end
    
    return false
end

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

return { match = match, generate_response = generate_response }
```

---

## YAML 脚本编写

### 基本结构

YAML 脚本由多个意图（intent）组成，每个意图包含：

```yaml
- intent: <意图名称>
  priority: <优先级 0-100>
  condition:
    # 匹配条件
  templates:
    - <响应模板 1>
    - <响应模板 2>
  keyword_only: <是否仅关键词匹配>
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `intent` | string | ✓ | 意图唯一标识 |
| `priority` | int | ✗ | 优先级 (0-100)，默认 50 |
| `condition` | object | ✗ | 匹配条件 |
| `templates` | string[] | ✓ | 响应模板列表 |
| `keyword_only` | bool | ✗ | 是否仅关键词匹配（不进行代词替换） |

### 响应模板语法

在模板中可以使用占位符，系统会自动替换：

```yaml
templates:
  - "你好，{entity_PERSON}！"           # 命名实体
  - "主语是{subject}，谓语是{predicate}"  # 句法成分
  - "第 1 个词是{token_0}"               # 分词位置
  - "现在是{time_hour}点"               # 时间上下文
  - "你好，{user_name}"                 # 用户信息
  - "当前心情：{var_mood}"              # 脚本变量
```

---

## Lua 脚本编写

### 基本结构

Lua 脚本需要导出两个核心函数：

```lua
-- 匹配函数
function match(context)
    -- 返回匹配结果
end

-- 响应生成函数
function generate_response(context)
    -- 返回响应文本
end

-- 导出模块
return { match = match, generate_response = generate_response }
```

### context 对象结构

Lua 脚本通过 `context` 参数访问所有上下文数据：

```lua
function match(context)
    -- 输入数据
    local text = context.text              -- 原始文本
    local tokens = context.tokens          -- 分词列表
    local entities = context.entities      -- 实体列表
    local pos_tags = context.pos_tags      -- 词性标注
    local dependencies = context.dependencies  -- 依存关系
    local syntax = context.syntax          -- 句法分析
    
    -- 对话上下文
    local turn_count = context.turn_count      -- 对话轮数
    local recent_turns = context.recent_turns  -- 最近对话
    local time_context = context.time_context  -- 时间上下文
    local user_profile = context.user_profile  -- 用户画像
    
    -- 脚本状态
    local matched_scripts = context.matched_scripts  -- 已匹配脚本
    local variables = context.variables    -- 脚本变量
end
```

### 返回值格式

**match 函数返回值：**

```lua
-- 格式 1：布尔值
return true
return false

-- 格式 2：数字（置信度）
return 0.85  -- 85% 置信度

-- 格式 3：详细结果表
return {
    matched = true,           -- 是否匹配
    priority = 90,            -- 优先级
    confidence = 0.9,         -- 置信度
}
```

**generate_response 函数返回值：**

```lua
return "响应文本"
```

---

## 模板变量完整列表

### 1. 命名实体占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{entity_PERSON}` | 人名 | "你好，{entity_PERSON}" → "你好，小明" |
| `{entity_LOCATION}` | 地名 | "{entity_LOCATION}是个好地方" |
| `{entity_ORGANIZATION}` | 机构名 | "{entity_ORGANIZATION}是一家大公司" |
| `{entity_TIME}` | 时间 | "在{entity_TIME}见面" |
| `{entity_DATE}` | 日期 | "{entity_DATE}有活动" |

**通用格式：** `{entity_类型}`，类型不区分大小写

### 2. 句法成分占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{subject}` | 主语 | "{subject}做了什么？" |
| `{predicate}` | 谓语 | "动作是{predicate}" |
| `{object}` | 宾语 | "对象是{object}" |

### 3. 分词占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{token_N}` | 第 N 个分词（从 0 开始） | "{token_0}是第一个词" |
| `{first_token}` | 第一个分词 | "开头是{first_token}" |
| `{last_token}` | 最后一个分词 | "结尾是{last_token}" |

### 4. 时间上下文占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{time_hour}` | 小时（0-23） | "现在是{time_hour}点" |
| `{time_minute}` | 分钟 | "{time_hour}:{time_minute}" |
| `{time_weekday}` | 星期几 | "今天是{time_weekday}" |
| `{time_category}` | 时段分类 | "{time_category}好" → "早上/下午/晚上好" |
| `{time_is_weekend}` | 是否周末 | "{time_is_weekend}" → "true/false" |

### 5. 用户信息占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{user_name}` | 用户姓名 | "你好，{user_name}" |
| `{user_nickname}` | 用户昵称 | "欢迎，{user_nickname}" |
| `{user_address_form}` | 称呼偏好 | "用{user_address_form}称呼" → "你/您" |

### 6. 对话上下文占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{turn_count}` | 对话轮数 | "这是第{turn_count}轮对话" |

### 7. 脚本变量占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{var_变量名}` | 脚本间共享变量 | "{var_mood}" → "happy" |

**设置变量（Lua）：**
```lua
context.variables["mood"] = "happy"
```

**设置变量（Python）：**
```python
context.set_variable("mood", "happy")
```

### 8. 完整示例

```yaml
- intent: personalized_greeting
  priority: 95
  condition:
    keywords: ["你好"]
  templates:
    - "{time_category}好，{user_name}！"
    - "嗨，{user_nickname}！现在是{time_hour}点{time_minute}分"
    - "这是你们的第{turn_count}次对话"

- intent: entity_chat
  priority: 80
  condition:
    entities: ["PERSON", "LOCATION"]
  templates:
    - "你在说{entity_PERSON}吗？"
    - "{entity_LOCATION}是个很有意思的地方"
    - "主语{subject}，宾语{object}"
```

---

## 条件匹配语法

### YAML 条件类型

```yaml
condition:
  # 1. 关键词匹配
  keywords: ["你好", "您好"]
  
  # 2. 实体匹配
  entities: ["PERSON", "LOCATION"]
  
  # 3. 词性匹配
  pos_tags: ["n", "v", "a"]  # 名词、动词、形容词
  
  # 4. 依存关系匹配
  dependencies: ["SBV", "VOB"]  # 主谓、动宾
  
  # 5. 句法成分匹配
  subject: ["我", "你"]
  predicate: ["喜欢", "爱"]
  object: ["音乐", "电影"]
  
  # 6. 分词数量范围
  min_tokens: 5
  max_tokens: 50
  
  # 7. 对话轮数范围
  min_turns: 1
  max_turns: 10
```

### 组合条件

多个条件同时存在时，使用**与**逻辑：

```yaml
condition:
  keywords: ["喜欢"]
  entities: ["PERSON"]
  min_tokens: 3
# 必须同时满足：包含"喜欢"、有人名实体、至少 3 个分词
```

### Lua 条件匹配

```lua
function match(context)
    local text = context.text or ""
    local entities = context.entities or {}
    local tokens = context.tokens or {}
    
    -- 关键词匹配
    if not string.find(text, "喜欢") then
        return false
    end
    
    -- 实体匹配
    local has_person = false
    for _, entity in ipairs(entities) do
        if entity[1] == "PERSON" then
            has_person = true
            break
        end
    end
    if not has_person then
        return false
    end
    
    -- 分词数量
    if #tokens < 3 then
        return false
    end
    
    return { matched = true, priority = 80, confidence = 0.85 }
end
```

---

## 最佳实践

### 1. 优先级设置

遵循系统优先级规范：

| 级别 | 范围 | 用途 | 示例 |
|------|------|------|------|
| P0 | 90-100 | 核心功能 | 问候、告别、紧急 |
| P1 | 70-89 | 实体挖掘 | 人名、地名、事物查询 |
| P2 | 40-69 | 叙事助推 | 话题扩展、引导 |
| P3 | 0-39 | 万能回复 | 回退响应、通用 |

### 2. 模板多样性

使用多个模板避免重复：

```yaml
# ❌ 不好：只有一个模板
templates:
  - "你好！"

# ✓ 好：多个模板随机选择
templates:
  - "你好！很高兴见到你。"
  - "您好！有什么可以帮您的吗？"
  - "嗨！今天过得怎么样？"
```

### 3. 变量使用

合理使用脚本变量实现状态追踪：

```lua
-- 记录用户心情
function generate_response(context)
    local mood = context.variables["user_mood"] or "neutral"
    
    if mood == "happy" then
        return "看到你开心我也很高兴！"
    elseif mood == "sad" then
        return "别难过，一切都会好起来的。"
    else
        return "有什么我可以帮你的吗？"
    end
end
```

### 4. 错误处理

Lua 脚本添加错误处理：

```lua
function match(context)
    -- 安全检查
    if not context or not context.text then
        return false
    end
    
    local success, result = pcall(function()
        -- 匹配逻辑
        return { matched = true, priority = 50 }
    end)
    
    if not success then
        logger.error("匹配错误：" .. tostring(result))
        return false
    end
    
    return result
end
```

### 5. 性能优化

- 避免在 `match` 函数中执行耗时操作
- 高置信度匹配尽早返回
- 使用 `keyword_only: true` 减少不必要的处理

---

## 示例脚本

### 示例 1：问候脚本（YAML）

```yaml
# scripts/greeting.yaml

- intent: greeting_morning
  priority: 95
  condition:
    keywords: ["早", "早上好"]
  templates:
    - "早上好！希望你今天过得愉快。"
    - "早安！有什么计划吗？"
    - "早上好！阳光真好呢。"

- intent: greeting_general
  priority: 90
  condition:
    keywords: ["你好", "您好", "嗨", "hello"]
  templates:
    - "{time_category}好！很高兴见到你。"
    - "你好！有什么我可以帮你的吗？"
    - "嗨！今天过得怎么样？"

- intent: greeting_farewell
  priority: 90
  condition:
    keywords: ["再见", "拜拜", "晚安"]
  templates:
    - "再见！期待下次聊天。"
    - "拜拜！保重。"
    - "晚安！好梦。"
```

### 示例 2：实体对话脚本（YAML）

```yaml
# scripts/entity_chat.yaml

- intent: person_query
  priority: 85
  condition:
    entities: ["PERSON"]
  templates:
    - "你在说{entity_PERSON}吗？能多告诉我一些吗？"
    - "{entity_PERSON}是个很有趣的人。你们是怎么认识的？"
    - "提到{entity_PERSON}，你想到了什么？"

- intent: location_chat
  priority: 80
  condition:
    entities: ["LOCATION", "GPE"]
  templates:
    - "{entity_LOCATION}是个好地方！你去过吗？"
    - "我对{entity_LOCATION}很感兴趣。那里有什么特别的？"
    - "听说{entity_LOCATION}很美。你最喜欢那里的什么？"

- intent: time_chat
  priority: 75
  condition:
    entities: ["TIME", "DATE"]
  templates:
    - "在{entity_TIME}啊，那时候发生了什么？"
    - "{entity_TIME}是个特别的时间点。"
```

### 示例 3：好奇心对话脚本（Lua）

```lua
-- scripts/lua/curiosity_chat.lua

function match(context)
    local text = context.text or ""
    local entities = context.entities or {}
    local turn_count = context.turn_count or 0
    
    -- 至少需要 3 轮对话后才介入
    if turn_count < 3 then
        return false
    end
    
    -- 检查是否有实体
    local has_entity = #entities > 0
    
    -- 检查是否有疑问词
    local has_question = string.find(text, "为什么") 
        or string.find(text, "怎么")
        or string.find(text, "什么")
    
    if has_entity and not has_question then
        return {
            matched = true,
            priority = 75,
            confidence = 0.7
        }
    end
    
    return false
end

function generate_response(context)
    local entities = context.entities or {}
    local entity_text = ""
    local entity_type = ""
    
    -- 获取第一个实体
    if #entities > 0 then
        entity_type = entities[1][1]
        entity_text = entities[1][2]
    end
    
    -- 好奇心回应模板
    local responses = {
        PERSON = {
            "关于" .. entity_text .. "，你最欣赏他什么？",
            entity_text .. "是个怎样的人呢？",
            "你和" .. entity_text .. "是怎么认识的？",
        },
        LOCATION = {
            entity_text .. "有什么特别的地方吗？",
            "你对" .. entity_text .. "印象最深的是什么？",
            "为什么喜欢" .. entity_text .. "呢？",
        },
        ORGANIZATION = {
            entity_text .. "是做什么的？",
            "你对" .. entity_text .. "了解多少？",
        },
    }
    
    -- 根据实体类型选择回应
    local type_responses = responses[entity_type]
    if type_responses then
        -- 随机选择一个回应
        local idx = math.random(#type_responses)
        return type_responses[idx]
    end
    
    -- 默认回应
    return "能多告诉我一些关于" .. entity_text .. "的事情吗？"
end

return { match = match, generate_response = generate_response }
```

### 示例 4：话题扩展脚本（Lua）

```lua
-- scripts/lua/topic_expansion.lua

function match(context)
    local text = context.text or ""
    local turn_count = context.turn_count or 0
    local variables = context.variables or {}
    
    -- 检查是否已记录话题
    local current_topic = variables["current_topic"]
    
    -- 对话进行到一半时扩展话题
    if turn_count >= 5 and turn_count <= 10 and current_topic then
        return {
            matched = true,
            priority = 60,
            confidence = 0.6
        }
    end
    
    return false
end

function generate_response(context)
    local variables = context.variables or {}
    local current_topic = variables["current_topic"] or "这个话题"
    
    local expansions = {
        "说到" .. current_topic .. "，你还对什么感兴趣？",
        "这个话题很有意思。你还想了解其他方面吗？",
        current_topic .. "确实值得探讨。我们聊聊相关的话题怎么样？",
        "我很好奇，你对" .. current_topic .. "有什么特别的看法？",
    }
    
    -- 随机选择
    local idx = math.random(#expansions)
    return expansions[idx]
end

return { match = match, generate_response = generate_response }
```

### 示例 5：万能回复脚本（YAML）

```yaml
# scripts/fallback.yaml

- intent: fallback_general
  priority: 20
  condition:
    min_tokens: 1
    max_tokens: 100
  keyword_only: true
  templates:
    - "嗯嗯，我在听。"
    - "原来是这样啊。"
    - "这很有意思，继续说。"
    - "我理解你的感受。"
    - "能详细说说吗？"

- intent: fallback_short
  priority: 10
  condition:
    max_tokens: 3
  keyword_only: true
  templates:
    - "嗯？"
    - "哦？"
    - "然后呢？"
    - "真的吗？"
```

---

## 调试技巧

### 1. 查看匹配日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('alice.scripting')
logger.setLevel(logging.DEBUG)
```

### 2. 测试脚本匹配

```python
from alice.scripting import ScriptMatcher, ScriptContext

matcher = ScriptMatcher()
# ... 注册引擎和加载脚本 ...

context = ScriptContext(
    text="你好，我叫小明",
    tokens=["你好", "，", "我", "叫", "小明"],
    entities=[("PERSON", "小明")],
    turn_count=1,
)

match = matcher.match(context)
print(f"匹配结果：{match}")
```

### 3. 检查模板变量

```python
from alice.scripting import YAMLScriptEngine

engine = YAMLScriptEngine()
# ... 加载脚本 ...

# 获取意图
intent = engine.get_intent("demo_greeting")
print(f"模板：{intent.templates}")
```

---

## 常见问题

### Q: 模板变量不生效？

A: 检查：
1. 变量名拼写是否正确
2. 上下文中是否有对应数据
3. 占位符格式是否正确（使用花括号）

### Q: 脚本优先级不生效？

A: 检查：
1. `priority` 字段是否在正确位置
2. 优先级范围是否在 0-100
3. 是否有更高优先级的脚本先匹配

### Q: Lua 脚本报错？

A: 检查：
1. 语法是否正确
2. 是否导出了 `match` 和 `generate_response` 函数
3. 是否处理了 nil 值
4. 沙箱模式是否限制了某些操作

---

## 参考资源

- [UNIFIED_SCRIPT_ENGINE.md](../UNIFIED_SCRIPT_ENGINE.md) - 完整架构文档
- [alice/scripting/README.md](../alice/scripting/README.md) - 快速参考
- 测试用例：`tests/scripting/`
