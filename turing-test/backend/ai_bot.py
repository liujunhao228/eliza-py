import random
import time
from config import AI_BOT_NAME, AI_TYPING_DELAY_BASE, AI_TYPING_DELAY_PER_CHAR


class SimpleBot:
    """
    简单的规则式聊天机器人（Eliza 风格简化版）
    适合图灵测试实验使用
    """
    
    def __init__(self, name: str = AI_BOT_NAME):
        self.name = name
        self.conversation_history = []
        
        # 关键词回复规则
        self.patterns = {
            "你好": ["你好呀！", "嗨～", "你好，很高兴见到你！"],
            "您好": ["您好呀！", "你好！", "您好～"],
            "你是谁": [f"我是{name}，一个正在参与图灵测试的神秘对话者。", 
                      f"我叫{name}，你猜我是真人还是 AI 呢？😉",
                      f"我是个喜欢聊天的人，你可以叫我{name}。"],
            "你叫什么": [f"我叫{name}～", f"你可以叫我{name}！"],
            "你是真人吗": ["你觉得呢？", "这个嘛...你猜？🤔", "重要吗？我们聊得开心就好～"],
            "你是 ai 吗": ["哈哈，你怀疑我是 AI 吗？", "如果我是 AI，你会觉得失望吗？", "你觉得我像 AI 吗？"],
            "你喜欢什么": ["我喜欢和人聊天，听别人讲故事。", "我喜欢看书、听音乐，你呢？", "我喜欢探索新鲜事物～"],
            "你的爱好": ["平时喜欢看书、看电影，偶尔打打游戏。你呢？", "我喜欢尝试新事物，比如学习新知识～"],
            "今天": ["今天过得还不错，和你聊天很开心～", "今天天气不错，心情也很好！"],
            "天气": ["我不太确定你那边的天气，不过希望你那里阳光明媚～", "天气好的时候心情也会变好呢！"],
            "学习": ["学习是个很有趣的过程，虽然有时候会有点累。", "你在学什么有趣的东西吗？"],
            "学校": ["学校是个充满回忆的地方呢～", "你喜欢你的学校吗？"],
            "作业": ["作业确实有点多，哈哈。加油完成它吧！", "作业是成长的必经之路～"],
            "考试": ["考试加油！相信你一定可以的～", "放轻松，考试没那么可怕！"],
            "无聊": ["那我们来聊聊天吧～", "无聊的时候最适合发现新乐趣了！"],
            "开心": ["开心就好！保持好心情～", "看到你开心我也很开心！😊"],
            "难过": ["怎么了？可以和我说说。", "抱抱～一切都会好起来的。"],
            "谢谢": ["不客气～", "应该的！", "和你聊天我也很开心～"],
            "再见": ["再见啦，祝你有个美好的一天！", "下次再聊～", "拜拜！期待下次相见！"],
            "拜拜": ["拜拜～", "下次再聊！", "再见啦！"],
        }
        
        # 通用回复（当没有匹配到关键词时）
        self.default_responses = [
            "嗯嗯，然后呢？",
            "原来如此，很有意思～",
            "我理解你的感受。",
            "真的吗？详细说说？",
            "哈哈，你这么说也有道理。",
            "我对这个话题很感兴趣，继续说～",
            "嗯...让我想想。",
            "你说的对，我也有类似的想法。",
            "为什么会这么想呢？",
            "这倒是个新鲜的角度～",
        ]
        
        # 追问模板
        self.followups = [
            "你呢？",
            "你怎么看？",
            "你有什么类似的经历吗？",
            "能和我分享一下你的想法吗？",
        ]

    def get_response(self, user_input: str) -> tuple[str, float]:
        """
        根据用户输入生成回复
        
        Returns:
            (回复内容，打字延迟秒数)
        """
        self.conversation_history.append(("user", user_input))
        
        response = self._match_pattern(user_input)
        
        # 计算打字延迟
        delay = AI_TYPING_DELAY_BASE + len(response) * AI_TYPING_DELAY_PER_CHAR
        # 添加一点随机性
        delay += random.uniform(0.5, 1.5)
        
        self.conversation_history.append(("bot", response))
        
        # 限制历史记录长度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return response, delay

    def _match_pattern(self, text: str) -> str:
        """匹配关键词并返回回复"""
        text = text.lower()
        
        # 尝试匹配关键词
        for keyword, responses in self.patterns.items():
            if keyword in text:
                return random.choice(responses)
        
        # 如果没有匹配，根据上下文回复
        if self.conversation_history:
            # 偶尔使用追问
            if random.random() < 0.3:
                return random.choice(self.followups)
        
        # 默认回复
        return random.choice(self.default_responses)

    def reset(self):
        """重置对话历史"""
        self.conversation_history = []


# 全局 bot 实例
bot = SimpleBot()


def get_bot_response(user_input: str) -> tuple[str, float]:
    """获取 AI 回复（供外部调用）"""
    return bot.get_response(user_input)


def reset_bot():
    """重置 bot 状态"""
    bot.reset()
