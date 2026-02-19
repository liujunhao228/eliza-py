#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP 基础模块 - 定义统一接口和数据类
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """实体类型枚举"""
    # 人称代词
    PRONOUN = "pronoun"
    # 人名
    PERSON = "person"
    # 称谓/关系
    TITLE = "title"
    # 地名
    LOCATION = "location"
    # 机构
    ORGANIZATION = "organization"
    # 时间
    TIME = "time"
    # 日期
    DATE = "date"
    # 数字/数量
    NUMBER = "number"
    # 情感
    EMOTION = "emotion"
    # 通用
    GENERAL = "general"


@dataclass
class Entity:
    """命名实体数据类"""
    text: str
    entity_type: EntityType
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)

    def to_tuple(self) -> Tuple[str, str]:
        """转换为 (类型，文本) 元组"""
        return (self.entity_type.value, self.text)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'text': self.text,
            'type': self.entity_type.value,
            'start': self.start_pos,
            'end': self.end_pos,
            'confidence': self.confidence,
        }


@dataclass
class SyntaxStructure:
    """句法结构数据类"""
    words: List[str] = field(default_factory=list)
    poses: List[str] = field(default_factory=list)
    subject: str = ""
    predicate: str = ""
    object: str = ""
    modifiers: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'words': self.words,
            'poses': self.poses,
            'subject': self.subject,
            'predicate': self.predicate,
            'object': self.object,
            'modifiers': self.modifiers,
        }


@dataclass
class NlpResult:
    """NLP 分析结果"""
    text: str
    tokens: List[str] = field(default_factory=list)
    sentiment: float = 0.0
    intent: str = "general"
    entities: List[Entity] = field(default_factory=list)
    syntax: Optional[SyntaxStructure] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'text': self.text,
            'tokens': self.tokens,
            'sentiment': self.sentiment,
            'intent': self.intent,
            'entities': [e.to_dict() for e in self.entities],
            'syntax': self.syntax.to_dict() if self.syntax else None,
        }


class NlpEngine(ABC):
    """
    NLP 引擎基类

    定义统一的 NLP 处理接口
    """

    @abstractmethod
    def analyze(self, text: str) -> NlpResult:
        """
        分析文本

        Args:
            text: 待分析文本

        Returns:
            NLP 分析结果
        """
        pass

    @abstractmethod
    def extract_entities(self, text: str) -> List[Entity]:
        """
        提取实体

        Args:
            text: 待分析文本

        Returns:
            实体列表
        """
        pass

    @abstractmethod
    def get_syntax(self, text: str) -> Optional[SyntaxStructure]:
        """
        获取句法结构

        Args:
            text: 待分析文本

        Returns:
            句法结构，无法分析时返回 None
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass
