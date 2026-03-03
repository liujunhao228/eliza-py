#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 标注集验证器
================

提供标注集完整性校验功能，确保 LTP 输出符合 LTP 4.1.4 文档规范。

验证器类型:
- PosTagValidator: 词性标注验证（27 种 863 标注集）
- DependencyValidator: 依存句法关系验证（14 种标准关系）
- SemanticRoleValidator: 语义角色验证（22 种角色类型）
- SemanticDepValidator: 语义依存关系验证（4 大类）

使用示例:
    >>> from alice.nlp.engines.ltp.validators import PosTagValidator
    >>> from alice.nlp.engines.ltp.models import POSTag, Token
    >>> tokens = [Token('美丽', 0, 0, 2)]
    >>> pos_tags = [POSTag(tokens[0], 'a')]
    >>> invalid = PosTagValidator.validate(pos_tags)
    >>> assert len(invalid) == 0
"""

import logging
from typing import List, Tuple, Optional, Set

from .models import (
    POSTag,
    DependencyRelation,
    SemanticRole,
    SemanticDependency,
    SemanticDependencyGraph,
)

logger = logging.getLogger(__name__)


class PosTagValidator:
    """
    词性标注验证器
    
    验证词性标签是否符合 863 标注集规范（27 种词性）
    参考：LTP 4.1.4 文档 - 词性标注集
    """

    # 完整 863 词性标注集（27 种）
    VALID_POS_TAGS: Set[str] = {
        # 实词 - 体词
        'n', 'nd', 'nh', 'ni', 'nl', 'ns', 'nt', 'nz',
        'v', 'a', 'b', 'm', 'q', 'r',
        # 实词 - 谓词
        'd', 'z',
        # 虚词
        'p', 'c', 'u',
        # 其他
        'e', 'o', 'wp',
        # 语素/词缀
        'h', 'k', 'g',
        # 特殊
        'i', 'j', 'ws', 'x',
    }

    # 词性分类
    POS_CATEGORIES = {
        '体词': {'n', 'nd', 'nh', 'ni', 'nl', 'ns', 'nt', 'nz', 'm', 'q', 'r'},
        '谓词': {'v', 'a', 'd', 'z'},
        '虚词': {'p', 'c', 'u'},
        '其他': {'e', 'o', 'wp'},
        '语素/词缀': {'h', 'k', 'g'},
        '特殊': {'i', 'j', 'ws', 'x'},
    }

    @classmethod
    def validate(cls, pos_tags: List[POSTag]) -> List[Tuple[int, str]]:
        """
        验证词性标注

        Args:
            pos_tags: 词性标注列表

        Returns:
            无效标注列表 [(索引，词性标签), ...]
        """
        invalid = []
        for idx, tag in enumerate(pos_tags):
            if tag.pos not in cls.VALID_POS_TAGS:
                invalid.append((idx, tag.pos))
                logger.warning(f"无效词性标签：{tag.pos} at index {idx} (token: {tag.token.text})")
        return invalid

    @classmethod
    def is_valid(cls, pos: str) -> bool:
        """检查单个词性标签是否有效"""
        return pos in cls.VALID_POS_TAGS

    @classmethod
    def get_category(cls, pos: str) -> str:
        """获取词性所属分类"""
        for category, tags in cls.POS_CATEGORIES.items():
            if pos in tags:
                return category
        return '未知'

    @classmethod
    def get_stats(cls, pos_tags: List[POSTag]) -> dict:
        """获取词性分布统计"""
        stats = {'total': len(pos_tags), 'by_category': {}, 'by_tag': {}}
        for tag in pos_tags:
            category = cls.get_category(tag.pos)
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            stats['by_tag'][tag.pos] = stats['by_tag'].get(tag.pos, 0) + 1
        return stats


class DependencyValidator:
    """
    依存句法关系验证器

    验证依存关系是否符合 LTP 标准（14 种标准关系）
    参考：LTP 4.1.4 文档 - 依存句法关系
    """

    # 14 种标准依存关系 + WP(标点)
    VALID_RELATIONS: Set[str] = {
        'SBV',  # 主谓关系
        'VOB',  # 动宾关系
        'IOB',  # 间宾关系
        'FOB',  # 前置宾语
        'DBL',  # 兼语
        'ATT',  # 定中关系
        'ADV',  # 状中结构
        'CMP',  # 动补结构
        'COO',  # 并列关系
        'POB',  # 介宾关系
        'LAD',  # 左附加关系
        'RAD',  # 右附加关系
        'IS',   # 独立结构
        'HED',  # 核心关系
        'WP',   # 标点符号（扩展）
    }

    # 关系分类
    RELATION_CATEGORIES = {
        '核心关系': {'HED'},
        '主干关系': {'SBV', 'VOB', 'IOB', 'FOB', 'DBL'},
        '修饰关系': {'ATT', 'ADV', 'CMP'},
        '并列关系': {'COO'},
        '介词关系': {'POB'},
        '附加关系': {'LAD', 'RAD'},
        '独立关系': {'IS'},
        '标点': {'WP'},
    }

    @classmethod
    def validate(cls, dependencies: List[DependencyRelation]) -> List[Tuple[int, str]]:
        """
        验证依存关系

        Args:
            dependencies: 依存关系列表

        Returns:
            无效关系列表 [(索引，关系标签), ...]
        """
        invalid = []
        for idx, dep in enumerate(dependencies):
            if dep.relation not in cls.VALID_RELATIONS:
                invalid.append((idx, dep.relation))
                logger.warning(
                    f"无效依存关系：{dep.relation} at index {idx} "
                    f"(token: {dep.token.text}, head: {dep.head_idx})"
                )
        return invalid

    @classmethod
    def is_valid(cls, relation: str) -> bool:
        """检查单个依存关系是否有效"""
        return relation in cls.VALID_RELATIONS

    @classmethod
    def get_category(cls, relation: str) -> str:
        """获取依存关系所属分类"""
        for category, relations in cls.RELATION_CATEGORIES.items():
            if relation in relations:
                return category
        return '未知'


class SemanticRoleValidator:
    """
    语义角色验证器

    验证语义角色是否符合 LTP 标准（22 种角色类型）
    参考：LTP 4.1.4 文档 - 语义角色类型
    """

    # 22 种标准语义角色
    VALID_ROLES: Set[str] = {
        # 核心论元
        'ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4',
        # 附加角色
        'ADV', 'BNF', 'CND', 'CRD', 'DGR', 'DIR', 'DIS',
        'EXT', 'FRQ', 'LOC', 'MNR', 'PRP', 'QTY',
        'TMP', 'TPC',
        # 特殊角色
        'PRD', 'PSR', 'PSE',
    }

    # 角色分类
    ROLE_CATEGORIES = {
        '核心论元': {'ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4'},
        '附加角色': {
            'ADV', 'BNF', 'CND', 'CRD', 'DGR', 'DIR', 'DIS',
            'EXT', 'FRQ', 'LOC', 'MNR', 'PRP', 'QTY', 'TMP', 'TPC',
        },
        '特殊角色': {'PRD', 'PSR', 'PSE'},
    }

    @classmethod
    def validate(
        cls, semantic_roles: Optional[List[SemanticRole]]
    ) -> List[Tuple[int, str, str]]:
        """
        验证语义角色

        Args:
            semantic_roles: 语义角色列表

        Returns:
            无效角色列表 [(谓词索引，论元类型，论元文本), ...]
        """
        if not semantic_roles:
            return []

        invalid = []
        for pred_idx, role in enumerate(semantic_roles):
            for arg_type, arg_text, _, _ in role.arguments:
                if arg_type and arg_type not in cls.VALID_ROLES:
                    invalid.append((pred_idx, arg_type, arg_text))
                    logger.warning(
                        f"无效语义角色：{arg_type} for predicate '{role.predicate}' "
                        f"(arg: {arg_text})"
                    )
        return invalid

    @classmethod
    def is_valid(cls, role: str) -> bool:
        """检查单个语义角色是否有效"""
        return role in cls.VALID_ROLES

    @classmethod
    def get_category(cls, role: str) -> str:
        """获取语义角色所属分类"""
        for category, roles in cls.ROLE_CATEGORIES.items():
            if role in roles:
                return category
        return '未知'


class SemanticDepValidator:
    """
    语义依存关系验证器

    验证语义依存关系是否符合 LTP 标准（4 大类）
    参考：LTP 4.1.4 文档 - 语义依存关系

    支持的关系类型:
    1. 语义周边角色（16 种）: AGT/EXP/PAT/CONT/DATV/LINK/TOOL/MATL/MANN/SCO/REAS/TIME/LOC/MEAS/STAT/FEAT
    2. 语义结构关系：反关系 (r+ 角色)/嵌套关系 (d+ 角色)
    3. 事件关系（3 种）: eCOO/ePREC/eSUCC
    4. 语义依附标记（4 种）: mPUNC/mNEG/mRELA/mDEPD
    """

    # 语义周边角色（16 种）
    CORE_ROLES: Set[str] = {
        'AGT', 'EXP', 'PAT', 'CONT', 'DATV', 'LINK',
        'TOOL', 'MATL', 'MANN', 'SCO', 'REAS', 'TIME',
        'LOC', 'MEAS', 'STAT', 'FEAT',
    }

    # 语义结构关系前缀
    STRUCT_PREFIXES: Set[str] = {'r', 'd'}

    # 事件关系（3 种）
    EVENT_RELATIONS: Set[str] = {'eCOO', 'ePREC', 'eSUCC'}

    # 语义依附标记（4 种）
    DEPENDENCY_MARKERS: Set[str] = {'mPUNC', 'mNEG', 'mRELA', 'mDEPD'}

    # 角色分类
    RELATION_CATEGORIES = {
        '语义周边角色': CORE_ROLES,
        '事件关系': EVENT_RELATIONS,
        '语义依附标记': DEPENDENCY_MARKERS,
        '反关系': set(),  # 动态生成
        '嵌套关系': set(),  # 动态生成
    }

    @classmethod
    def validate_relation(cls, relation: str) -> bool:
        """
        验证单个语义依存关系

        Args:
            relation: 关系标签

        Returns:
            是否有效
        """
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

    @classmethod
    def validate(
        cls, edges: List[SemanticDependency]
    ) -> List[Tuple[int, str]]:
        """
        验证语义依存边

        Args:
            edges: 语义依存边列表

        Returns:
            无效关系列表 [(边索引，关系标签), ...]
        """
        invalid = []
        for idx, edge in enumerate(edges):
            if not cls.validate_relation(edge.relation):
                invalid.append((idx, edge.relation))
                logger.warning(
                    f"无效语义依存关系：{edge.relation} "
                    f"(head: {edge.head_idx}, dep: {edge.dependent_idx})"
                )
        return invalid

    @classmethod
    def get_category(cls, relation: str) -> str:
        """获取语义依存关系所属分类"""
        if relation in cls.CORE_ROLES:
            return '语义周边角色'
        elif relation in cls.EVENT_RELATIONS:
            return '事件关系'
        elif relation in cls.DEPENDENCY_MARKERS:
            return '语义依附标记'
        elif len(relation) > 1 and relation[0] in cls.STRUCT_PREFIXES:
            if relation[0] == 'r':
                return '反关系'
            else:
                return '嵌套关系'
        return '未知'

    @classmethod
    def get_relation_type(cls, relation: str) -> dict:
        """
        获取关系类型详情

        Args:
            relation: 关系标签

        Returns:
            {'category': str, 'base_role': str, 'is_structural': bool}
        """
        result = {
            'category': cls.get_category(relation),
            'base_role': relation,
            'is_structural': False,
        }

        if len(relation) > 1 and relation[0] in cls.STRUCT_PREFIXES:
            result['is_structural'] = True
            result['prefix'] = relation[0]
            result['base_role'] = relation[1:]

        return result


# 导出所有验证器
__all__ = [
    'PosTagValidator',
    'DependencyValidator',
    'SemanticRoleValidator',
    'SemanticDepValidator',
]
