-- 实体深度分析脚本
-- 支持基于LTP实体分析的复杂对话逻辑

---@meta
script_name = "entity_analysis"
script_version = "1.0.0"
script_priority = 85

-- 主匹配函数
function match(context)
    local text = context.text or ""
    local entities = context.entities or {}
    local nlp = context.nlp or {}

    -- 检查是否包含实体
    if not entities or #entities == 0 then
        return false
    end

    -- 统计实体类型
    local entity_counts = {}
    local has_person = false
    local has_location = false
    local has_organization = false

    for _, entity in ipairs(entities) do
        entity_counts[entity.type] = (entity_counts[entity.type] or 0) + 1
        if entity.type == "PERSON" then
            has_person = true
        elseif entity.type == "LOCATION" then
            has_location = true
        elseif entity.type == "ORGANIZATION" then
            has_organization = true
        end
    end

    -- 根据实体类型计算优先级
    local priority = script_priority

    if has_person and has_location then
        priority = priority + 20  -- 人物+地点：高优先级
    elseif has_person and has_organization then
        priority = priority + 15  -- 人物+组织：较高优先级
    elseif has_person then
        priority = priority + 10  -- 仅人物：中等优先级
    end

    -- 检查句法结构
    local has_subject = false
    local has_object = false

    if nlp.syntax then
        for _, token in ipairs(nlp.syntax.tokens or {}) do
            if token.dep and (token.dep == "SBV" or token.dep == "主语") then
                has_subject = true
            end
            if token.dep and (token.dep == "VOB" or token.dep == "宾语") then
                has_object = true
            end
        end
    end

    -- 如果有完整的句子结构，提高优先级
    if has_subject and has_object then
        priority = priority + 5
    end

    -- 检查关键词
    local keywords = {"知道", "了解", "想知道", "告诉我", "介绍一下", "是什么"}
    for _, keyword in ipairs(keywords) do
        if string.find(text, keyword) then
            priority = priority + 10
            break
        end
    end

    -- 返回匹配结果
    return true, {
        priority = priority,
        confidence = 0.7,
        metadata = {
            entity_counts = entity_counts,
            has_complete_syntax = has_subject and has_object
        }
    }
end

-- 响应生成函数
function generate_response(context, intent_data)
    local entities = context.entities or {}
    local metadata = intent_data.metadata or {}
    local entity_counts = metadata.entity_counts or {}

    -- 基础响应
    local responses = {
        "我注意到了您提到的内容。"
    }

    -- 根据实体数量生成个性化响应
    if entity_counts.PERSON and entity_counts.PERSON > 0 then
        table.insert(responses, "您提到了" .. entity_counts.PERSON .. "个人物。")
    end

    if entity_counts.LOCATION and entity_counts.LOCATION > 0 then
        table.insert(responses, "您提到了" .. entity_counts.LOCATION .. "个地点。")
    end

    if entity_counts.ORGANIZATION and entity_counts.ORGANIZATION > 0 then
        table.insert(responses, "您提到了" .. entity_counts.ORGANIZATION .. "个组织。")
    end

    -- 如果句子结构完整，添加特殊响应
    if metadata.has_complete_syntax then
        table.insert(responses, "您的句子结构很完整。")
    end

    -- 随机选择一个响应
    return responses[math.random(#responses)]
end

-- 实体分析辅助函数
local function analyze_entity_density(entities, text_length)
    if not entities or text_length == 0 then
        return 0
    end

    return #entities / text_length
end

-- 获取主要实体类型
local function get_dominant_entity(entities)
    if not entities then
        return nil
    end

    local type_count = {}
    local max_count = 0
    local dominant_type = nil

    for _, entity in ipairs(entities) do
        type_count[entity.type] = (type_count[entity.type] or 0) + 1
        if type_count[entity.type] > max_count then
            max_count = type_count[entity.type]
            dominant_type = entity.type
        end
    end

    return dominant_type, max_count
end

return {
    match = match,
    generate_response = generate_response,
    helper = {
        analyze_entity_density = analyze_entity_density,
        get_dominant_entity = get_dominant_entity
    }
}