"""
钓鱼机器人服务

模拟真实人类行为，增加钓鱼机器人的识别难度。
"""

import random
from typing import Optional, List, Dict
from datetime import datetime, timezone
from loguru import logger

from config import settings


class HoneypotBehavior:
    """
    钓鱼机器人行为配置
    
    定义不同类型的钓鱼机器人行为模式。
    """
    
    # 正常人类行为模式
    NORMAL_HUMAN = {
        "name": "normal_human",
        "response_length_avg": 50,
        "response_length_std": 20,
        "typing_speed_avg": 5.0,  # 字符/秒
        "typing_speed_std": 1.5,
        "emoji_probability": 0.3,
        "typo_probability": 0.02,
        "pause_probability": 0.1,
        "pause_duration_avg": 3.0,  # 秒
        "question_probability": 0.2,
        "topic_change_probability": 0.15,
    }
    
    # 健谈型人类
    TALKATIVE_HUMAN = {
        "name": "talkative_human",
        "response_length_avg": 80,
        "response_length_std": 30,
        "typing_speed_avg": 4.0,
        "typing_speed_std": 1.0,
        "emoji_probability": 0.5,
        "typo_probability": 0.01,
        "pause_probability": 0.05,
        "pause_duration_avg": 2.0,
        "question_probability": 0.3,
        "topic_change_probability": 0.1,
    }
    
    # 简洁型人类
    BRIEF_HUMAN = {
        "name": "brief_human",
        "response_length_avg": 20,
        "response_length_std": 10,
        "typing_speed_avg": 8.0,
        "typing_speed_std": 2.0,
        "emoji_probability": 0.2,
        "typo_probability": 0.03,
        "pause_probability": 0.15,
        "pause_duration_avg": 5.0,
        "question_probability": 0.1,
        "topic_change_probability": 0.2,
    }
    
    # 谨慎型人类（较少使用元对话）
    CAUTIOUS_HUMAN = {
        "name": "cautious_human",
        "response_length_avg": 40,
        "response_length_std": 15,
        "typing_speed_avg": 6.0,
        "typing_speed_std": 1.2,
        "emoji_probability": 0.25,
        "typo_probability": 0.015,
        "pause_probability": 0.12,
        "pause_duration_avg": 4.0,
        "question_probability": 0.15,
        "topic_change_probability": 0.12,
        "meta_conversation_avoid_probability": 0.8,  # 避免元对话
    }


