#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎数据模型
================

定义 LTP 分析使用的数据模型和枚举类型。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Tuple, Any

from alice.nlp.base import Entity


class TaskType(Enum):
    """LTP 支持的任务类型"""
    CWS = auto()      # 中文分词
    POS = auto()      # 词性标注
    NER = auto()      # 命名实体识别
    DEP = auto()      # 依存句法分析
    SDP = auto()      # 语义依存分析（需单独开启）
    SRL = auto()      # 语义角色标注（需单独开启）


@dataclass(frozen=True)
class Token:
    """分词单元"""
    text: str
    idx: int
    start_pos: int
    end_pos: int

    def __repr__(self) -> str:
        return f"Token({self.text!r}, pos={self.start_pos}-{self.end_pos})"


@dataclass
class POSTag:
    """词性标注结果"""
    token: Token
    pos: str          # 词性标签
    probability: float = 1.0

    # 常见词性对照表（PKU 标注集）
    POS_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        'n': '名词', 'v': '动词', 'a': '形容词', 'd': '副词',
        'm': '数词', 'q': '量词', 'r': '代词', 'p': '介词',
        'c': '连词', 'u': '助词', 'e': '叹词', 'y': '语气词',
        'o': '拟声词', 'h': '前缀', 'k': '后缀', 'x': '字符串',
        'w': '标点符号',
        # 命名实体标签
        'nh': '人名', 'ni': '机构名', 'ns': '地名',
        'nt': '时间词', 'nz': '其他专名',
    })

    @property
    def description(self) -> str:
        return self.POS_DESCRIPTIONS.get(self.pos, '未知')


@dataclass
class DependencyRelation:
    """依存句法关系"""
    token: Token
    head_idx: int     # 依存头部索引 (-1 表示根节点)
    relation: str     # 依存关系类型

    # LTP 依存关系标注集（共 14 种）
    RELATION_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        'SBV': '主谓关系',      # Subject-Verb
        'VOB': '动宾关系',      # Verb-Object
        'IOB': '间宾关系',      # Indirect-Object
        'FOB': '前置宾语',      # Fronting-Object
        'DBL': '兼语',          # Double
        'ATT': '定中关系',      # Attribute
        'ADV': '状中结构',      # Adverbial
        'CMP': '动补结构',      # Complement
        'COO': '并列关系',      # Coordinate
        'POB': '介宾关系',      # Preposition-Object
        'LAD': '左附加关系',    # Left Adjunct
        'RAD': '右附加关系',    # Right Adjunct
        'IS': '独立结构',       # Independent Structure
        'HED': '核心关系',      # Head
        'WP': '标点符号',       # Punctuation
    })

    @property
    def is_root(self) -> bool:
        return self.head_idx == -1 or self.relation == 'HED'

    @property
    def description(self) -> str:
        return self.RELATION_DESCRIPTIONS.get(self.relation, self.relation)


@dataclass
class SemanticRole:
    """语义角色标注结果（SRL）"""
    predicate_idx: int
    predicate: str
    arguments: List[Tuple[str, str, int, int]]  # (role_type, text, start, end)

    # 语义角色类型（基于 PropBank 标准）
    ROLE_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        'A0': '施事（动作发出者）',
        'A1': '受事（动作承受者）',
        'A2': '起点/终点/受益人',
        'A3': '起点/受益人',
        'A4': '终点',
        'A5': '工具/方式',
        'ADV': '附加语（状语）',
        'TMP': '时间',
        'LOC': '地点',
        'MNR': '方式',
        'PRP': '目的',
        'CAU': '原因',
        'EXT': '范围',
        'DIR': '方向',
    })


@dataclass
class SemanticDependency:
    """语义依存关系（SDP）"""
    head_idx: int
    dependent_idx: int
    relation: str


@dataclass
class SemanticDependencyGraph:
    """语义依存图（SDP）"""
    edges: List[SemanticDependency]

    def get_heads(self, idx: int) -> List[int]:
        """获取一个词的所有语义父节点"""
        return [e.head_idx for e in self.edges if e.dependent_idx == idx]

    def get_dependents(self, idx: int) -> List[int]:
        """获取一个词的所有语义子节点"""
        return [e.dependent_idx for e in self.edges if e.head_idx == idx]


@dataclass
class LtpFullResult:
    """LTP 完整分析结果"""
    text: str
    tokens: List[Token] = field(default_factory=list)
    pos_tags: List[POSTag] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    dependencies: List[DependencyRelation] = field(default_factory=list)
    semantic_roles: Optional[List[SemanticRole]] = None
    semantic_deps: Optional[SemanticDependencyGraph] = None
    raw_output: Optional[Any] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'text': self.text,
            'tokens': [{'text': t.text, 'pos': t.start_pos} for t in self.tokens],
            'pos_tags': [{'word': p.token.text, 'pos': p.pos, 'desc': p.description}
                        for p in self.pos_tags],
            'entities': [{'text': e.text, 'type': e.entity_type.name,
                         'confidence': e.confidence} for e in self.entities],
            'dependencies': [{'word': d.token.text, 'relation': d.relation,
                            'head': d.head_idx, 'desc': d.description}
                           for d in self.dependencies],
            'semantic_roles': [
                {
                    'predicate': r.predicate,
                    'arguments': [
                        {'type': arg[0], 'text': arg[1], 'desc': SemanticRole.ROLE_DESCRIPTIONS.get(arg[0], arg[0])}
                        for arg in r.arguments
                    ]
                }
                for r in (self.semantic_roles or [])
            ] if self.semantic_roles else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def get_main_predicate(self) -> Optional[str]:
        """获取句子核心谓语"""
        for dep in self.dependencies:
            if dep.relation == 'HED' and dep.token.pos in ['v', 'a']:
                return dep.token.text
        return None

    def get_subjects(self) -> List[str]:
        """获取所有主语"""
        return [dep.token.text for dep in self.dependencies if dep.relation == 'SBV']

    def get_objects(self) -> List[str]:
        """获取所有宾语"""
        return [dep.token.text for dep in self.dependencies if dep.relation == 'VOB']


__all__ = [
    'TaskType',
    'Token',
    'POSTag',
    'DependencyRelation',
    'SemanticRole',
    'SemanticDependency',
    'SemanticDependencyGraph',
    'LtpFullResult',
]
