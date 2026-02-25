#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理器模块

负责对话上下文的管理，包括：
- 对话历史追踪
- 实体记忆
- 话题追踪
- 上下文智能更新
- 用户画像管理
- 时间感知上下文
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
    turn_number: int = 0  # 对话轮数


@dataclass
class UserProfile:
    """
    用户画像
    
    Attributes:
        name: 用户姓名
        nickname: 用户昵称
        address_form: 称呼偏好（如"你"、"您"）
        created_at: 画像创建时间
        updated_at: 画像更新时间
        metadata: 其他元数据
    """
    name: Optional[str] = None
    nickname: Optional[str] = None
    address_form: str = "你"  # 默认使用"你"，可选"您"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    上下文管理器

    功能:
    - 管理对话历史（限制长度）
    - 追踪实体和话题
    - 提供上下文感知的对话支持
    - 智能上下文更新
    - 用户画像管理
    - 时间感知上下文
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

        # 用户画像
        self._user_profile: Optional[UserProfile] = None

        # 时间感知上下文
        self._session_start_time: datetime = datetime.now()
        self._last_interaction_time: datetime = datetime.now()
        self._turn_count: int = 0

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
        # 更新对话轮数
        self._turn_count += 1

        # 创建对话轮次
        turn = ConversationTurn(
            user_input=user_input,
            bot_response=bot_response,
            entities=entities or [],
            intent=intent,
            turn_number=self._turn_count,
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

        # 更新最后交互时间
        self._last_interaction_time = datetime.now()

        logger.debug(f"上下文已更新：第 {self._turn_count} 轮对话")

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

    # =========================================================================
    # 用户画像管理
    # =========================================================================

    def set_user_profile(
        self,
        name: Optional[str] = None,
        nickname: Optional[str] = None,
        address_form: str = "你",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        设置用户画像

        Args:
            name: 用户姓名
            nickname: 用户昵称
            address_form: 称呼偏好（"你"或"您"）
            metadata: 其他元数据
        """
        if self._user_profile is None:
            self._user_profile = UserProfile()

        if name is not None:
            self._user_profile.name = name
        if nickname is not None:
            self._user_profile.nickname = nickname
        if address_form in ["你", "您"]:
            self._user_profile.address_form = address_form
        if metadata:
            self._user_profile.metadata.update(metadata)

        self._user_profile.updated_at = datetime.now()
        logger.info(f"用户画像已更新：{self._user_profile.name or '未命名'}")

    def get_user_profile(self) -> Optional[UserProfile]:
        """
        获取用户画像

        Returns:
            用户画像对象，如果未设置则返回 None
        """
        return self._user_profile

    def get_user_name(self) -> Optional[str]:
        """
        获取用户姓名

        Returns:
            用户姓名，如果未设置则返回 None
        """
        return self._user_profile.name if self._user_profile else None

    def get_user_nickname(self) -> Optional[str]:
        """
        获取用户昵称

        Returns:
            用户昵称，如果未设置则返回 None
        """
        return self._user_profile.nickname if self._user_profile else None

    def get_address_form(self) -> str:
        """
        获取称呼偏好

        Returns:
            称呼偏好（"你"或"您"）
        """
        return self._user_profile.address_form if self._user_profile else "你"

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        设置用户偏好

        Args:
            key: 偏好键
            value: 偏好值
        """
        self._user_preferences[key] = value
        logger.debug(f"用户偏好已设置：{key}={value}")

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """
        获取用户偏好

        Args:
            key: 偏好键
            default: 默认值

        Returns:
            偏好值，如果不存在则返回默认值
        """
        return self._user_preferences.get(key, default)

    # =========================================================================
    # 时间感知上下文
    # =========================================================================

    def get_session_start_time(self) -> datetime:
        """
        获取会话开始时间

        Returns:
            会话开始时间
        """
        return self._session_start_time

    def get_last_interaction_time(self) -> datetime:
        """
        获取最后交互时间

        Returns:
            最后交互时间
        """
        return self._last_interaction_time

    def get_turn_count(self) -> int:
        """
        获取对话轮数

        Returns:
            对话轮数
        """
        return self._turn_count

    def get_session_duration(self) -> float:
        """
        获取会话持续时间（秒）

        Returns:
            会话持续时间（秒）
        """
        return (datetime.now() - self._session_start_time).total_seconds()

    def get_idle_duration(self) -> float:
        """
        获取空闲时长（秒）

        Returns:
            距离上次交互的时长（秒）
        """
        return (datetime.now() - self._last_interaction_time).total_seconds()

    def get_time_context(self) -> Dict[str, Any]:
        """
        获取时间上下文

        Returns:
            时间上下文字典，包含：
            - year: 年份
            - month: 月份
            - day: 日期
            - weekday: 星期（0-6，0=周一）
            - weekday_name: 星期名称（如"星期一"）
            - hour: 小时
            - minute: 分钟
            - second: 秒
            - category_time: 时间段（早晨/中午/下午/晚上/深夜）
            - session_start: 会话开始时间
            - last_interaction: 最后交互时间
            - turn_count: 对话轮数
        """
        now = datetime.now()
        return {
            # 日期信息
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.weekday(),  # 0=周一，6=周日
            "weekday_name": self._get_weekday_name(now.weekday()),
            # 时间信息
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "category_time": self._get_time_of_day(now.hour),
            # 会话信息
            "session_start": self._session_start_time.isoformat(),
            "last_interaction": self._last_interaction_time.isoformat(),
            "turn_count": self._turn_count,
            "session_duration_seconds": self.get_session_duration(),
            "idle_duration_seconds": self.get_idle_duration(),
        }

    def _get_weekday_name(self, weekday: int) -> str:
        """
        根据星期数字获取星期名称

        Args:
            weekday: 星期数字（0-6，0=周一）

        Returns:
            星期名称字符串
        """
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekday_names[weekday]

    def _get_time_of_day(self, hour: int) -> str:
        """
        根据小时获取时间段

        Args:
            hour: 小时（0-23）

        Returns:
            时间段描述
        """
        if 5 <= hour < 12:
            return "早晨"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 18:
            return "下午"
        elif 18 <= hour < 22:
            return "晚上"
        else:
            return "深夜"

    def get_formatted_time_variables(self) -> Dict[str, Any]:
        """
        获取格式化后的时间变量字典

        支持的变量（不区分大小写）:
        - {year}: 年份（如 2026）
        - {month}: 月份（1-12）
        - {day}: 日期（1-31）
        - {weekday}: 星期数字（0-6，0=周一）
        - {weekday_name}: 星期名称（如"星期五"）
        - {hour}: 小时（0-23）
        - {minute}: 分钟（0-59）
        - {second}: 秒（0-59）
        - {category_time}: 时间段（早晨/中午/下午/晚上/深夜）

        Returns:
            时间变量字典，包含所有支持的变量
        """
        time_ctx = self.get_time_context()
        return {
            "year": time_ctx["year"],
            "month": time_ctx["month"],
            "day": time_ctx["day"],
            "weekday": time_ctx["weekday"],
            "weekday_name": time_ctx["weekday_name"],
            "hour": time_ctx["hour"],
            "minute": time_ctx["minute"],
            "second": time_ctx["second"],
            "category_time": time_ctx["category_time"],
        }

    def get_context_summary(self) -> Dict[str, Any]:
        """
        获取上下文摘要

        Returns:
            上下文摘要字典
        """
        summary = {
            "total_turns": len(self._history),
            "recent_turns": len(self._short_term),
            "current_topic": self._current_topic,
            "total_entities": sum(len(e) for e in self._entities.values()),
            "recent_entities": self.get_recent_entities(3),
            "topics": list(self._topics.keys()),
        }

        # 添加用户画像信息
        if self._user_profile:
            summary["user_profile"] = {
                "name": self._user_profile.name,
                "nickname": self._user_profile.nickname,
                "address_form": self._user_profile.address_form,
            }
        else:
            summary["user_profile"] = None

        # 添加时间上下文
        summary["time_context"] = self.get_time_context()

        return summary

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
        self._user_profile = None
        self._session_start_time = datetime.now()
        self._last_interaction_time = datetime.now()
        self._turn_count = 0

        logger.info("上下文已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_turns": len(self._history),
            "short_term_size": len(self._short_term),
            "total_entities": sum(len(e) for e in self._entities.values()),
            "total_topics": len(self._topics),
            "current_topic": self._current_topic,
            "turn_count": self._turn_count,
            "session_duration_seconds": self.get_session_duration(),
            "user_profile_set": self._user_profile is not None,
        }
