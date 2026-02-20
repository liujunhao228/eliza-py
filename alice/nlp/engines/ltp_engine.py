#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎 - 句法分析与实体识别
"""

import logging
from typing import List, Optional, Dict

from alice.nlp.base import (
    SyntaxAnalyzer,
    Entity,
    EntityType,
    NlpResult,
    SyntaxStructure,
)
from alice.exceptions import DependencyError

logger = logging.getLogger(__name__)

# 尝试导入 LTP
try:
    from ltp import LTP
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False
    logger.info("LTP 未安装，句法分析功能不可用（可选：pip install ltp>=4.2.10）")


# LTP 实体类型映射
LTP_ENTITY_MAPPING: Dict[str, EntityType] = {
    'Nh': EntityType.PERSON,
    'Ni': EntityType.ORGANIZATION,
    'Ns': EntityType.LOCATION,
    'nt': EntityType.ORGANIZATION,
    'nz': EntityType.ORGANIZATION,
    'time': EntityType.TIME,
    'date': EntityType.DATE,
}


class LtpEngine(SyntaxAnalyzer):
    """
    LTP 句法分析引擎
    
    功能:
    - 分词 + 词性标注
    - 依存句法分析（主谓宾提取）
    - 命名实体识别
    
    注意:
    - 模型首次加载较慢（约 5-10 秒）
    - 支持懒加载
    - 不支持情感分析
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        lazy_load: bool = True,
    ):
        """
        初始化 LTP 引擎
        
        Args:
            model_path: 模型路径，None 使用官方默认模型
            lazy_load: 是否懒加载（首次分析时才加载模型）
        """
        if not LTP_AVAILABLE:
            raise DependencyError(
                "LTP 库未安装",
                suggestion="pip install ltp>=4.2.10"
            )
        
        self._model_path = model_path
        self._lazy_load = lazy_load
        self._ltp: Optional[LTP] = None
        self._initialized = False
        
        if not lazy_load:
            self._load_model()
    
    def _load_model(self) -> bool:
        """加载 LTP 模型"""
        if self._initialized:
            return True
        
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
            return False
    
    @property
    def is_available(self) -> bool:
        """检查是否可用"""
        if not LTP_AVAILABLE:
            return False
        if self._lazy_load:
            return True
        return self._ltp is not None
    
    def _ensure_loaded(self) -> bool:
        """确保模型已加载"""
        if not self._initialized:
            return self._load_model()
        return self._ltp is not None
    
    def analyze(self, text: str) -> NlpResult:
        """完整分析"""
        if not self._ensure_loaded():
            logger.warning("LTP 模型未加载，返回空结果")
            return NlpResult(text=text, tokens=list(text))
        
        try:
            result = self._ltp.pipeline(
                [text],
                tasks=['seg', 'pos', 'parser', 'ner']
            )
            seg, pos, parser, ner = result
            
            syntax = self._build_syntax(seg[0], pos[0], parser[0])
            entities = self._extract_entities(ner[0], text)
            
            return NlpResult(
                text=text,
                tokens=seg[0],
                entities=entities,
                syntax=syntax,
            )
            
        except Exception as e:
            logger.error(f"LTP 分析失败：{e}", exc_info=True)
            return NlpResult(text=text, tokens=list(text))
    
    def _build_syntax(
        self,
        seg: List[str],
        pos: List[str],
        parser: List[tuple],
    ) -> SyntaxStructure:
        """构建句法结构"""
        subject = ""
        predicate = ""
        obj = ""
        modifiers: Dict[str, List[str]] = {}
        
        for idx, (word, pos_tag, dep_info) in enumerate(
            zip(seg, pos, parser)
        ):
            dep_rel, head_idx = dep_info
            
            if dep_rel == 'SBV':
                subject = word
            elif dep_rel == 'VOB':
                obj = word
            elif dep_rel == 'HED':
                predicate = word
            elif dep_rel in ['ATT', 'ADV']:
                head_word = seg[head_idx] if head_idx < len(seg) else ""
                if head_word:
                    modifiers.setdefault(head_word, []).append(word)
        
        return SyntaxStructure(
            words=seg,
            poses=pos,
            subject=subject,
            predicate=predicate,
            object=obj,
            modifiers=modifiers,
        )
    
    @classmethod
    def clear_cache(cls):
        """清除 LTP 缓存（用于恢复）"""
        # LTP 本身没有缓存机制，这个方法用于兼容恢复管理器
        pass

    def reset(self):
        """重置引擎状态"""
        self._ltp = None
        self._initialized = False
        logger.info("LTP 引擎已重置")

    def _extract_entities(
        self,
        ner_result: List[tuple],
        text: str,
    ) -> List[Entity]:
        """从 NER 结果提取实体"""
        entities = []
        
        for entity_text, entity_type in ner_result:
            etype = LTP_ENTITY_MAPPING.get(
                entity_type,
                EntityType.GENERAL
            )
            start_pos = text.find(entity_text)
            
            entities.append(Entity(
                text=entity_text,
                entity_type=etype,
                start_pos=start_pos,
                end_pos=start_pos + len(entity_text),
                confidence=0.9,
            ))
        
        return entities
