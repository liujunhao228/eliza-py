-- 对话流程控制脚本
-- 支持基于对话历史和用户行为的流程控制

---@meta
script_name = "conversation_flow"
script_version = "1.0.0"
script_priority = 75

-- 对话状态
local conversation_states = {
    initial = "initial",
    greeting = "greeting",
    information_gathering = "information_gathering",
    response_providing = "response_providing",
    confirmation = "confirmation",
    closing = "closing"
}

-- 主匹配函数
function match(context)
    local text = context.text or ""
    local history = context.recent_turns or {}
    local turn_count = context.turn_count or 0
    local current_state = context.conversation_state or conversation_states.initial

    -- 根据当前状态选择匹配策略
    local priority = script_priority

    -- 初始状态匹配
    if current_state == conversation_states.initial then
        if turn_count == 0 then
            -- 第一次对话
            return true, {
                priority = priority + 20,
                confidence = 0.9,
                next_state = conversation_states.greeting,
                action = "start_conversation"
            }
        end
    end

    -- 问候状态匹配
    if current_state == conversation_states.greeting then
        local greeting_keywords = {"名字", "叫什么", "介绍一下", "你是谁"}
        for _, keyword in ipairs(greeting_keywords) do
            if string.find(text, keyword) then
                return true, {
                    priority = priority + 15,
                    confidence = 0.8,
                    next_state = conversation_states.information_gathering,
                    action = "ask_information"
                }
            end
        end
    end

    -- 信息收集状态匹配
    if current_state == conversation_states.information_gathering then
        local info_keywords = {"工作", "爱好", "兴趣", "喜欢", "平时"}
        for _, keyword in ipairs(info_keywords) do
            if string.find(text, keyword) then
                return true, {
                    priority = priority + 10,
                    confidence = 0.7,
                    next_state = conversation_states.response_providing,
                    action = "provide_response"
                }
            end
        end

        -- 检查是否完成了信息收集
        if #history >= 3 and turn_count >= 3 then
            return true, {
                priority = priority + 5,
                confidence = 0.6,
                next_state = conversation_states.confirmation,
                action = "confirm_summary"
            }
        end
    end

    -- 响应提供状态匹配
    if current_state == conversation_states.response_providing then
        -- 检查用户是否满意
        local satisfaction_keywords = {"好的", "谢谢", "明白了", "知道了"}
        for _, keyword in ipairs(satisfaction_keywords) do
            if string.find(text, keyword) then
                return true, {
                    priority = priority,
                    confidence = 0.7,
                    next_state = conversation_states.closing,
                    action = "end_conversation"
                }
            end
        end
    end

    -- 关闭对话状态匹配
    if current_state == conversation_states.closing then
        local closing_keywords = {"再见", "拜拜", "结束", "下次", "88"}
        for _, keyword in ipairs(closing_keywords) do
            if string.find(text, keyword) then
                return true, {
                    priority = priority + 10,
                    confidence = 0.9,
                    next_state = conversation_states.initial,
                    action = "reset_conversation"
                }
            end
        end
    end

    return false
end

-- 响应生成函数
function generate_response(context, intent_data)
    local action = intent_data.action or "default"
    local next_state = intent_data.next_state or context.conversation_state
    local history = context.recent_turns or {}

    -- 更新对话状态
    context.conversation_state = next_state

    -- 根据动作生成响应
    if action == "start_conversation" then
        return "你好！我是Alice，很高兴认识你。"
    elseif action == "ask_information" then
        return "你好！我是Alice。你可以告诉我一些关于你的事情吗？比如你的工作、兴趣爱好等。"
    elseif action == "provide_response" then
        -- 根据历史提供个性化响应
        if #history >= 2 then
            local last_response = history[#history]
            if string.find(last_response, "工作") then
                return "听起来工作很有趣！"
            elseif string.find(last_response, "爱好") or string.find(last_response, "兴趣") then
                return "那很棒！爱好能让生活更丰富多彩。"
            end
        end
        return "我明白了，谢谢分享！"
    elseif action == "confirm_summary" then
        return "让我总结一下我们刚才的对话。您已经分享了一些信息，如果您还想告诉我更多，我很乐意继续听。"
    elseif action == "end_conversation" then
        return "很高兴和你聊天！如果你还有其他问题，随时可以找我。"
    elseif action == "reset_conversation" then
        context.conversation_state = conversation_states.initial
        return "再见！期待下次聊天。"
    else
        return "我明白你的意思。"
    end
end

-- 对话流程管理器
local function get_next_state(current_state, user_action)
    -- 定义状态转换规则
    local state_transitions = {
        [conversation_states.initial] = {
            ["start_conversation"] = conversation_states.greeting
        },
        [conversation_states.greeting] = {
            ["ask_information"] = conversation_states.information_gathering
        },
        [conversation_states.information_gathering] = {
            ["provide_response"] = conversation_states.response_providing,
            ["confirm_summary"] = conversation_states.confirmation
        },
        [conversation_states.response_providing] = {
            ["end_conversation"] = conversation_states.closing
        },
        [conversation_states.confirmation] = {
            ["provide_response"] = conversation_states.response_providing,
            ["end_conversation"] = conversation_states.closing
        },
        [conversation_states.closing] = {
            ["reset_conversation"] = conversation_states.initial
        }
    }

    local transitions = state_transitions[current_state]
    if transitions then
        return transitions[user_action] or current_state
    end

    return current_state
end

-- 检查对话活跃度
local function is_conversation_active(context)
    local history = context.recent_turns or {}
    local turn_count = context.turn_count or 0

    -- 如果太久没有对话，可能需要重启
    if #history >= 10 and turn_count > 20 then
        return false
    end

    return true
end

-- 获取对话建议
local function get_conversation_suggestions(context)
    local suggestions = {}
    local current_state = context.conversation_state or conversation_states.initial

    if current_state == conversation_states.greeting then
        suggestions = {
            "可以告诉我你的名字吗？",
            "你平时喜欢做什么？",
            "你的工作是什么？"
        }
    elseif current_state == conversation_states.information_gathering then
        suggestions = {
            "你的兴趣爱好是什么？",
            "你住在哪个城市？",
            "你有什么特别喜欢的食物吗？"
        }
    end

    return suggestions
end

return {
    match = match,
    generate_response = generate_response,
    states = conversation_states,
    helper = {
        get_next_state = get_next_state,
        is_conversation_active = is_conversation_active,
        get_conversation_suggestions = get_conversation_suggestions
    }
}