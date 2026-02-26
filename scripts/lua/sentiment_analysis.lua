-- 情感分析脚本
-- 支持基于文本情感分析的响应生成

---@meta
script_name = "sentiment_analysis"
script_version = "1.0.0"
script_priority = 70

-- 情感关键词
local positive_keywords = {
    "开心", "高兴", "快乐", "幸福", "美好", "棒", "赞", "喜欢", "爱",
    "满意", "惊喜", "感动", "温暖", "阳光", "灿烂", "顺利", "成功"
}

local negative_keywords = {
    "难过", "伤心", "痛苦", "悲伤", "沮丧", "失望", "生气", "愤怒",
    "烦恼", "焦虑", "害怕", "恐惧", "孤独", "寂寞", "累", "烦", "糟糕"
}

-- 主匹配函数
function match(context)
    local text = context.text or ""

    -- 统计情感关键词
    local positive_count = 0
    local negative_count = 0

    for _, keyword in ipairs(positive_keywords) do
        if string.find(text, keyword) then
            positive_count = positive_count + 1
        end
    end

    for _, keyword in ipairs(negative_keywords) do
        if string.find(text, keyword) then
            negative_count = negative_count + 1
        end
    end

    -- 如果没有检测到情感词，不匹配
    if positive_count == 0 and negative_count == 0 then
        return false
    end

    -- 计算情感得分
    local sentiment_score = positive_count - negative_count
    local total = positive_count + negative_count

    -- 返回匹配结果
    return true, {
        priority = script_priority + math.abs(sentiment_score) * 5,
        confidence = math.min(0.9, 0.5 + total * 0.1),
        metadata = {
            positive_count = positive_count,
            negative_count = negative_count,
            sentiment_score = sentiment_score,
            is_positive = sentiment_score > 0,
            is_negative = sentiment_score < 0
        }
    }
end

-- 响应生成函数
function generate_response(context, intent_data)
    local metadata = intent_data.metadata or {}
    local is_positive = metadata.is_positive
    local is_negative = metadata.is_negative
    local score = metadata.sentiment_score or 0

    -- 积极情感响应
    local positive_responses = {
        "听起来你心情不错！有什么好事发生吗？",
        "真为你感到高兴！继续保持这份好心情吧。",
        "太好了！希望你一直这么开心。",
        "看到你这么开心，我也很高兴！",
        "这真是个好消息！能和我详细说说吗？"
    }

    -- 消极情感响应
    local negative_responses = {
        "听起来你心情不太好，想聊聊吗？",
        "我理解你的感受，有时候确实会这样。",
        "别太难过了，一切都会好起来的。",
        "我在这里陪着你，有什么想说的都可以告诉我。",
        "辛苦了，要不要休息一下？"
    }

    -- 中性情感响应（正负相抵）
    local neutral_responses = {
        "我能感受到你的复杂心情。",
        "生活就是这样，有起有落。",
        "你的感受很正常，每个人都有这样的时候。"
    }

    -- 根据情感选择响应
    if is_positive then
        return positive_responses[math.random(#positive_responses)]
    elseif is_negative then
        return negative_responses[math.random(#negative_responses)]
    else
        return neutral_responses[math.random(#neutral_responses)]
    end
end

-- 辅助函数：计算情感强度
local function calculate_sentiment_intensity(positive_count, negative_count)
    local total = positive_count + negative_count
    if total == 0 then
        return 0
    end
    return math.abs(positive_count - negative_count) / total
end

-- 辅助函数：获取主导情感
local function get_dominant_sentiment(positive_count, negative_count)
    if positive_count > negative_count then
        return "positive"
    elseif negative_count > positive_count then
        return "negative"
    else
        return "neutral"
    end
end

return {
    match = match,
    generate_response = generate_response,
    helper = {
        calculate_sentiment_intensity = calculate_sentiment_intensity,
        get_dominant_sentiment = get_dominant_sentiment
    }
}
