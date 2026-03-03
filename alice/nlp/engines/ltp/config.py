#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎配置
============

定义 LTP 引擎的配置类和标注集常量。

配置说明:
- 任务启用开关默认值来自 alice.config 模块，支持统一配置管理
- 可在实例化时通过参数覆盖默认值

标注集常量:
- NER_ENTITY_MAPPING: NER 标签映射（Nh/Ni/Ns）
- POS_TAG_SET: 完整词性标注集（27 种 863 标注集）
- SEMANTIC_ROLE_SET: 完整语义角色集（22 种）
- DEPENDENCY_RELATION_SET: 依存关系集（14 种）
- SEMANTIC_DEP_CORE_ROLES: 语义依存核心角色（16 种）
- SEMANTIC_DEP_EVENT_RELATIONS: 事件关系（3 种）
- SEMANTIC_DEP_MARKERS: 语义依附标记（4 种）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, Dict

# 从主配置模块导入默认值
from ....config import (
    LTP_ENABLE_CWS,
    LTP_ENABLE_POS,
    LTP_ENABLE_NER,
    LTP_ENABLE_DEP,
    LTP_ENABLE_SDP,
    LTP_ENABLE_SRL,
)


# =============================================================================
# LTP 标注集常量（参考 LTP 4.1.4 文档）
# =============================================================================

# NER 标签映射（3 种核心实体 + 扩展）
NER_ENTITY_MAPPING: Dict[str, str] = {
    'Nh': 'PERSON',        # 人名
    'Ni': 'ORGANIZATION',  # 机构名
    'Ns': 'LOCATION',      # 地名
    'nt': 'TIME',          # 时间词
    'nd': 'DATE',          # 日期
    'nz': 'GENERAL',       # 其他专名
}

# 完整词性标注集（863 标注集，27 种）
POS_TAG_SET: Set[str] = {
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

# 完整语义角色集（22 种）
SEMANTIC_ROLE_SET: Set[str] = {
    # 核心论元
    'ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4',
    # 附加角色
    'ADV', 'BNF', 'CND', 'CRD', 'DGR', 'DIR', 'DIS',
    'EXT', 'FRQ', 'LOC', 'MNR', 'PRP', 'QTY',
    'TMP', 'TPC',
    # 特殊角色
    'PRD', 'PSR', 'PSE',
}

# 依存关系集（14 种标准关系）
DEPENDENCY_RELATION_SET: Set[str] = {
    'SBV', 'VOB', 'IOB', 'FOB', 'DBL',
    'ATT', 'ADV', 'CMP', 'COO', 'POB',
    'LAD', 'RAD', 'IS', 'HED',
}

# 语义依存核心角色（16 种）
SEMANTIC_DEP_CORE_ROLES: Set[str] = {
    'AGT', 'EXP', 'PAT', 'CONT', 'DATV', 'LINK',
    'TOOL', 'MATL', 'MANN', 'SCO', 'REAS', 'TIME',
    'LOC', 'MEAS', 'STAT', 'FEAT',
}

# 语义依存事件关系（3 种）
SEMANTIC_DEP_EVENT_RELATIONS: Set[str] = {
    'eCOO', 'ePREC', 'eSUCC',
}

# 语义依存依附标记（4 种）
SEMANTIC_DEP_MARKERS: Set[str] = {
    'mPUNC', 'mNEG', 'mRELA', 'mDEPD',
}

# 语义依存结构前缀（反关系/嵌套关系）
SEMANTIC_DEP_STRUCT_PREFIXES: Set[str] = {'r', 'd'}


@dataclass
class LtpConfig:
    """LTP 引擎配置"""
    model_path: Optional[str] = None
    device: Optional[str] = None      # 'cpu', 'cuda', 'cuda:0' 等
    batch_size: int = 32
    max_length: int = 512
    cache_dir: Optional[str] = None

    # 任务启用开关（默认值来自 alice.config）
    enable_cws: bool = LTP_ENABLE_CWS
    enable_pos: bool = LTP_ENABLE_POS
    enable_ner: bool = LTP_ENABLE_NER
    enable_dep: bool = LTP_ENABLE_DEP
    enable_sdp: bool = LTP_ENABLE_SDP          # 语义依存分析，默认关闭
    enable_srl: bool = LTP_ENABLE_SRL          # 语义角色标注，默认关闭

    # 验证器开关
    enable_validation: bool = True             # 是否启用标注集验证
    validation_strict: bool = False            # 严格模式（验证失败时抛出异常）

    def get_enabled_tasks(self) -> List[str]:
        """获取启用的任务列表"""
        tasks = []
        if self.enable_cws:
            tasks.append('cws')
        if self.enable_pos:
            tasks.append('pos')
        if self.enable_ner:
            tasks.append('ner')
        if self.enable_dep:
            tasks.append('dep')
        if self.enable_sdp:
            tasks.append('sdp')
        if self.enable_srl:
            tasks.append('srl')
        return tasks

    def is_valid_pos(self, pos: str) -> bool:
        """检查词性标签是否有效"""
        return pos in POS_TAG_SET

    def is_valid_semantic_role(self, role: str) -> bool:
        """检查语义角色是否有效"""
        return role in SEMANTIC_ROLE_SET

    def is_valid_dependency(self, relation: str) -> bool:
        """检查依存关系是否有效"""
        return relation in DEPENDENCY_RELATION_SET

    def is_valid_semantic_dep(self, relation: str) -> bool:
        """检查语义依存关系是否有效"""
        if relation in SEMANTIC_DEP_CORE_ROLES:
            return True
        if relation in SEMANTIC_DEP_EVENT_RELATIONS:
            return True
        if relation in SEMANTIC_DEP_MARKERS:
            return True
        # 反关系/嵌套关系
        if len(relation) > 1 and relation[0] in SEMANTIC_DEP_STRUCT_PREFIXES:
            return relation[1:] in SEMANTIC_DEP_CORE_ROLES
        return False


__all__ = [
    'LtpConfig',
    # 标注集常量
    'NER_ENTITY_MAPPING',
    'POS_TAG_SET',
    'SEMANTIC_ROLE_SET',
    'DEPENDENCY_RELATION_SET',
    'SEMANTIC_DEP_CORE_ROLES',
    'SEMANTIC_DEP_EVENT_RELATIONS',
    'SEMANTIC_DEP_MARKERS',
]
