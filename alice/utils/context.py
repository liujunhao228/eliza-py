#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理模块 - 增强版
提供对话上下文记忆和话题追踪功能
集成命名实体识别（NER）支持
"""

from collections import deque
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class EntityMention:
    """实体提及记录"""
    text: str                    # 实体文本
    entity_type: str             # 实体类型
    mention_time: datetime = field(default_factory=datetime.now)
    frequency: int = 1           # 提及频率
    last_mentioned: datetime = field(default_factory=datetime.now)
    context: str = ""            # 提及的上下文
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'text': self.text,
            'type': self.entity_type,
            'first_mention': self.mention_time.isoformat(),
            'last_mention': self.last_mentioned.isoformat(),
            'frequency': self.frequency,
            'context': self.context,
            'metadata': self.metadata
        }


@dataclass
class MemoryItem:
    """记忆项"""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    type: str = "general"  # 'person', 'event', 'topic', 'emotion'
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'type': self.type,
            'metadata': self.metadata
        }


class ContextManager:
    """上下文管理器（增强版 - 支持实体追踪）"""

    def __init__(self, max_items: int = 10):
        """
        初始化上下文管理器

        Args:
            max_items: 最大记忆项数量
        """
        self.memory = deque(maxlen=max_items)
        self.current_topic = ""
        self.mentioned_persons = set()
        self.recent_events = deque(maxlen=5)
        self.emotion_history = deque(maxlen=5)

        # 实体追踪增强
        self.entity_mentions: Dict[str, EntityMention] = {}  # 实体提及记录
        self.person_chain: deque = deque(maxlen=10)  # 人物提及链
        self.topic_chain: deque = deque(maxlen=10)   # 话题链
        self.entity_relations: Dict[str, Set[str]] = {}  # 实体关系

    def update_context(self, analysis: Dict, user_input: str):
        """
        更新对话上下文

        Args:
            analysis: 语义分析结果
            user_input: 用户输入
        """
        # 更新提及的人物
        self._update_persons(analysis, user_input)

        # 更新话题
        self._update_topic(user_input)

        # 记录事件
        self._record_events(analysis, user_input)

        # 记录情感
        self._record_emotion(analysis)

        # 添加到记忆队列
        self._add_to_memory(user_input, analysis)

        # 【新增】更新实体追踪
        self._update_entity_tracking(analysis, user_input)

    def _update_entity_tracking(self, analysis: Dict, user_input: str):
        """
        更新实体追踪记录

        Args:
            analysis: 语义分析结果
            user_input: 用户输入
        """
        entities = analysis.get('entities', [])
        for entity_type, entity_text in entities:
            # 创建或更新实体提及记录
            entity_key = f"{entity_type}:{entity_text}"

            if entity_key in self.entity_mentions:
                # 更新现有实体
                mention = self.entity_mentions[entity_key]
                mention.frequency += 1
                mention.last_mentioned = datetime.now()
                mention.context = user_input
            else:
                # 创建新实体记录
                mention = EntityMention(
                    text=entity_text,
                    entity_type=entity_type,
                    context=user_input
                )
                self.entity_mentions[entity_key] = mention

            # 更新人物链
            if entity_type in ['person', 'title', 'pronoun']:
                self.person_chain.append({
                    'text': entity_text,
                    'type': entity_type,
                    'timestamp': datetime.now()
                })

            # 更新话题链
            if entity_type in ['location', 'organization', 'time']:
                self.topic_chain.append({
                    'text': entity_text,
                    'type': entity_type,
                    'timestamp': datetime.now()
                })
    
    def _update_persons(self, analysis: Dict, user_input: str):
        """更新提及的人物"""
        # 从实体中提取人物
        entities = analysis.get('entities', [])
        for entity_type, entity_name in entities:
            if entity_type == 'pronoun':
                continue
            
            # 检查是否可能是人名或称谓
            person_keywords = ['朋友', '家人', '同事', '同学', '老板', '老师', 
                              '爸', '妈', '哥', '姐', '弟', '妹', '他', '她']
            if any(kw in entity_name for kw in person_keywords):
                self.mentioned_persons.add(entity_name)
        
        # 从文本中直接提取人名（简化版）
        import re
        # 匹配常见的称谓
        titles = re.findall(r'[小老][张王李赵刘陈杨黄周吴徐孙朱马胡郭何高郑罗]', user_input)
        for title in titles:
            self.mentioned_persons.add(title)
    
    def _update_topic(self, user_input: str):
        """更新当前话题"""
        # 简单的话题检测逻辑
        topic_indicators = ['关于', '谈到', '讨论', '聊聊', '说', '讲']
        for indicator in topic_indicators:
            if indicator in user_input:
                # 提取话题关键词
                parts = user_input.split(indicator)
                if len(parts) > 1:
                    # 取后面的内容作为话题
                    topic = parts[1].strip('吧吗？！。. ')
                    if topic and len(topic) < 20:  # 限制话题长度
                        self.current_topic = topic
                        break
    
    def _record_events(self, analysis: Dict):
        """记录重要事件"""
        # 检测事件相关的动词
        event_verbs = ['去', '做', '发生', '出现', '开始', '结束', '看了', '买了', '吃了']
        tokens = analysis.get('tokens', list(user_input))

        if any(verb in user_input for verb in event_verbs):
            event_record = {
                'description': user_input,
                'timestamp': datetime.now(),
                'components': analysis.get('tokens', []),
            }
            self.recent_events.append(event_record)

    def _add_to_memory(self, content: str, analysis: Dict):
        """
        添加到记忆队列

        Args:
            content: 内容
            analysis: 语义分析结果
        """
        item_type = self._classify_content(content, analysis)
        memory_item = MemoryItem(
            content=content,
            timestamp=datetime.now(),
            type=item_type,
            metadata={
                'entities': analysis.get('entities', []),
            }
        )
        self.memory.append(memory_item)

    def _classify_content(self, content: str, analysis: Dict) -> str:
        """
        内容分类

        Args:
            content: 内容
            analysis: 语义分析结果

        Returns:
            内容类型
        """
        entities = analysis.get('entities', [])

        # 检查是否与人相关
        if any(ent[0] == 'pronoun' or any(kw in ent[1] for kw in ['朋友', '家人', '同事'])
               for ent in entities if isinstance(ent, tuple) and len(ent) > 1):
            return 'person'

        # 检查是否与事件相关
        event_verbs = ['去', '做', '发生', '出现', '开始', '结束']
        if any(verb in content for verb in event_verbs):
            return 'event'

        return 'general'
    
    def get_context_state(self) -> Dict:
        """
        获取当前上下文状态

        Returns:
            上下文状态字典
        """
        return {
            'current_topic': self.current_topic,
            'mentioned_persons': list(self.mentioned_persons),
            'recent_events': list(self.recent_events),
            'memory_items': [item.to_dict() for item in self.memory],
            'has_recent_narrative': len(self.recent_events) > 0,
            'conversation_length': len(self.memory),
            'emotion_trend': self._get_emotion_trend(),
            # 新增实体追踪信息
            'entity_mentions': {k: v.to_dict() for k, v in self.entity_mentions.items()},
            'recent_person_chain': list(self.person_chain)[-5:],
            'topic_chain': list(self.topic_chain)[-5:]
        }

    def get_entity_mentions(self, entity_type: Optional[str] = None) -> List[EntityMention]:
        """
        获取实体提及记录

        Args:
            entity_type: 实体类型过滤，None 则返回所有

        Returns:
            实体提及列表
        """
        if entity_type is None:
            return list(self.entity_mentions.values())

        return [
            mention for mention in self.entity_mentions.values()
            if mention.entity_type == entity_type
        ]

    def get_person_chain(self, limit: int = 5) -> List[Dict]:
        """
        获取人物提及链

        Args:
            limit: 最大返回数量

        Returns:
            人物提及列表
        """
        return list(self.person_chain)[-limit:]

    def get_topic_chain(self, limit: int = 5) -> List[Dict]:
        """
        获取话题链

        Args:
            limit: 最大返回数量

        Returns:
            话题列表
        """
        return list(self.topic_chain)[-limit:]

    def get_most_mentioned_entity(self, entity_type: Optional[str] = None) -> Optional[EntityMention]:
        """
        获取提及频率最高的实体

        Args:
            entity_type: 实体类型过滤，None 则返回所有类型中频率最高的

        Returns:
            提及频率最高的实体
        """
        mentions = self.get_entity_mentions(entity_type)
        if not mentions:
            return None

        return max(mentions, key=lambda m: m.frequency)

    def get_entities_in_context(self, time_window_minutes: int = 5) -> List[EntityMention]:
        """
        获取指定时间窗口内的实体

        Args:
            time_window_minutes: 时间窗口（分钟）

        Returns:
            时间窗口内的实体列表
        """
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)

        return [
            mention for mention in self.entity_mentions.values()
            if mention.last_mentioned > cutoff_time
        ]

    def find_entity_by_text(self, text: str) -> Optional[EntityMention]:
        """
        根据文本查找实体

        Args:
            text: 实体文本

        Returns:
            实体提及记录，不存在返回 None
        """
        for mention in self.entity_mentions.values():
            if mention.text == text:
                return mention
        return None

    def get_related_entities(self, entity_text: str) -> List[str]:
        """
        获取与指定实体相关的其他实体

        Args:
            entity_text: 实体文本

        Returns:
            相关实体文本列表
        """
        return list(self.entity_relations.get(entity_text, set()))

    def add_entity_relation(self, entity1: str, entity2: str):
        """
        添加实体关系

        Args:
            entity1: 实体 1
            entity2: 实体 2
        """
        if entity1 not in self.entity_relations:
            self.entity_relations[entity1] = set()
        self.entity_relations[entity1].add(entity2)

        if entity2 not in self.entity_relations:
            self.entity_relations[entity2] = set()
        self.entity_relations[entity2].add(entity1)

    def get_relevant_memory(self, query: str, max_results: int = 3) -> List[MemoryItem]:
        """
        根据查询获取相关记忆
        
        Args:
            query: 查询关键词
            max_results: 最大返回数量
            
        Returns:
            相关记忆项列表
        """
        relevant_items = []
        for item in self.memory:
            # 简单的相关性匹配
            if query in item.content or any(query in str(v) for v in item.metadata.values()):
                relevant_items.append(item)
        
        return relevant_items[:max_results]
    
    def get_recent_persons(self, limit: int = 3) -> List[str]:
        """
        获取最近提及的人物
        
        Args:
            limit: 最大返回数量
            
        Returns:
            人物列表
        """
        return list(self.mentioned_persons)[-limit:]
    
    def get_recent_events(self, limit: int = 3) -> List[Dict]:
        """
        获取最近事件
        
        Args:
            limit: 最大返回数量
            
        Returns:
            事件列表
        """
        return list(self.recent_events)[-limit:]
    
    def clear_expired_memory(self, hours: int = 24):
        """
        清除过期记忆
        
        Args:
            hours: 保留的小时数
        """
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        self.memory = deque(
            [item for item in self.memory if item.timestamp > cutoff_time],
            maxlen=self.memory.maxlen
        )
    
    def reset(self):
        """重置上下文"""
        self.memory.clear()
        self.current_topic = ""
        self.mentioned_persons.clear()
        self.recent_events.clear()
        self.emotion_history.clear()
        # 重置实体追踪
        self.entity_mentions.clear()
        self.person_chain.clear()
        self.topic_chain.clear()
        self.entity_relations.clear()


class ConversationHistory:
    """对话历史记录"""
    
    def __init__(self, max_turns: int = 20):
        """
        初始化对话历史
        
        Args:
            max_turns: 最大对话轮数
        """
        self.history = deque(maxlen=max_turns)
    
    def add_turn(self, user_input: str, bot_response: str):
        """
        添加一轮对话
        
        Args:
            user_input: 用户输入
            bot_response: 机器人回复
        """
        self.history.append({
            'user': user_input,
            'bot': bot_response,
            'timestamp': datetime.now()
        })
    
    def get_history(self, last_n: int = 5) -> List[Dict]:
        """
        获取最近的对话历史
        
        Args:
            last_n: 返回最近 n 轮对话
            
        Returns:
            对话历史列表
        """
        return list(self.history)[-last_n:]
    
    def get_last_user_input(self) -> Optional[str]:
        """获取最后一次用户输入"""
        if self.history:
            return self.history[-1]['user']
        return None
    
    def get_last_bot_response(self) -> Optional[str]:
        """获取最后一次机器人回复"""
        if self.history:
            return self.history[-1]['bot']
        return None
    
    def clear(self):
        """清空对话历史"""
        self.history.clear()
    
    def to_list(self) -> List[Dict]:
        """转换为列表格式"""
        return [
            {
                'user': turn['user'],
                'bot': turn['bot'],
                'timestamp': turn['timestamp'].isoformat()
            }
            for turn in self.history
        ]
