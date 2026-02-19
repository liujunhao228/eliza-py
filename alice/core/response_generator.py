#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应生成器模块

负责根据意图和上下文生成合适的响应。
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
        # 1. 基于意图选择响应
        response = self._select_by_intent(intent, user_input)
        if response:
            return response
        
        # 2. 尝试使用重组规则
        if semantic_info.get("tokens"):
            response = self._try_reassembly(user_input, semantic_info)
            if response:
                return response
        
        # 3. 使用回退响应
        return self._get_fallback_response()

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
