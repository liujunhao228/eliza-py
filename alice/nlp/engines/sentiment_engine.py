#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情感分析引擎 - 基于词典和规则
"""

import logging
from typing import Dict, List, Set, Optional, Tuple

from alice.nlp.base import SentimentAnalyzer
from alice.nlp.dictionaries.dictionary_manager import DictionaryManager

logger = logging.getLogger(__name__)


class SentimentEngine(SentimentAnalyzer):
    """
    基于词典的情感分析引擎
    
    功能:
    - 基础情感极性判断（正面/负面/中性）
    - 情感强度计算
    - 否定词处理
    - 程度副词加权
    """
    
    NEGATION_WORDS: Set[str] = {
        '不', '没', '没有', '别', '勿', '莫', '无', '未',
        '从不', '从未', '绝不', '决不', '未必',
    }
    
    DEGREE_ADVERBS: Dict[str, float] = {
        '极其': 2.5,
        '非常': 2.0,
        '特别': 2.0,
        '十分': 2.0,
        '格外': 2.0,
        '很': 1.5,
        '挺': 1.5,
        '相当': 1.5,
        '比较': 1.2,
        '较为': 1.2,
        '稍': 0.8,
        '稍微': 0.8,
        '略微': 0.8,
        '有点': 0.6,
        '有些': 0.6,
        '不太': 0.5,
    }
    
    def __init__(
        self,
        dictionary_manager: Optional[DictionaryManager] = None,
    ):
        """
        初始化情感分析引擎
        
        Args:
            dictionary_manager: 词典管理器
        """
        self.dictionary_manager = dictionary_manager or DictionaryManager()
        
        self._positive_words: Set[str] = set()
        self._negative_words: Set[str] = set()
        
        self._load_dictionaries()
    
    def _load_dictionaries(self):
        """加载情感词典"""
        emotion_words = self.dictionary_manager.load('emotion_words')
        
        self._positive_words = set(emotion_words.get('positive', []))
        self._negative_words = set(emotion_words.get('negative', []))
        
        negation_data = self.dictionary_manager.get_list(
            'sentiment_rules', 'negation_words'
        )
        if negation_data:
            self.NEGATION_WORDS.update(negation_data)
        
        degree_data = self.dictionary_manager.get_dict(
            'sentiment_rules', 'degree_adverbs'
        )
        if degree_data:
            self.DEGREE_ADVERBS.update(degree_data)
        
        logger.info(
            f"情感词典加载完成：正面={len(self._positive_words)}, "
            f"负面={len(self._negative_words)}"
        )
    
    @property
    def is_available(self) -> bool:
        return True
    
    def analyze(self, text: str) -> float:
        """分析情感"""
        pos_matches = self._find_matches(text, self._positive_words)
        neg_matches = self._find_matches(text, self._negative_words)
        
        if not pos_matches and not neg_matches:
            return 0.0
        
        pos_matches = self._apply_negation(text, pos_matches, is_positive=True)
        neg_matches = self._apply_negation(text, neg_matches, is_positive=False)
        
        pos_score = self._apply_degree(text, pos_matches)
        neg_score = self._apply_degree(text, neg_matches)
        
        total = pos_score + neg_score
        if total == 0:
            return 0.0
        
        return (pos_score - neg_score) / abs(total)
    
    def _find_matches(
        self,
        text: str,
        word_set: Set[str],
    ) -> List[Tuple[str, int]]:
        """查找匹配的情感词"""
        matches = []
        for word in word_set:
            start = 0
            while True:
                pos = text.find(word, start)
                if pos == -1:
                    break
                matches.append((word, pos))
                start = pos + 1
        return matches
    
    def _apply_negation(
        self,
        text: str,
        matches: List[Tuple[str, int]],
        is_positive: bool,
    ) -> List[Tuple[str, int, bool]]:
        """应用否定词规则"""
        result = []
        
        for word, pos in matches:
            start_check = max(0, pos - 6)
            preceding_text = text[start_check:pos]
            
            is_negated = any(
                neg in preceding_text
                for neg in self.NEGATION_WORDS
            )
            
            result.append((word, pos, is_negated))
        
        return result
    
    def _apply_degree(
        self,
        text: str,
        matches: List[Tuple[str, int, bool]],
    ) -> float:
        """应用程度副词规则"""
        total_score = 0.0
        
        for word, pos, is_negated in matches:
            base_score = 1.0
            
            start_check = max(0, pos - 10)
            preceding_text = text[start_check:pos]
            
            degree_weight = 1.0
            for adverb, weight in self.DEGREE_ADVERBS.items():
                if adverb in preceding_text:
                    adverb_pos = preceding_text.rfind(adverb)
                    if adverb_pos > len(preceding_text) - 10:
                        degree_weight = weight
                        break
            
            if is_negated:
                total_score -= base_score * degree_weight
            else:
                total_score += base_score * degree_weight
        
        return total_score
    
    def get_label(self, score: float) -> str:
        """获取情感标签"""
        if score > 0.2:
            return 'positive'
        elif score < -0.2:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_with_label(self, text: str) -> Tuple[float, str]:
        """分析情感并返回标签"""
        score = self.analyze(text)
        return score, self.get_label(score)
