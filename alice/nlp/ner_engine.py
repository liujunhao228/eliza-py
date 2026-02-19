#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NER 引擎模块 - 命名实体识别

基于规则和词典的轻量级实体识别
支持 LTP 增强模式
"""

import logging
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from alice.nlp.base import NlpEngine, Entity, EntityType

logger = logging.getLogger(__name__)


class NerEngine(NlpEngine):
    """
    命名实体识别引擎

    特性:
    - 规则优先：基于词典和规则
    - 可选 LTP 增强
    - 上下文实体追踪
    """

    # 人称代词
    PRONOUNS: Set[str] = {
        '我', '你', '他', '她', '它', '咱', '您',
        '我们', '你们', '他们', '她们', '它们', '咱们',
        '我自己', '你自己', '他自己', '她自己', '它自己',
        '人家', '别人', '大家', '各位', '彼此', '互相',
        '谁', '什么', '哪', '哪些',
    }

    # 称谓/关系词
    TITLES: Set[str] = {
        '朋友', '家人', '爸爸', '妈妈', '父亲', '母亲',
        '哥哥', '姐姐', '弟弟', '妹妹', '儿子', '女儿',
        '老师', '同学', '同事', '领导', '老板',
    }

    # 常见姓氏
    SURNAMES: Set[str] = {
        '李', '王', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
        '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗',
    }

    # 时间词
    TIME_WORDS: Set[str] = {
        '今天', '昨天', '明天', '刚才', '最近', '上周', '下周',
        '现在', '当时', '早上', '中午', '晚上', '凌晨',
    }

    # 情感词
    EMOTION_WORDS: Dict[str, Set[str]] = field(default_factory=lambda: {
        'positive': {
            '开心', '高兴', '快乐', '幸福', '满意', '喜欢', '爱',
            '美好', '顺利', '成功', '优秀', '温暖', '安心',
        },
        'negative': {
            '难过', '生气', '焦虑', '痛苦', '失望', '讨厌', '恨',
            '烦恼', '压力', '累', '困', '烦', '糟糕', '伤心',
            '悲伤', '沮丧', '愤怒', '紧张', '害怕', '孤独',
        },
    })

    def __init__(self, use_ltp: bool = False, ltp_engine: Optional['LtpEngine'] = None):
        """
        初始化 NER 引擎

        Args:
            use_ltp: 是否使用 LTP 增强
            ltp_engine: LTP 引擎实例
        """
        self.use_ltp = use_ltp
        self.ltp_engine = ltp_engine
        self._entities_history: Dict[str, List[Entity]] = {}

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return True

    def analyze(self, text: str) -> 'NlpResult':
        """分析文本（完整 NLP 分析）"""
        from alice.nlp.base import NlpResult

        entities = self.extract_entities(text)

        # 情感分析
        sentiment = self._analyze_sentiment(text)

        return NlpResult(
            text=text,
            entities=entities,
            sentiment=sentiment,
        )

    def extract_entities(self, text: str) -> List[Entity]:
        """
        提取实体

        Args:
            text: 待分析文本

        Returns:
            实体列表
        """
        entities = []

        # 1. 人称代词
        entities.extend(self._extract_pronouns(text))

        # 2. 称谓/关系
        entities.extend(self._extract_titles(text))

        # 3. 时间词
        entities.extend(self._extract_time_words(text))

        # 4. 简单人名（姓氏 + 名字模式）
        entities.extend(self._extract_person_names(text))

        # 5. LTP 增强
        if self.use_ltp and self.ltp_engine and self.ltp_engine.is_available:
            ltp_entities = self.ltp_engine.extract_entities(text)
            entities = self._merge_entities(entities, ltp_entities)

        return entities

    def _extract_pronouns(self, text: str) -> List[Entity]:
        """提取人称代词"""
        entities = []
        for pronoun in self.PRONOUNS:
            if pronoun in text:
                start = text.find(pronoun)
                entities.append(Entity(
                    text=pronoun,
                    entity_type=EntityType.PRONOUN,
                    start_pos=start,
                    end_pos=start + len(pronoun),
                ))
        return entities

    def _extract_titles(self, text: str) -> List[Entity]:
        """提取称谓/关系"""
        entities = []
        for title in self.TITLES:
            if title in text:
                start = text.find(title)
                entities.append(Entity(
                    text=title,
                    entity_type=EntityType.TITLE,
                    start_pos=start,
                    end_pos=start + len(title),
                ))
        return entities

    def _extract_time_words(self, text: str) -> List[Entity]:
        """提取时间词"""
        entities = []
        for time_word in self.TIME_WORDS:
            if time_word in text:
                start = text.find(time_word)
                entities.append(Entity(
                    text=time_word,
                    entity_type=EntityType.TIME,
                    start_pos=start,
                    end_pos=start + len(time_word),
                ))
        return entities

    def _extract_person_names(self, text: str) -> List[Entity]:
        """提取简单人名"""
        entities = []
        # 匹配 2-3 字的中文名字（姓氏 + 名字）
        pattern = r'([{' + ''.join(self.SURNAMES) + r'}][\u4e00-\u9fa5]{1,2})'
        for match in re.finditer(pattern, text):
            name = match.group(1)
            # 排除已经是称谓的情况
            if name not in self.TITLES:
                entities.append(Entity(
                    text=name,
                    entity_type=EntityType.PERSON,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.7,
                ))
        return entities

    def _analyze_sentiment(self, text: str) -> float:
        """
        简单情感分析

        Returns:
            情感分数 (-1.0 到 1.0)
        """
        pos_count = sum(1 for word in self.EMOTION_WORDS['positive'] if word in text)
        neg_count = sum(1 for word in self.EMOTION_WORDS['negative'] if word in text)

        if pos_count + neg_count == 0:
            return 0.0

        return (pos_count - neg_count) / (pos_count + neg_count)

    def _merge_entities(
        self,
        rule_entities: List[Entity],
        ltp_entities: List[Entity],
    ) -> List[Entity]:
        """融合规则和 LTP 的实体识别结果"""
        all_entities = rule_entities + ltp_entities

        # 去重（基于文本和类型）
        seen = set()
        unique = []
        for entity in all_entities:
            key = (entity.text, entity.entity_type)
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        return unique

    def get_syntax(self, text: str) -> Optional['SyntaxStructure']:
        """获取句法结构（委托给 LTP 引擎）"""
        if self.use_ltp and self.ltp_engine:
            return self.ltp_engine.get_syntax(text)
        return None

    def track_entity(self, entity: Entity, context_id: str = 'default') -> None:
        """
        追踪实体到上下文

        Args:
            entity: 实体
            context_id: 上下文 ID
        """
        if context_id not in self._entities_history:
            self._entities_history[context_id] = []
        self._entities_history[context_id].append(entity)

    def get_tracked_entities(
        self,
        context_id: str = 'default',
        limit: int = 10,
    ) -> List[Entity]:
        """
        获取追踪的实体

        Args:
            context_id: 上下文 ID
            limit: 返回数量限制

        Returns:
            实体列表
        """
        history = self._entities_history.get(context_id, [])
        return history[-limit:]

    def clear_history(self, context_id: Optional[str] = None) -> None:
        """
        清理实体追踪历史

        Args:
            context_id: 上下文 ID，None 则清理全部
        """
        if context_id:
            self._entities_history.pop(context_id, None)
        else:
            self._entities_history.clear()
