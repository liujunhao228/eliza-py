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

    # 完整 863 词性标注集（27 种）
    # 参考：LTP 4.1.4 文档 - 词性标注集
    POS_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        # 实词 - 体词
        'n': '名词', 'nd': '方位名词', 'nh': '人名', 'ni': '机构名',
        'nl': '处所名词', 'ns': '地名', 'nt': '时间词', 'nz': '其他专名',
        'v': '动词', 'a': '形容词', 'b': '其他名词修饰语',
        'm': '数词', 'q': '量词', 'r': '代词',
        # 实词 - 谓词
        'd': '副词', 'z': '状态词',
        # 虚词
        'p': '介词', 'c': '连词', 'u': '助词',
        # 其他
        'e': '叹词', 'o': '拟声词', 'wp': '标点符号',
        # 语素/词缀
        'h': '前缀', 'k': '后缀', 'g': '语素',
        # 特殊
        'i': '成语', 'j': '简称', 'ws': '外来词', 'x': '非语素字',
    })

    @property
    def description(self) -> str:
        return self.POS_DESCRIPTIONS.get(self.pos, '未知')

    @classmethod
    def is_valid_pos(cls, pos: str) -> bool:
        """检查词性标签是否有效"""
        from .config import POS_TAG_SET
        return pos in POS_TAG_SET


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

    # 完整语义角色类型（22 种）
    # 参考：LTP 4.1.4 文档 - 语义角色类型
    ROLE_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        # 核心论元
        'ARG0': '施事（动作发出者）',
        'ARG1': '受事（动作承受者）',
        'ARG2': '与事/范围',
        'ARG3': '起点/受益人',
        'ARG4': '终点',
        # 附加角色
        'ADV': '状语',
        'BNF': '受益人',
        'CND': '条件',
        'CRD': '并列',
        'DGR': '程度',
        'DIR': '方向',
        'DIS': '话语标记',
        'EXT': '范围',
        'FRQ': '频率',
        'LOC': '地点',
        'MNR': '方式',
        'PRP': '目的',
        'QTY': '数量',
        'TMP': '时间',
        'TPC': '话题',
        # 特殊角色
        'PRD': '谓语',
        'PSR': '持有者',
        'PSE': '被持有',
    })

    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        """检查语义角色是否有效"""
        from .config import SEMANTIC_ROLE_SET
        return role in SEMANTIC_ROLE_SET


@dataclass
class SemanticDependency:
    """语义依存关系（SDP）"""
    head_idx: int
    dependent_idx: int
    relation: str

    # 完整语义依存关系标注集
    # 参考：LTP 4.1.4 文档 - 语义依存关系
    
    # 语义周边角色（16 种）
    CORE_ROLES: set = field(default_factory=lambda: {
        'AGT', 'EXP', 'PAT', 'CONT', 'DATV', 'LINK',
        'TOOL', 'MATL', 'MANN', 'SCO', 'REAS', 'TIME',
        'LOC', 'MEAS', 'STAT', 'FEAT',
    })

    # 语义结构关系前缀
    STRUCT_PREFIXES: set = field(default_factory=lambda: {'r', 'd'})  # 反关系/嵌套关系

    # 事件关系（3 种）
    EVENT_RELATIONS: set = field(default_factory=lambda: {'eCOO', 'ePREC', 'eSUCC'})

    # 语义依附标记（4 种）
    DEPENDENCY_MARKERS: set = field(default_factory=lambda: {'mPUNC', 'mNEG', 'mRELA', 'mDEPD'})

    # 完整有效关系集合
    VALID_RELATIONS: set = field(default_factory=lambda: {
        # 核心角色
        'AGT', 'EXP', 'PAT', 'CONT', 'DATV', 'LINK',
        'TOOL', 'MATL', 'MANN', 'SCO', 'REAS', 'TIME',
        'LOC', 'MEAS', 'STAT', 'FEAT',
        # 事件关系
        'eCOO', 'ePREC', 'eSUCC',
        # 依附标记
        'mPUNC', 'mNEG', 'mRELA', 'mDEPD',
    })

    @property
    def relation_type(self) -> str:
        """获取关系类型分类"""
        if self.relation in self.CORE_ROLES:
            return '核心角色'
        elif self.relation in self.EVENT_RELATIONS:
            return '事件关系'
        elif self.relation in self.DEPENDENCY_MARKERS:
            return '依附标记'
        elif len(self.relation) > 1 and self.relation[0] in self.STRUCT_PREFIXES:
            if self.relation[0] == 'r':
                return '反关系'
            else:
                return '嵌套关系'
        return '未知'

    @property
    def description(self) -> str:
        """获取关系描述"""
        descriptions = {
            'AGT': '施事', 'EXP': '当事', 'PAT': '受事', 'CONT': '客事',
            'DATV': '涉事', 'LINK': '系事', 'TOOL': '工具', 'MATL': '材料',
            'MANN': '方式', 'SCO': '范围', 'REAS': '缘由', 'TIME': '时间',
            'LOC': '空间', 'MEAS': '度量', 'STAT': '状态', 'FEAT': '修饰',
            'eCOO': '并列关系', 'ePREC': '先行关系', 'eSUCC': '后继关系',
            'mPUNC': '标点标记', 'mNEG': '否定标记', 'mRELA': '关系标记', 'mDEPD': '依附标记',
        }
        base = descriptions.get(self.relation, self.relation)
        if len(self.relation) > 1 and self.relation[0] == 'r':
            return f'反{descriptions.get(self.relation[1:], self.relation[1:])}'
        elif len(self.relation) > 1 and self.relation[0] == 'd':
            return f'嵌套{descriptions.get(self.relation[1:], self.relation[1:])}'
        return base

    @classmethod
    def is_valid_relation(cls, relation: str) -> bool:
        """验证语义依存关系是否有效"""
        # 核心角色
        if relation in cls.CORE_ROLES:
            return True
        # 事件关系
        if relation in cls.EVENT_RELATIONS:
            return True
        # 依附标记
        if relation in cls.DEPENDENCY_MARKERS:
            return True
        # 反关系/嵌套关系 (rEXP, dCONT 等)
        if len(relation) > 1 and relation[0] in cls.STRUCT_PREFIXES:
            return relation[1:] in cls.CORE_ROLES
        return False


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
