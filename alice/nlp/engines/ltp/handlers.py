#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 任务处理器
==============

定义各任务类型的处理器，实现插件化任务管理。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Dict

from .models import (
    TaskType,
    Token,
    POSTag,
    DependencyRelation,
    SemanticRole,
    SemanticDependency,
    SemanticDependencyGraph,
)
from alice.nlp.base import Entity, EntityType


class BaseTaskHandler(ABC):
    """任务处理器基类"""
    task_type: TaskType

    @abstractmethod
    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Any:
        """处理 LTP 输出"""
        raise NotImplementedError


class CWSTaskHandler(BaseTaskHandler):
    """分词任务处理器 (CWS)"""
    task_type = TaskType.CWS

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[Token]:
        if not hasattr(ltp_output, 'cws') or not ltp_output.cws:
            # 回退到字符级分词
            return [Token(text[i], i, i, i + 1) for i in range(len(text))]

        words = ltp_output.cws[0] if ltp_output.cws else []
        result_tokens = []
        pos = 0
        for idx, word in enumerate(words):
            start = text.find(word, pos)
            if start == -1:
                start = pos
            end = start + len(word)
            result_tokens.append(Token(word, idx, start, end))
            pos = end
        return result_tokens


class POSTaskHandler(BaseTaskHandler):
    """词性标注处理器 (POS)"""
    task_type = TaskType.POS

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[POSTag]:
        if not hasattr(ltp_output, 'pos') or not ltp_output.pos:
            return [POSTag(token, 'n', 0.0) for token in tokens]

        pos_tags = ltp_output.pos[0] if ltp_output.pos else []
        return [
            POSTag(token, pos_tag, 1.0)
            for token, pos_tag in zip(tokens, pos_tags)
        ]


class NERTaskHandler(BaseTaskHandler):
    """命名实体识别处理器 (NER)"""
    task_type = TaskType.NER

    # LTP NER 标签映射（BIOES 标注方案）
    ENTITY_MAPPING: Dict[str, EntityType] = {
        'Nh': EntityType.PERSON,        # 人名
        'Ni': EntityType.ORGANIZATION,  # 机构名
        'Ns': EntityType.LOCATION,      # 地名
        'nt': EntityType.TIME,          # 时间词
        'nd': EntityType.DATE,          # 日期
        'nz': EntityType.GENERAL,       # 其他专名
    }

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[Entity]:
        if not hasattr(ltp_output, 'ner') or not ltp_output.ner:
            return []

        entities = []
        ner_data = ltp_output.ner[0] if ltp_output.ner else []

        # 处理可能的嵌套结构 [[(text, type), ...]]
        if ner_data and isinstance(ner_data[0], list):
            ner_data = ner_data[0]

        for item in ner_data:
            if not isinstance(item, (tuple, list)) or len(item) < 2:
                continue

            entity_text, entity_type = item[0], item[1]

            # 查找位置
            start_pos = text.find(entity_text)
            if start_pos == -1:
                continue

            entity_type_enum = self.ENTITY_MAPPING.get(
                entity_type, EntityType.GENERAL
            )

            entities.append(Entity(
                text=entity_text,
                entity_type=entity_type_enum,
                start_pos=start_pos,
                end_pos=start_pos + len(entity_text),
                confidence=0.95,
            ))

        return entities


class DEPTaskHandler(BaseTaskHandler):
    """依存句法分析处理器 (DEP)"""
    task_type = TaskType.DEP

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[DependencyRelation]:
        if not hasattr(ltp_output, 'dep') or not ltp_output.dep:
            return []

        dep_data = ltp_output.dep[0] if ltp_output.dep else {}

        # 处理不同版本的格式
        if isinstance(dep_data, dict):
            # 新版本：{'head': [...], 'label': [...]}
            heads = dep_data.get('head', [])
            labels = dep_data.get('label', [])
        elif isinstance(dep_data, list):
            # 旧版本：[(label, head), ...]
            labels = [d[0] if isinstance(d, (list, tuple)) else 'HED'
                     for d in dep_data]
            heads = [d[1] if isinstance(d, (list, tuple)) and len(d) > 1 else -1
                    for d in dep_data]
        else:
            return []

        dependencies = []
        for idx, (token, head, label) in enumerate(zip(tokens, heads, labels)):
            dependencies.append(DependencyRelation(
                token=token,
                head_idx=head if head is not None else -1,
                relation=label if label else 'HED'
            ))

        return dependencies


class SRLTaskHandler(BaseTaskHandler):
    """语义角色标注处理器 (SRL)"""
    task_type = TaskType.SRL

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Optional[List[SemanticRole]]:
        if not hasattr(ltp_output, 'srl') or not ltp_output.srl:
            return None

        srl_data = ltp_output.srl[0] if ltp_output.srl else []
        roles = []

        for predicate_data in srl_data:
            if not isinstance(predicate_data, dict):
                continue

            pred_idx = predicate_data.get('index', -1)
            pred_text = tokens[pred_idx].text if 0 <= pred_idx < len(tokens) else ''

            arguments = []
            for arg in predicate_data.get('arguments', []):
                if isinstance(arg, dict):
                    role_type = arg.get('type', '')
                    arg_text = arg.get('text', '')
                    arg_start = arg.get('start', -1)
                    arg_end = arg.get('end', -1)
                    arguments.append((role_type, arg_text, arg_start, arg_end))

            roles.append(SemanticRole(
                predicate_idx=pred_idx,
                predicate=pred_text,
                arguments=arguments
            ))

        return roles if roles else None


class SDPTaskHandler(BaseTaskHandler):
    """语义依存分析处理器 (SDP)"""
    task_type = TaskType.SDP

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Optional[SemanticDependencyGraph]:
        if not hasattr(ltp_output, 'sdp') or not ltp_output.sdp:
            return None

        sdp_data = ltp_output.sdp[0] if ltp_output.sdp else []
        edges = []

        for dep_idx, heads in enumerate(sdp_data):
            if not isinstance(heads, list):
                continue
            for head_info in heads:
                if isinstance(head_info, (tuple, list)) and len(head_info) >= 2:
                    head_idx, relation = head_info[0], head_info[1]
                    edges.append(SemanticDependency(
                        head_idx=head_idx,
                        dependent_idx=dep_idx,
                        relation=relation
                    ))

        return SemanticDependencyGraph(edges) if edges else None


# 导出所有处理器
__all__ = [
    'BaseTaskHandler',
    'CWSTaskHandler',
    'POSTaskHandler',
    'NERTaskHandler',
    'DEPTaskHandler',
    'SRLTaskHandler',
    'SDPTaskHandler',
]
