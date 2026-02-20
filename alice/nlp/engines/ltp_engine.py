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
            # 使用正确的LTP任务参数，包含NER任务
            result = self._ltp.pipeline(
                [text],
                tasks=['cws', 'pos', 'dep', 'ner']  # 添加NER任务
            )
            
            # 正确处理LTPOutput对象返回值
            if hasattr(result, 'cws'):
                # LTPOutput对象格式
                seg = result.cws[0] if result.cws else list(text)
                pos = result.pos[0] if hasattr(result, 'pos') and result.pos else ['n'] * len(seg)
                
                # 处理依存关系
                if hasattr(result, 'dep') and result.dep:
                    dep_data = result.dep[0]
                    if isinstance(dep_data, dict):
                        # 新版本格式：{'head': [...], 'label': [...]}
                        parser = list(zip(dep_data.get('label', []), dep_data.get('head', [])))
                    else:
                        # 兼容旧版本格式
                        parser = dep_data if isinstance(dep_data, list) else []
                else:
                    # 如果没有依存关系信息，创建默认结构
                    parser = [('HED', -1)] + [('SBV', 0)] * (len(seg) - 1) if seg else []
                
                # 处理NER结果
                if hasattr(result, 'ner') and result.ner:
                    ner_result = result.ner[0]
                else:
                    # 如果没有NER信息，创建空结果
                    ner_result = []
            else:
                # 如果返回格式不符合预期，记录错误但不降级
                logger.error("LTP返回格式不符合预期")
                raise ValueError("LTP返回格式错误")

            syntax = self._build_syntax(seg, pos, parser)
            entities = self._extract_entities(ner_result, text)
            
            return NlpResult(
                text=text,
                tokens=seg,
                entities=entities,
                syntax=syntax,
            )
            
        except Exception as e:
            logger.error(f"LTP 分析失败：{e}", exc_info=True)
            # 对于核心功能，应该明确报错而不是降级
            raise RuntimeError(f"LTP句法分析失败: {str(e)}") from e
    
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
    
    def _simple_analyze(self, text: str) -> NlpResult:
        """简化分析（降级方案）"""
        # 简单分词（按字符）
        tokens = list(text)
        
        return NlpResult(
            text=text,
            tokens=tokens,
            syntax=SyntaxStructure(words=tokens),
        )
    
    def _extract_entities_simple(self, seg: List[str], pos: List[str], text: str) -> List[Entity]:
        """基于词性和规则的简单实体识别"""
        entities = []
        
        for i, (word, pos_tag) in enumerate(zip(seg, pos)):
            # 基于词性标注的简单实体识别
            if pos_tag.startswith('nh'):  # 人名
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.PERSON,
                    start_pos=text.find(word),
                    end_pos=text.find(word) + len(word),
                    confidence=0.7
                ))
            elif pos_tag.startswith('ns'):  # 地名
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.LOCATION,
                    start_pos=text.find(word),
                    end_pos=text.find(word) + len(word),
                    confidence=0.7
                ))
            elif pos_tag.startswith('ni'):  # 机构名
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.ORGANIZATION,
                    start_pos=text.find(word),
                    end_pos=text.find(word) + len(word),
                    confidence=0.7
                ))
        
        return entities
