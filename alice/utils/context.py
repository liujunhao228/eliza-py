#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理模块 - 增强版
提供对话上下文记忆和话题追踪功能
"""

from collections import deque
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


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
    """上下文管理器"""
    
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
    
    def _record_events(self, analysis: Dict, user_input: str):
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
    
    def _record_emotion(self, analysis: Dict):
        """记录情感状态"""
        sentiment = analysis.get('sentiment', 0)
        if abs(sentiment) > 0.3:  # 情感强度超过阈值
            emotion_record = {
                'sentiment': sentiment,
                'timestamp': datetime.now(),
                'type': 'positive' if sentiment > 0 else 'negative'
            }
            self.emotion_history.append(emotion_record)
    
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
                'sentiment': analysis.get('sentiment', 0),
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
        sentiment = analysis.get('sentiment', 0)
        
        # 检查是否与人相关
        if any(ent[0] == 'pronoun' or any(kw in ent[1] for kw in ['朋友', '家人', '同事']) 
               for ent in entities if isinstance(ent, tuple) and len(ent) > 1):
            return 'person'
        
        # 检查是否与情感相关
        if abs(sentiment) > 0.5:
            return 'emotion'
        
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
            'emotion_trend': self._get_emotion_trend()
        }
    
    def _get_emotion_trend(self) -> str:
        """
        获取情感趋势
        
        Returns:
            'positive', 'negative', 或 'neutral'
        """
        if not self.emotion_history:
            return 'neutral'
        
        avg_sentiment = sum(e['sentiment'] for e in self.emotion_history) / len(self.emotion_history)
        if avg_sentiment > 0.2:
            return 'positive'
        elif avg_sentiment < -0.2:
            return 'negative'
        return 'neutral'
    
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
