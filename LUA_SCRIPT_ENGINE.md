# Lua脚本引擎使用指南

## 概述

Lua脚本引擎是为Alice聊天机器人新增的功能，支持使用Lua脚本实现复杂的对话逻辑、条件判断和动态响应生成。Lua具有轻量级、高性能的特点，非常适合实时对话场景。

## 功能特点

- ✅ **灵活的脚本控制**：支持复杂的逻辑判断和条件匹配
- ✅ **动态响应生成**：基于上下文和用户输入生成个性化响应
- ✅ **安全沙箱**：RestrictedPython提供安全的执行环境
- ✅ **高性能缓存**：脚本编译缓存，避免重复加载
- ✅ **热重载支持**：支持脚本的热重载（开发中）
- ✅ **与YAML引擎集成**：可与现有的YAML脚本引擎共存

## 快速开始

### 1. 启用Lua脚本引擎

在 `config.alice.yaml` 中添加以下配置：

```yaml
# 启用Lua脚本引擎
enable_lua_engine: true

# 指定Lua脚本目录
lua_script_dir: scripts/lua

# Lua脚本配置
lua_cache_size: 100
lua_execution_timeout: 1.0
lua_sandbox_enabled: true
```

### 2. 创建Lua脚本

在 `scripts/lua/` 目录下创建 `.lua` 文件。脚本需要包含两个主要函数：

```lua
---@meta
script_name = "greeting"
script_version = "1.0.0"
script_priority = 90

-- 主匹配函数
function match(context)
    -- 获取上下文
    local text = context.text or ""
    local entities = context.entities or {}

    -- 匹配逻辑
    if string.find(text, "你好") then
        return true, {
            priority = script_priority,
            confidence = 0.9,
            variables = {
                greeted = true
            }
        }
    end

    return false
end

-- 响应生成函数
function generate_response(context, intent_data)
    -- 生成响应
    local responses = {
        "你好！很高兴认识你。",
        "您好！有什么可以帮助您的吗？",
        "嗨！今天过得怎么样？"
    }

    return responses[math.random(#responses)]
end

return { match = match, generate_response = generate_response }
```

### 3. 创建元数据文件（可选）

创建 `.meta.yaml` 文件来配置脚本：

```yaml
name: "greeting"
version: "1.0.0"
priority: 90
description: "问候脚本"
author: "Alice Team"
dependencies: []
tags: ["greeting", "basic"]
enabled: true
max_execution_time: 1.0
sandbox_mode: true
variables:
  greeting_threshold: 80
```

## Lua脚本语法

### 基本结构

```lua
-- 脚本元信息
---@meta
script_name = "example"
script_version = "1.0.0"
script_priority = 50

-- 主匹配函数
function match(context)
    -- 匹配逻辑
    return true, {
        priority = script_priority,
        confidence = 0.8
    }
end

-- 响应生成函数
function generate_response(context, intent_data)
    -- 生成响应
    return "默认响应"
end

-- 返回接口
return { match = match, generate_response = generate_response }
```

### 访问上下文数据

Lua脚本可以访问以下上下文数据：

```lua
function match(context)
    -- 文本
    local text = context.text

    -- NLP结果
    local tokens = context.nlp.tokens
    local entities = context.entities
    local syntax = context.nlp.syntax

    -- 对话历史
    local history = context.recent_turns
    local turn_count = context.turn_count

    -- 其他数据
    local user_profile = context.user_profile
    local time_context = context.time_context

    -- 使用示例
    if entities and #entities > 0 then
        for _, entity in ipairs(entities) do
            print("实体: " .. entity.text .. " 类型: " .. entity.type)
        end
    end

    return true, { priority = 50 }
end
```

### 条件判断

```lua
function match(context)
    local text = context.text or ""
    local turn_count = context.turn_count or 0

    -- 字符串匹配
    if string.find(text, "你好") then
        -- 匹配成功
    end

    -- 数值比较
    if turn_count > 10 then
        -- 超过10轮对话
    end

    -- 实体检查
    if context.entities then
        for _, entity in ipairs(context.entities) do
            if entity.type == "PERSON" then
                -- 找到人物实体
            end
        end
    end

    return false
end
```

### 动态响应生成

```lua
function generate_response(context, intent_data)
    -- 响应模板列表
    local responses = {
        "你好！",
        "您好！",
        "嗨！"
    }

    -- 根据上下文选择
    local hour = tonumber(os.date("%H"))
    if hour >= 6 and hour < 12 then
        responses = {
            "早上好！",
            "早安！"
        }
    elseif hour >= 12 and hour < 18 then
        responses = {
            "下午好！",
            "您好！"
        }
    else
        responses = {
            "晚上好！",
            "晚安！"
        }
    end

    -- 随机选择
    return responses[math.random(#responses)]
end
```

### 辅助函数

