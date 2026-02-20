#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应生成器模块

负责根据意图和上下文生成合适的响应。

情感分析增强：
- 支持基于情感标签的响应选择
- 提供情感驱动的共情回应
- 支持细粒度情感（喜、怒、哀、惧等）的特定响应
"""

import logging
import random
from typing import Any, Dict, List, Optional

from alice.nlp.syntax_reassembly import SyntaxReassembly

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    响应生成器

    功能:
    - 基于意图的响应选择
    - 基于重组规则的响应生成
    - 回退响应处理
    - 响应多样性控制
    - 情感驱动的共情回应
    """

    def __init__(self, rules_file: Optional[str] = None):
        """
        初始化响应生成器

        Args:
            rules_file: 反射规则文件路径
        """
        self.reassembly_engine = SyntaxReassembly(rules_file=rules_file)

        # 预定义响应库
        self._init_response_pools()

    def _init_response_pools(self) -> None:
        """初始化响应池"""
        # 问候响应
        self.greeting_responses = [
            "你好！有什么可以帮你的吗？",
            "嗨！今天过得怎么样？",
            "你好！想聊些什么呢？",
        ]
        
        # 告别响应
        self.farewell_responses = [
            "再见！很高兴和你聊天！",
            "拜拜，下次再聊！",
            "再见，祝你一切顺利！",
        ]
        
        # 感谢响应
        self.thanks_responses = [
            "不客气！能帮到你我很开心。",
            "别客气，随时找我聊天哦。",
            "小事一桩，有什么问题再来问我。",
        ]
        
        # 肯定响应
        self.affirmation_responses = [
            "嗯，我在听。",
            "好的，继续说。",
            "明白了，然后呢？",
        ]
        
        # 否定响应
        self.negation_responses = [
            "为什么这么想呢？",
            "能说说为什么不同意吗？",
            "唔，看来你有不同的看法。",
        ]
        
        # 问题响应
        self.question_responses = [
            "这是个好问题，你是怎么想的？",
            "我觉得这个问题值得深入思考。",
            "嗯，这个问题我也想知道答案。",
        ]
        
        # 自我介绍响应
        self.self_intro_responses = [
            "我是一个对你的故事充满好奇的朋友呀。",
            "我是 Alice，一个想听你说话的朋友。",
            "我就是我，一个愿意倾听的朋友。",
        ]
        
        # 通用回退响应
        self.fallback_responses = [
            "嗯，我明白了。",
            "能再多说一些吗？",
            "这很有趣，继续说。",
            "我理解你的感受。",
            "为什么会这样呢？",
            "唔，我在听。",
            "原来是这样啊。",
        ]

        # 情感驱动响应
        self._init_empathy_responses()

    def _init_empathy_responses(self) -> None:
        """初始化情感驱动响应池"""
        # 正面情感响应
        self.positive_responses = [
            "哇，听得出你现在心情不错！这种好心情是因为什么呢？",
            "太好了！这种开心的感觉真棒，能多跟我分享一下吗？",
            "真为你高兴！这种时候最想和谁分享呢？",
            "听起来很棒！这种感觉让你想到了什么？",
        ]

        # 负面情感响应
        self.negative_responses = [
            "听起来那阵子你挺不容易的，那种感觉现在还在吗？",
            "我能感受到你的难过，想和我多说说吗？",
            "这种情况确实让人难受，你是怎么应对的呢？",
            "我在这里陪着你，想说什么都可以。",
        ]

        # 细粒度情感响应
        self.emotion_specific_responses = {
            # 喜悦
            "joy": [
                "真为你感到开心！这种喜悦是从哪里来的呢？",
                "太好了！这种快乐的感觉一定很美妙吧？",
            ],
            # 愤怒
            "anger": [
                "听起来这件事让你很生气，能说说发生了什么吗？",
                "我理解你的感受，遇到这种事确实会让人恼火。",
            ],
            # 悲伤
            "sadness": [
                "我能感受到你的难过，想和我多说说吗？",
                "这种悲伤的感觉一定很难熬，我在这里陪着你。",
            ],
            # 恐惧
            "fear": [
                "听起来这件事让你有些害怕，能告诉我更多吗？",
                "别担心，我在这里。这种担心是从哪里来的呢？",
            ],
            # 焦虑
            "anxiety": [
                "听起来你有些焦虑，这种感觉是什么时候开始的？",
                "我理解这种不安的感觉，想和我聊聊吗？",
            ],
            # 厌恶
            "disgust": [
                "听起来这件事让你很反感，能说说为什么吗？",
                "我理解你的感受，遇到这种事确实让人不舒服。",
            ],
            # 惊讶
            "surprise": [
                "哇，这真是个意外！当时你是怎么反应的？",
                "听起来很令人惊讶，接下来发生了什么？",
            ],
        }

        # 情感强度修饰词
        self.intensity_modifiers = {
            "strong": ["真的", "确实", "非常"],
            "moderate": ["有点", "有些", "比较"],
            "weak": ["稍微", "略微"],
        }

    def generate(
        self,
        user_input: str,
        semantic_info: Dict[str, Any],
        intent: str,
    ) -> str:
        """
        生成响应

        Args:
            user_input: 用户输入
            semantic_info: 语义分析结果
            intent: 意图类型

        Returns:
            生成的响应
        """
        # 记录响应策略
        response_strategy = "fallback"  # 默认回退策略
        
        # 1. 尝试基于情感选择响应（优先级最高）
        sentiment_detail = semantic_info.get("sentiment_detail", {})
        if sentiment_detail:
            response = self._select_by_sentiment(
                sentiment_detail=sentiment_detail,
                user_input=user_input,
            )
            if response:
                response_strategy = "sentiment_driven"
                logger.debug(
                    f"响应策略：{response_strategy}",
                    extra={"response_strategy": response_strategy, "intent": intent},
                )
                return response

        # 2. 基于意图选择响应
        response = self._select_by_intent(intent, user_input)
        if response:
            response_strategy = "intent_based"
            logger.debug(
                f"响应策略：{response_strategy}",
                extra={"response_strategy": response_strategy, "intent": intent},
            )
            return response

        # 3. 对于问候、告别、感谢等 keyword_only 意图，不使用重组规则
        # 直接返回回退响应，避免代词替换
        if intent in ("greeting", "farewell", "thanks"):
            logger.debug(
                f"响应策略：{response_strategy}",
                extra={"response_strategy": response_strategy, "intent": intent},
            )
            return self._get_fallback_response()

        # 4. 尝试使用重组规则（仅适用于非 keyword_only 意图）
        if semantic_info.get("tokens"):
            response = self._try_reassembly(user_input, semantic_info)
            if response:
                response_strategy = "reassembly"
                logger.debug(
                    f"响应策略：{response_strategy}",
                    extra={"response_strategy": response_strategy, "intent": intent},
                )
                return response

        # 5. 使用回退响应
        logger.debug(
            f"响应策略：{response_strategy}",
            extra={"response_strategy": response_strategy, "intent": intent},
        )
        return self._get_fallback_response()

    def _select_by_sentiment(
        self,
        sentiment_detail: Dict[str, Any],
        user_input: str,
    ) -> Optional[str]:
        """
        根据情感选择响应

        Args:
            sentiment_detail: 详细情感分析结果
            user_input: 用户输入

        Returns:
            选中的响应
        """
        label = sentiment_detail.get("label", "neutral")
        emotions = sentiment_detail.get("emotions", {})
        intensity = sentiment_detail.get("intensity", "moderate")

        # 1. 优先使用细粒度情感响应
        if emotions:
            # 获取主导情感
            dominant_emotion = max(emotions, key=emotions.get)
            if dominant_emotion in self.emotion_specific_responses:
                responses = self.emotion_specific_responses[dominant_emotion]
                return random.choice(responses)

        # 2. 使用情感极性响应
        if label == "positive":
            return random.choice(self.positive_responses)
        elif label == "negative":
            return random.choice(self.negative_responses)

        return None

    def _select_by_intent(self, intent: str, user_input: str) -> Optional[str]:
        """
        根据意图选择响应
        
        Args:
            intent: 意图类型
            user_input: 用户输入
            
        Returns:
            选中的响应
        """
        if intent == "greeting":
            return random.choice(self.greeting_responses)
        
        elif intent == "farewell":
            return random.choice(self.farewell_responses)
        
        elif intent == "thanks":
            return random.choice(self.thanks_responses)
        
        elif intent == "affirmation":
            return random.choice(self.affirmation_responses)
        
        elif intent == "negation":
            return random.choice(self.negation_responses)
        
        elif intent == "question":
            return random.choice(self.question_responses)
        
        elif intent == "self_introduction":
            return random.choice(self.self_intro_responses)
        
        return None

    def _try_reassembly(
        self,
        user_input: str,
        semantic_info: Dict[str, Any],
    ) -> Optional[str]:
        """
        尝试使用重组规则生成响应
        
        Args:
            user_input: 用户输入
            semantic_info: 语义分析结果
            
        Returns:
            重组后的响应
        """
        if not self.reassembly_engine:
            return None
        
        # 使用简单的重组规则
        tokens = semantic_info.get("tokens", [])
        if not tokens:
            return None
        
        # 尝试使用预设的重组规则
        components = [user_input]
        rules = [
            "你为什么会有'{1}'这样的想法呢？",
            "能多说说关于'{1}'的事吗？",
            "{1}，这是什么时候开始的？",
        ]
        
        rule = random.choice(rules)
        response = self.reassembly_engine.reassemble(
            components=components,
            reassembly_rule=rule,
            apply_pronoun_mapping=True,
        )
        
        return response.strip() if response else None

    def _get_fallback_response(self) -> str:
        """
        获取回退响应
        
        Returns:
            回退响应
        """
        return random.choice(self.fallback_responses)

    def add_custom_response(
        self,
        intent: str,
        responses: List[str],
    ) -> None:
        """
        添加自定义响应
        
        Args:
            intent: 意图类型
            responses: 响应列表
        """
        attr_name = f"{intent}_responses"
        
        if not hasattr(self, attr_name):
            setattr(self, attr_name, [])
        
        existing = getattr(self, attr_name)
        existing.extend(responses)

    def set_fallback_responses(self, responses: List[str]) -> None:
        """
        设置回退响应
        
        Args:
            responses: 响应列表
        """
        self.fallback_responses = responses
