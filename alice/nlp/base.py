#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP 基础模块 - 定义统一接口和数据类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class EntityType(Enum):
    """实体类型"""
    PERSON = "person"
    LOCATION = "location"
    ORGANIZATION = "organization"
    TIME = "time"
    DATE = "date"
    PRONOUN = "pronoun"
    TITLE = "title"
    NUMBER = "number"
    EMOTION = "emotion"
    GENERAL = "general"


@dataclass
class Entity:
    """命名实体"""
    text: str
    entity_type: EntityType
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 1.0


@dataclass
class SyntaxStructure:
    """句法结构"""
    words: List[str] = field(default_factory=list)
    poses: List[str] = field(default_factory=list)
    subject: str = ""
    predicate: str = ""
    object: str = ""
    modifiers: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class NlpResult:
    """NLP 分析结果"""
    text: str
    tokens: List[str] = field(default_factory=list)
    sentiment: float = 0.0
    entities: List[Entity] = field(default_factory=list)
    syntax: Optional[SyntaxStructure] = None


class Segmenter(ABC):
    """分词器接口 - 只负责分词"""
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def segment(self, text: str) -> List[str]:
        pass


class SyntaxAnalyzer(ABC):
    """句法分析器接口"""
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def analyze(self, text: str) -> NlpResult:
        """完整分析（分词 + 词性 + 句法 + 实体）"""
        pass


class EntityRecognizer(ABC):
    """实体识别器接口"""
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def recognize(self, text: str) -> List[Entity]:
        pass


class SentimentAnalyzer(ABC):
    """情感分析器接口"""
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def analyze(self, text: str) -> float:
        """返回情感分数 (-1.0 到 1.0)"""
        pass