```lua
-- 字符串工具
local function has_keyword(text, keywords)
    for _, keyword in ipairs(keywords) do
        if string.find(text, keyword) then
            return true
        end
    end
    return false
end

-- 统计函数
local function count_entities(entities, type)
    local count = 0
    for _, entity in ipairs(entities or {}) do
        if entity.type == type then
            count = count + 1
        end
    end
    return count
end

-- 使用辅助函数
function match(context)
    local text = context.text or ""
    local entities = context.entities or {}

    -- 使用辅助函数
    local greeting_keywords = {"你好", "您好", "嗨"}
    if has_keyword(text, greeting_keywords) then
        local person_count = count_entities(entities, "PERSON")
        if person_count > 0 then
            return true, { priority = 90 }
        end
    end

    return false
end

-- 返回辅助函数
return {
    match = match,
    generate_response = generate_response,
    helper = {
        has_keyword = has_keyword,
        count_entities = count_entities
    }
}
```

## 高级功能

### 对话状态管理

```lua
-- 定义对话状态
local states = {
    initial = "initial",
    greeting = "greeting",
    information_gathering = "information_gathering",
    closing = "closing"
}

function match(context)
    local current_state = context.conversation_state or states.initial

    if current_state == states.initial and string.find(context.text or "", "你好") then
        return true, {
            next_state = states.greeting,
            action = "start_conversation"
        }
    end

    -- ... 其他状态转换逻辑

    return false
end

function generate_response(context, intent_data)
    local next_state = intent_data.next_state

    -- 更新状态
    context.conversation_state = next_state

    if next_state == states.greeting then
        return "你好！很高兴认识你。"
    end

    -- ... 其他状态响应

    return "默认响应"
end
```

### 时间感知

```lua
function match(context)
    local hour = tonumber(os.date("%H"))

    -- 根据时间调整优先级
    local time_priority = 50

    if hour >= 6 and hour < 12 then
        time_priority = 70  -- 早上
    elseif hour >= 12 and hour < 18 then
        time_priority = 60  -- 下午
    else
        time_priority = 80  -- 晚上
    end

    return true, { priority = time_priority }
end

function generate_response(context, intent_data)
    local hour = tonumber(os.date("%H"))

    if hour >= 5 and hour < 12 then
        return "早上好！今天过得怎么样？"
    elseif hour >= 12 and hour < 14 then
        return "中午好！吃饭了吗？"
    elseif hour >= 14 and hour < 18 then
        return "下午好！工作顺利吗？"
    else
        return "晚上好！今天辛苦了。"
    end
end
```

### 个性化响应

```lua
function generate_response(context, intent_data)
    local response = ""

    -- 检查用户名
    if context.user_profile and context.user_profile.name then
        response = response .. context.user_profile.name .. "，"
    end

    -- 检查最后轮次
    if context.last_response then
        -- 基于最后响应生成连续对话
        if string.find(context.last_response, "工作") then
            response = response .. "听起来工作很有趣！"
        elseif string.find(context.last_response, "爱好") then
            response = response .. "那很棒！爱好能让生活更丰富多彩。"
        end
    else
        response = response .. "很高兴认识你！"
    end

    return response
end
```

## 安全限制

Lua脚本运行在受限环境中，以下功能被禁用：

### 禁用的模块

- `os` - 操作系统访问
- `io` - 输入输出操作
- `package` - 包管理
- `debug` - 调试功能
- `coroutine` - 协程（部分限制）

### 禁止的操作

- 文件系统访问
- 网络请求
- 系统命令执行
- 内存管理操作

### 资源限制

- 最大执行时间：1秒（可配置）
- 内存使用限制：2MB
- 调用栈深度限制：100层

## 性能优化

### 缓存机制

脚本引擎使用多层缓存：

1. **编译缓存**：Lua脚本编译后缓存
2. **结果缓存**：匹配结果缓存
3. **元数据缓存**：脚本元数据缓存

### 热重载

开发模式下支持脚本热重载：

```lua
-- 监听文件变化
local hot_reload = require("hot_reload")
hot_reload.watch("scripts/lua/greeting.lua", function(new_script)
    -- 重新加载脚本
    engine.load_script(new_script)
end)
```

### 异步执行

对于耗时操作，可以使用异步执行：

```lua
function match(context)
    -- 异步检查
    local check_result = coroutine.yield(function()
        -- 耗时操作
        return check_database(context)
    end)

    return check_result
end
```

## 错误处理

### 常见错误

1. **语法错误**
   - 检查Lua语法
   - 确保函数定义正确

2. **运行时错误**
   - 检查上下文数据格式
   - 处理nil值

3. **超时错误**
   - 优化脚本逻辑
   - 减少复杂计算

### 错误处理示例

```lua
function safe_match(context)
    local success, result = pcall(function()
        -- 匹配逻辑
        if context.text == nil then
            error("text is nil")
        end
        return true, { priority = 50 }
    end)

    if not success then
        print("匹配错误:", result)
        return false
    end

    return result
end
```

## 最佳实践

### 1. 脚本组织

