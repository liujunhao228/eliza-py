#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理器模块

负责对话上下文的管理，包括：
- 对话历史追踪
- 实体记忆
- 话题追踪
- 上下文智能更新
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """对话轮次"""
    user_input: str
    bot_response: str
    timestamp: datetime = field(default_factory=datetime.now)
    entities: List[Tuple[str, str]] = field(default_factory=list)
    intent: str = "general"


class ContextManager:
    """
    上下文管理器
    
    功能:
    - 管理对话历史（限制长度）
    - 追踪实体和话题
    - 提供上下文感知的对话支持
    - 智能上下文更新
    """

    def __init__(self, max_items: int = 10, max_turns: int = 20):
        """
        初始化上下文管理器
        
        Args:
            max_items: 最大上下文条目数
            max_turns: 最大对话轮数
        """
        self.max_items = max_items
        self.max_turns = max_turns
        
        # 短期上下文（最近几轮对话）
        self._short_term: deque = deque(maxlen=max_items)
        
        # 对话历史（完整历史记录）
        self._history: deque = deque(maxlen=max_turns)
        
        # 实体记忆
        self._entities: Dict[str, List[Dict[str, Any]]] = {}
        
        # 话题追踪
        self._topics: Dict[str, Dict[str, Any]] = {}
        self._current_topic: Optional[str] = None
        
        # 用户偏好
        self._user_preferences: Dict[str, Any] = {}

    def update(
        self,
        user_input: str,
        bot_response: str,
        entities: Optional[List[Tuple[str, str]]] = None,
        intent: str = "general",
    ) -> None:
        """
        更新上下文

        Args:
            user_input: 用户输入
            bot_response: 机器人响应
            entities: 实体列表 [(类型，文本), ...]
            intent: 意图类型
        """
        # 创建对话轮次
        turn = ConversationTurn(
            user_input=user_input,
            bot_response=bot_response,
            entities=entities or [],
            intent=intent,
        )
        
        # 添加到短期上下文
        self._short_term.append(turn)
        
        # 添加到对话历史
        self._history.append(turn)
        
        # 更新实体记忆
        if entities:
            self._update_entities(entities)
        
        # 更新话题
        self._update_topic(user_input, bot_response, intent)
        
        logger.debug(f"上下文已更新：{len(self._history)} 轮对话")

    def _update_entities(self, entities: List[Tuple[str, str]]) -> None:
        """
        更新实体记忆
        
        Args:
            entities: 实体列表
        """
        for entity_type, entity_text in entities:
            if entity_type not in self._entities:
                self._entities[entity_type] = []
            
            # 检查实体是否已存在
            existing = next(
                (e for e in self._entities[entity_type] if e["text"] == entity_text),
                None,
            )
            
            if existing:
                # 更新现有实体
                existing["count"] = existing.get("count", 0) + 1
                existing["last_mentioned"] = datetime.now().isoformat()
            else:
                # 添加新实体
                self._entities[entity_type].append({
                    "text": entity_text,
                    "first_mentioned": datetime.now().isoformat(),
                    "last_mentioned": datetime.now().isoformat(),
                    "count": 1,
                })

    def _update_topic(
        self,
        user_input: str,
        bot_response: str,
        intent: str,
    ) -> None:
        """
        更新话题追踪
        
        Args:
            user_input: 用户输入
            bot_response: 机器人响应
            intent: 意图类型
        """
        # 基于意图识别话题
        topic = intent
        
        if topic != self._current_topic:
            # 话题切换
            if self._current_topic:
                # 保存旧话题状态
                self._topics[self._current_topic]["end_time"] = datetime.now().isoformat()
            
            # 开启新话题
            self._current_topic = topic
            self._topics[topic] = {
                "start_time": datetime.now().isoformat(),
                "turn_count": 1,
                "keywords": [],
            }
        else:
            # 当前话题继续
            if topic in self._topics:
                self._topics[topic]["turn_count"] += 1

    def get_recent_turns(self, n: int = 3) -> List[ConversationTurn]:
        """
        获取最近 n 轮对话
        
        Args:
            n: 轮数
            
        Returns:
            对话轮次列表
        """
        return list(self._short_term)[-n:]

    def get_history(self) -> List[ConversationTurn]:
        """
        获取完整对话历史
        
        Returns:
            对话历史列表
        """
        return list(self._history)

    def get_entities(
        self,
        entity_type: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取实体记忆
        
        Args:
            entity_type: 实体类型（可选）
            
        Returns:
            实体字典
        """
        if entity_type:
            return {entity_type: self._entities.get(entity_type, [])}
        return self._entities.copy()

    def get_recent_entities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近提到的实体
        
        Args:
            limit: 数量限制
            
        Returns:
            实体列表
        """
        all_entities = []
        for entity_type, entities in self._entities.items():
            for entity in entities:
                all_entities.append({
                    "type": entity_type,
                    **entity,
                })
        
        # 按最后提及时间排序
        sorted_entities = sorted(
            all_entities,
            key=lambda e: e.get("last_mentioned", ""),
            reverse=True,
        )
        
        return sorted_entities[:limit]

    def get_current_topic(self) -> Optional[str]:
        """获取当前话题"""
        return self._current_topic

    def get_topic_history(self) -> Dict[str, Dict[str, Any]]:
        """获取话题历史"""
        return self._topics.copy()

    def get_context_summary(self) -> Dict[str, Any]:
        """
        获取上下文摘要
        
        Returns:
            上下文摘要字典
        """
        return {
            "total_turns": len(self._history),
            "recent_turns": len(self._short_term),
            "current_topic": self._current_topic,
            "total_entities": sum(len(e) for e in self._entities.values()),
            "recent_entities": self.get_recent_entities(3),
            "topics": list(self._topics.keys()),
        }

    def get_conversation_context_for_prompt(self) -> str:
        """
        生成用于提示的对话上下文
        
        Returns:
            格式化的上下文字符串
        """
        if not self._short_term:
            return ""
        
        lines = []
        for turn in self._short_term:
            lines.append(f"用户：{turn.user_input}")
            lines.append(f"Alice: {turn.bot_response}")
        
        return "\n".join(lines)

    def clear(self) -> None:
        """清空上下文"""
        self._short_term.clear()
        self._history.clear()
        self._entities.clear()
        self._topics.clear()
        self._current_topic = None
        self._user_preferences.clear()
        
        logger.info("上下文已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_turns": len(self._history),
            "short_term_size": len(self._short_term),
            "total_entities": sum(len(e) for e in self._entities.values()),
            "total_topics": len(self._topics),
            "current_topic": self._current_topic,
        }
