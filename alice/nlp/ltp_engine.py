#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎模块 - 依存句法分析

基于 LTP (Language Technology Platform) 进行中文依存句法分析
支持懒加载和降级处理
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from alice.nlp.base import SyntaxStructure, NlpEngine

logger = logging.getLogger(__name__)

# 尝试导入 LTP
try:
    from ltp import LTP
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False
    logger.info("未安装 LTP，LTP 引擎不可用（可安装 ltp>=4.2.10 启用）")


@dataclass
class DependencyWord:
    """依存词单元"""
    word: str
    pos: str
    dep: str
    head: int
    index: int


class LtpEngine(NlpEngine):
    """
    LTP 依存句法分析引擎

    特性:
    - 懒加载：只在需要时加载模型
    - 智能降级：LTP 不可用时自动降级
    - 按需分析：简单句子跳过 LTP 分析
    """

    def __init__(self, model_path: Optional[str] = None, lazy_load: bool = True):
        """
        初始化 LTP 引擎

        Args:
            model_path: LTP 模型路径，None 则使用默认
            lazy_load: 是否懒加载
        """
        self._model_path = model_path
        self._lazy_load = lazy_load
        self._ltp: Optional[LTP] = None
        self._initialized = False

        if not lazy_load:
            self._initialize()

    def _initialize(self) -> bool:
        """初始化 LTP 模型"""
        if self._initialized:
            return True

        if not LTP_AVAILABLE:
            logger.warning("LTP 库未安装，无法初始化")
            return False

        try:
            if self._model_path:
                self._ltp = LTP(self._model_path)
            else:
                self._ltp = LTP()
            self._initialized = True
            logger.info("LTP 模型加载成功")
            return True
        except Exception as e:
            logger.error(f"LTP 模型加载失败：{e}")
            self._ltp = None
            return False

    @property
    def is_available(self) -> bool:
        """检查 LTP 是否可用"""
        if not LTP_AVAILABLE:
            return False
        if self._lazy_load and not self._initialized:
            return True  # 懒加载模式下，认为可用
        return self._ltp is not None

    def _ensure_initialized(self) -> bool:
        """确保 LTP 已初始化"""
        if self._initialized:
            return self._ltp is not None
        return self._initialize()

    def _should_use_ltp(self, text: str) -> bool:
        """
        智能判断是否需要使用 LTP

        简单句子（<6 字，无标点）跳过 LTP 分析
        """
        text = text.strip()
        if len(text) < 6:
            return False
        if not any(c in text for c in '，。！？、；：'):
            return False
        return True

    def analyze(self, text: str) -> 'NlpResult':
        """分析文本（完整 NLP 分析）"""
        from alice.nlp.base import NlpResult, Entity

        # 降级处理
        if not self.is_available or not self._should_use_ltp(text):
            return self._simple_analyze(text)

        # 确保 LTP 已初始化
        if not self._ensure_initialized():
            return self._simple_analyze(text)

        try:
            # LTP 分析
            result = self._ltp.pipeline([text], tasks=['seg', 'pos', 'parser', 'ner'])
            seg, pos, parser, ner = result

            # 构建句法结构
            syntax = self._build_syntax(seg[0], pos[0], parser[0])

            # 提取实体
            entities = self._extract_entities_from_ner(ner[0], text)

            return NlpResult(
                text=text,
                tokens=seg[0],
                syntax=syntax,
                entities=entities,
            )

        except Exception as e:
            logger.warning(f"LTP 分析失败，降级处理：{e}")
            return self._simple_analyze(text)

    def _simple_analyze(self, text: str) -> 'NlpResult':
        """简化分析（降级方案）"""
        from alice.nlp.base import NlpResult

        # 简单分词（按字符）
        tokens = list(text)

        return NlpResult(
            text=text,
            tokens=tokens,
            syntax=SyntaxStructure(words=tokens),
        )

    def _build_syntax(
        self,
        seg: List[str],
        pos: List[str],
        parser: List[tuple],
    ) -> SyntaxStructure:
        """构建句法结构"""
        # 提取主谓宾
        subject = ""
        predicate = ""
        obj = ""
        modifiers = {}

        for idx, (word, pos_tag, dep_info) in enumerate(zip(seg, pos, parser)):
            dep_rel, head_idx = dep_info

            # 主谓关系
            if dep_rel == 'SBV':  # 主谓关系
                subject = word
            elif dep_rel == 'VOB':  # 动宾关系
                obj = word
            elif dep_rel == 'HED':  # 核心谓词
                predicate = word
            elif dep_rel in ['ATT', 'ADV']:  # 定中/状中
                head_word = seg[head_idx] if head_idx < len(seg) else ""
                if head_word not in modifiers:
                    modifiers[head_word] = []
                modifiers[head_word].append(word)

        return SyntaxStructure(
            words=seg,
            poses=pos,
            subject=subject,
            predicate=predicate,
            object=obj,
            modifiers=modifiers,
        )

    def _extract_entities_from_ner(
        self,
        ner_result: List[tuple],
        text: str,
    ) -> List['Entity']:
        """从 NER 结果提取实体"""
        from alice.nlp.base import EntityType

        entities = []
        type_mapping = {
            'Nh': EntityType.PERSON,
            'Ni': EntityType.ORGANIZATION,
            'Ns': EntityType.LOCATION,
            'nt': EntityType.ORGANIZATION,
            'nz': EntityType.ORGANIZATION,
            'time': EntityType.TIME,
            'date': EntityType.DATE,
        }

        for entity_text, entity_type in ner_result:
            etype = type_mapping.get(entity_type, EntityType.GENERAL)
            entities.append(Entity(
                text=entity_text,
                entity_type=etype,
                start_pos=text.find(entity_text),
                confidence=0.9,
            ))

        return entities

    def extract_entities(self, text: str) -> List['Entity']:
        """提取实体"""
        result = self.analyze(text)
        return result.entities

    def get_syntax(self, text: str) -> Optional[SyntaxStructure]:
        """获取句法结构"""
        result = self.analyze(text)
        return result.syntax

    def parse(self, text: str) -> SyntaxStructure:
        """
        解析句子（兼容旧接口）

        Args:
            text: 待分析文本

        Returns:
            句法结构
        """
        syntax = self.get_syntax(text)
        return syntax or SyntaxStructure(words=list(text))

    def get_main_structure(self, text: str) -> Dict[str, str]:
        """
        获取句子主干（兼容旧接口）

        Args:
            text: 待分析文本

        Returns:
            主干结构 {subject, predicate, object}
        """
        syntax = self.get_syntax(text)
        if not syntax:
            return {'subject': '', 'predicate': '', 'object': ''}

        return {
            'subject': syntax.subject,
            'predicate': syntax.predicate,
            'object': syntax.object,
        }