- 一个脚本文件实现一个功能
- 使用元数据文件配置脚本
- 合理设置优先级

### 2. 性能优化

- 避免复杂的字符串操作
- 使用局部变量提高性能
- 合理使用缓存

### 3. 错误处理

- 始终检查数据有效性
- 使用pcall捕获异常
- 提供降级方案

### 4. 可维护性

- 添加清晰的注释
- 使用有意义的变量名
- 保持代码简洁

## 示例脚本

### 实体检测脚本

```lua
---@meta
script_name = "entity_detector"
script_version = "1.0.0"
script_priority = 80

function match(context)
    local text = context.text or ""
    local entities = context.entities or {}

    -- 检查是否有实体
    if not entities or #entities == 0 then
        return false
    end

    -- 统计实体类型
    local person_count = 0
    local location_count = 0

    for _, entity in ipairs(entities) do
        if entity.type == "PERSON" then
            person_count = person_count + 1
        elseif entity.type == "LOCATION" then
            location_count = location_count + 1
        end
    end

    -- 根据实体数量调整优先级
    local priority = script_priority

    if person_count > 0 and location_count > 0 then
        priority = priority + 20  -- 人物+地点：高优先级
    elseif person_count > 0 then
        priority = priority + 10  -- 仅人物：中等优先级
    end

    return true, {
        priority = priority,
        confidence = 0.7,
        metadata = {
            person_count = person_count,
            location_count = location_count
        }
    }
end

function generate_response(context, intent_data)
    local metadata = intent_data.metadata or {}

    local responses = {
        "我注意到了你提到的一些信息。"
    }

    if metadata.person_count and metadata.person_count > 0 then
        table.insert(responses, "你提到了" .. metadata.person_count .. "个人物。")
    end

    if metadata.location_count and metadata.location_count > 0 then
        table.insert(responses, "你提到了" .. metadata.location_count .. "个地点。")
    end

    return responses[math.random(#responses)]
end
```

### 情感分析脚本

```lua
---@meta
script_name = "sentiment_analyzer"
script_version = "1.0.0"
script_priority = 70

-- 情感词典
local sentiment_words = {
    positive = {"好", "棒", "喜欢", "开心", "高兴", "满意"},
    negative = {"坏", "差", "讨厌", "难过", "失望", "生气"}
}

function analyze_sentiment(text)
    local score = 0

    for _, word in ipairs(sentiment_words.positive) do
        if string.find(text, word) then
            score = score + 1
        end
    end

    for _, word in ipairs(sentiment_words.negative) do
        if string.find(text, word) then
            score = score - 1
        end
    end

    return score
end

function match(context)
    local text = context.text or ""
    local sentiment_score = analyze_sentiment(text)

    -- 根据情感分数匹配
    if sentiment_score > 0 then
        return true, {
            priority = 80,
            confidence = 0.8,
            sentiment = "positive"
        }
    elseif sentiment_score < 0 then
        return true, {
            priority = 80,
            confidence = 0.8,
            sentiment = "negative"
        }
    end

    return false
end

function generate_response(context, intent_data)
    local sentiment = intent_data.sentiment

    if sentiment == "positive" then
        local responses = {
            "很高兴听到你的好消息！",
            "太棒了！为你感到高兴。",
            "这真是个好消息！"
        }
        return responses[math.random(#responses)]
    elseif sentiment == "negative" then
        local responses = {
            "我理解你的感受，一切都会好起来的。",
            "抱抱，希望你能好起来。",
            "别难过，有什么我可以帮忙的吗？"
        }
        return responses[math.random(#responses)]
    end

    return "我明白你的意思。"
end
```

## 故障排除

### 常见问题

1. **脚本不加载**
   - 检查文件路径
   - 确认语法正确
   - 查看日志错误

2. **匹配失败**
   - 检查优先级设置
   - 验证匹配逻辑
   - 确认上下文数据

3. **响应为空**
   - 检查生成函数
   - 确认返回格式
   - 查看执行错误

### 调试技巧

1. **启用调试模式**
```lua
-- 在脚本中添加调试输出
print("匹配文本:", context.text)
print("实体数量:", #context.entities)
```

2. **使用日志**
```python
# 在Python代码中启用日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

3. **逐步测试**
```python
# 分步测试
config = LuaScriptConfig(...)
lua_engine = LuaScriptEngine()

# 1. 测试加载
print(lua_engine.load_script(config))

# 2. 测试匹配
print(lua_engine.match_script(...))

# 3. 测试响应
print(lua_engine.generate_response(...))
```

## 更新日志

### v1.0.0 (2026-02-24)
- 初始版本发布
- 支持基本Lua脚本执行
- 实现安全沙箱
- 添加缓存机制
- 支持与YAML引擎集成

### 计划功能
- [ ] 热重载支持
- [ ] 脚本版本管理
- [ ] 性能监控
- [ ] 更多内置函数
- [ ] 脚本依赖管理