class HoneypotService:
    """
    钓鱼机器人服务
    
    模拟真实人类行为特征：
    1. 打字速度波动
    2. 响应长度变化
    3. 偶尔的拼写错误
    4. 情绪化表达
    5. 话题转换
    6. 暂停思考
    """
    
    def __init__(self):
        """初始化钓鱼机器人服务"""
        # 常用表情符号
        self.emojis = ["😄", "😂", "🤣", "😊", "😅", "👍", "👌", "❤️", "🔥", "✨"]
        
        # 常见语气词
        self.filler_words = ["嗯", "啊", "这个", "那个", "怎么说呢", "其实", "就是", "然后"]
        
        # 常见拼写错误（拼音输入法常见错误）
        self.common_typos = {
            "的": "得",
            "了": "乐",
            "是": "事",
            "在": "再",
            "我": "偶",
            "什么": "神马",
            "不知道": "布吉岛",
        }
        
        # 话题转换短语
        self.topic_transitions = [
            "对了，",
            "说起来，",
            "话说，",
            "顺便问一下，",
            "哦对了，",
        ]
        
        # 行为模式库
        self.behavior_profiles = {
            "normal": HoneypotBehavior.NORMAL_HUMAN,
            "talkative": HoneypotBehavior.TALKATIVE_HUMAN,
            "brief": HoneypotBehavior.BRIEF_HUMAN,
            "cautious": HoneypotBehavior.CAUTIOUS_HUMAN,
        }
        
        # 会话行为状态
        self.session_behaviors: Dict[int, dict] = {}
    
    def select_behavior_profile(self, session_id: int, user_meta_count: int = 0) -> str:
        """
        为会话选择行为模式
        
        Args:
            session_id: 会话 ID
            user_meta_count: 用户元对话次数
            
        Returns:
            行为模式名称
        """
        # 如果用户频繁使用元对话，更可能遇到谨慎型对手
        if user_meta_count > 5:
            weights = {
                "cautious": 0.5,
                "normal": 0.3,
                "brief": 0.15,
                "talkative": 0.05,
            }
        else:
            # 默认分布
            weights = {
                "normal": 0.4,
                "talkative": 0.25,
                "brief": 0.2,
                "cautious": 0.15,
            }
        
        # 随机选择
        profile = random.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]
        
        # 保存会话行为状态
        self.session_behaviors[session_id] = {
            "profile": profile,
            "message_count": 0,
            "last_response_time": datetime.now(timezone.utc),
            "total_typing_time": 0,
            "meta_responses": 0,
        }
        
        return profile
    
    def get_behavior_profile(self, session_id: int) -> dict:
        """
        获取会话的行为模式
        
        Args:
            session_id: 会话 ID
            
        Returns:
            行为模式配置
        """
        if session_id not in self.session_behaviors:
            return self.behavior_profiles["normal"]
        
        profile_name = self.session_behaviors[session_id]["profile"]
        return self.behavior_profiles.get(profile_name, self.behavior_profiles["normal"])
    
    def simulate_typing_delay(self, response_length: int, session_id: int) -> float:
        """
        模拟人类打字延迟
        
        Args:
            response_length: 响应长度
            session_id: 会话 ID
            
        Returns:
            延迟时间（秒）
        """
        profile = self.get_behavior_profile(session_id)
        
        # 基础打字时间
        typing_speed = random.gauss(
            profile["typing_speed_avg"],
            profile["typing_speed_std"]
        )
        typing_speed = max(1.0, typing_speed)  # 确保至少 1 字符/秒
        
        base_delay = response_length / typing_speed
        
        # 添加随机波动
        jitter = random.uniform(-0.5, 1.0)
        
        # 可能的暂停思考
        if random.random() < profile["pause_probability"]:
            pause = random.gauss(
                profile["pause_duration_avg"],
                profile["pause_duration_avg"] * 0.3
            )
            base_delay += max(0, pause)
        
        return max(0.5, base_delay + jitter)
    
    def add_human_like_variations(self, text: str, session_id: int) -> str:
        """
        添加人类特征到文本
        
        Args:
            text: 原始文本
            session_id: 会话 ID
            
        Returns:
            添加人类特征后的文本
        """
        profile = self.get_behavior_profile(session_id)
        
        # 更新会话状态
        if session_id in self.session_behaviors:
            self.session_behaviors[session_id]["message_count"] += 1
        
        # 1. 添加表情符号
        if random.random() < profile["emoji_probability"]:
            emoji = random.choice(self.emojis)
            if random.random() < 0.5:
                text = emoji + " " + text
            else:
                text = text + " " + emoji
        
        # 2. 添加语气词（句首）
        if random.random() < 0.15:
            filler = random.choice(self.filler_words)
            text = filler + "，" + text
        
        # 3. 模拟拼写错误
        if random.random() < profile["typo_probability"]:
            text = self._introduce_typo(text)
        
        # 4. 添加问题
        if random.random() < profile["question_probability"]:
            questions = [
                "你呢？",
                "你怎么看？",
                "你觉得呢？",
                "是不是？",
                "对吧？",
            ]
            text = text + random.choice(questions)
        
        # 5. 话题转换
        if random.random() < profile["topic_change_probability"]:
            transition = random.choice(self.topic_transitions)
            text = transition + text
        
        return text
    
    def _introduce_typo(self, text: str) -> str:
        """
        在文本中引入拼写错误
        
        Args:
            text: 原始文本
            
        Returns:
            包含拼写错误的文本
        """
        for correct, typo in self.common_typos.items():
            if correct in text and random.random() < 0.3:
                text = text.replace(correct, typo, 1)
                break
        return text
    
    def generate_meta_response(self, session_id: int, user_message: str) -> Optional[str]:
        """
        生成元对话响应（当用户询问身份时）
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息
            
        Returns:
            元对话响应，如果不应答则返回 None
        """
        profile = self.get_behavior_profile(session_id)
        
        # 谨慎型人格更可能避免元对话
        if profile["name"] == "cautious_human":
            if random.random() < profile["meta_conversation_avoid_probability"]:
                return None
        
        # 常见的身份回应
        responses = {
            "identity_assertions": [
                "我当然是真人啊，这有什么好怀疑的？",
                "我是真人，正在参加这个图灵测试实验。",
                "我是人类参与者，你是吗？",
                "如假包换的真人，不信你考考我？",
                "我是真人，这个实验挺有意思的。",
            ],
            "defensive_responses": [
                "为什么要问这个？你是 AI 吗？",
                "你这么问，我反而怀疑你是不是真人了。",
                "这个问题本身就很可疑啊。",
                "我觉得你可能是 AI，一直在试探我。",
            ],
            "casual_responses": [
                "哈哈，我是真人，怎么了？",
                "我是人啊，有什么奇怪的吗？",
                "当然是真人，这还能有假？",
            ],
        }
        
        # 根据用户消息类型选择回应
        if any(word in user_message for word in ["怀疑", "真的", "假的", "骗"]):
            return random.choice(responses["defensive_responses"])
        elif any(word in user_message for word in ["是", "身份", "人类", "机器"]):
            return random.choice(responses["identity_assertions"])
        else:
            return random.choice(responses["casual_responses"])
    
    def get_response_with_delay(
        self, 
        base_response: str, 
        session_id: int,
        is_meta: bool = False,
        user_message: str = ""
    ) -> tuple[str, float]:
        """
        生成带延迟的拟人响应
        
        Args:
            base_response: 基础响应（来自 AI Bot）
            session_id: 会话 ID
            is_meta: 是否为元对话
            user_message: 用户消息
            
        Returns:
            (响应内容，延迟时间)
        """
        # 如果是元对话，尝试生成专门的回应
        if is_meta:
            meta_response = self.generate_meta_response(session_id, user_message)
            if meta_response:
                base_response = meta_response
        
        # 添加人类特征
        humanized_response = self.add_human_like_variations(base_response, session_id)
        
        # 计算打字延迟
        delay = self.simulate_typing_delay(len(humanized_response), session_id)
        
        return humanized_response, delay
    
    def record_meta_response(self, session_id: int):
        """
        记录元对话响应
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self.session_behaviors:
            self.session_behaviors[session_id]["meta_responses"] += 1
    
    def get_session_stats(self, session_id: int) -> dict:
        """
        获取会话统计信息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            统计信息
        """
        if session_id not in self.session_behaviors:
            return {}
        
        stats = self.session_behaviors[session_id].copy()
        profile_name = stats.get("profile", "unknown")
        stats["profile_config"] = self.behavior_profiles.get(profile_name, {})
        
        return stats
    
    def cleanup_session(self, session_id: int):
        """
        清理会话状态
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self.session_behaviors:
            del self.session_behaviors[session_id]


# 全局钓鱼机器人服务实例
_honeypot_service: Optional[HoneypotService] = None


def get_honeypot_service() -> HoneypotService:
    """获取钓鱼机器人服务实例"""
    global _honeypot_service
    
    if _honeypot_service is None:
        _honeypot_service = HoneypotService()
    
    return _honeypot_service
