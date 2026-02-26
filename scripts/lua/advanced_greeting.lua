-- 高级问候脚本
-- 支持根据上下文和时间动态生成问候语

---@meta
script_name = "advanced_greeting"
script_version = "1.0.0"
script_priority = 90

-- 主匹配函数
function match(context)
    -- 获取文本和上下文
    local text = context.text or ""
    local turn_count = context.turn_count or 0

    -- 检查问候关键词
    local greeting_keywords = {"你好", "您好", "嗨", "早上好", "晚上好", "晚安"}
    local has_greeting = false

    for _, keyword in ipairs(greeting_keywords) do
        if string.find(text, keyword) then
            has_greeting = true
            break
        end
    end

    if not has_greeting then
        return false
    end

    -- 根据时间调整优先级
    local hour = tonumber(os.date("%H"))
    local time_priority = 0

    if hour >= 6 and hour < 12 then
        time_priority = 5  -- 早上好
    elseif hour >= 12 and hour < 18 then
        time_priority = 3  -- 下午好
    else
        time_priority = 7  -- 晚上好/晚安
    end

    -- 检查实体
    local person_found = false
    if context.entities then
        for _, entity in ipairs(context.entities) do
            if entity.type == "PERSON" then
                person_found = true
                break
            end
        end
    end

    if person_found then
        return true, {
            priority = script_priority + time_priority + 10,
            confidence = 0.9
        }
    end

    -- 根据对话轮数调整优先级
    if turn_count < 5 then
        return true, {
            priority = script_priority + time_priority,
            confidence = 0.8
        }
    else
        return true, {
            priority = script_priority + time_priority - 5,
            confidence = 0.6
        }
    end
end

-- 响应生成函数
function generate_response(context, intent_data)
    -- 响应模板
    local morning_responses = {
        "早上好！今天过得怎么样？",
        "早安！有什么新鲜事吗？",
        "早上好！希望您有个美好的一天。"
    }

    local afternoon_responses = {
        "下午好！今天工作顺利吗？",
        "您好！有什么可以帮您的吗？",
        "下午好！需要休息一下吗？"
    }

    local evening_responses = {
        "晚上好！今天过得如何？",
        "晚安！今天辛苦了。",
        "晚上好！有什么需要帮忙的吗？"
    }

    -- 根据时间选择响应
    local hour = tonumber(os.date("%H"))
    local responses

    if hour >= 6 and hour < 12 then
        responses = morning_responses
    elseif hour >= 12 and hour < 18 then
        responses = afternoon_responses
    else
        responses = evening_responses
    end

    -- 如果检测到人名，添加个性化响应
    local personalized = false
    if context.entities then
        for _, entity in ipairs(context.entities) do
            if entity.type == "PERSON" then
                table.insert(responses, string.format("很高兴见到您，%s！", entity.text))
                personalized = true
                break
            end
        end
    end

    -- 如果是老用户，添加特殊响应
    if (context.turn_count or 0) > 10 and not personalized then
        table.insert(responses, "我们又见面了！很高兴再次和您聊天。")
    end

    -- 返回随机响应
    return responses[math.random(#responses)]
end

-- 可选：定义额外的辅助函数
local function has_keyword(text, keywords)
    for _, keyword in ipairs(keywords) do
        if string.find(text, keyword) then
            return true
        end
    end
    return false
end

return { match = match, generate_response = generate_response }
