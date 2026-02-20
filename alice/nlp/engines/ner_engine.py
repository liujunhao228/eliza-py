#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NER 引擎 - 基于规则的命名实体识别
"""

import logging
import re
from typing import List, Optional, Set

from alice.nlp.base import EntityRecognizer, Entity, EntityType
from alice.nlp.dictionaries.dictionary_manager import DictionaryManager

logger = logging.getLogger(__name__)


class NerEngine(EntityRecognizer):
    """
    基于规则的命名实体识别引擎
    
    识别目标:
    - 人称代词（我、你、他、我们...）
    - 称谓/关系（朋友、家人、老师、老板...）
    - 时间词（今天、昨天、最近、刚才...）
    - 中文人名（常见姓氏 + 名字模式）
    
    可选增强:
    - 使用 LTP 结果补充（人名、地名、机构名）
    """
    
    PRONOUNS: Set[str] = {
        '我', '你', '他', '她', '它', '咱', '您',
        '我们', '你们', '他们', '她们', '它们', '咱们',
        '我自己', '你自己', '他自己', '她自己', '它自己',
        '人家', '别人', '大家', '各位', '彼此',
    }
    
    TITLES: Set[str] = {
        '朋友', '家人', '爸爸', '妈妈', '父亲', '母亲',
        '哥哥', '姐姐', '弟弟', '妹妹', '儿子', '女儿',
        '老师', '同学', '同事', '领导', '老板', '亲戚',
    }
    
    TIME_WORDS: Set[str] = {
        '今天', '昨天', '明天', '前天', '后天', '刚才',
        '最近', '上周', '下周', '现在', '当时', '此刻',
        '方才', '刚刚', '早上', '中午', '晚上', '凌晨',
    }
    
    SURNAMES: Set[str] = {
        '李', '王', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
        '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗',
        '梁', '宋', '谢', '韩', '唐', '冯', '于', '董', '萧', '程',
        '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕', '苏',
        '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎', '余',
        '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜', '范',
        '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆', '郝',
        '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '尹', '史',
        '顾', '侯', '邵', '孟', '龙', '万', '段', '钱', '汤',
    }
    
    def __init__(
        self,
        use_ltp: bool = False,
        ltp_engine: Optional['LtpEngine'] = None,
        dictionary_manager: Optional[DictionaryManager] = None,
    ):
        """
        初始化 NER 引擎
        
        Args:
            use_ltp: 是否使用 LTP 增强
            ltp_engine: LTP 引擎实例
            dictionary_manager: 词典管理器
        """
        self.use_ltp = use_ltp
        self.ltp_engine = ltp_engine
        self.dictionary_manager = dictionary_manager or DictionaryManager()
        
        self._load_dictionaries()
    
    def _load_dictionaries(self):
        """从词典文件加载扩展词表"""
        pronouns_data = self.dictionary_manager.get_list(
            'entity_patterns', 'pronouns'
        )
        if pronouns_data:
            self.PRONOUNS.update(pronouns_data)
        
        titles_data = self.dictionary_manager.get_list(
            'entity_patterns', 'titles'
        )
        if titles_data:
            self.TITLES.update(titles_data)
        
        time_data = self.dictionary_manager.get_list(
            'entity_patterns', 'time_words'
        )
        if time_data:
            self.TIME_WORDS.update(time_data)
        
        logger.info(
            f"NER 词典加载完成：代词={len(self.PRONOUNS)}, "
            f"称谓={len(self.TITLES)}, 时间词={len(self.TIME_WORDS)}"
        )
    
    @property
    def is_available(self) -> bool:
        return True
    
    def recognize(self, text: str) -> List[Entity]:
        """识别实体"""
        entities = []
        
        entities.extend(self._extract_pronouns(text))
        entities.extend(self._extract_titles(text))
        entities.extend(self._extract_time_words(text))
        entities.extend(self._extract_person_names(text))
        
        if self.use_ltp and self.ltp_engine and self.ltp_engine.is_available:
            ltp_entities = self.ltp_engine.analyze(text).entities
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
        """提取中文人名"""
        entities = []
        surname_chars = ''.join(self.SURNAMES)
        pattern = rf'([{surname_chars}][\u4e00-\u9fa5]{{1,2}})'
        
        for match in re.finditer(pattern, text):
            name = match.group(1)
            
            if name in self.TITLES:
                continue
            
            if name in {'中国', '什么', '怎么', '为什么', '如何', '哪里'}:
                continue
            
            entities.append(Entity(
                text=name,
                entity_type=EntityType.PERSON,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.7,
            ))
        
        return entities
    
    def _merge_entities(
        self,
        rule_entities: List[Entity],
        ltp_entities: List[Entity],
    ) -> List[Entity]:
        """融合规则和 LTP 的实体结果"""
        seen = set()
        merged = []
        
        for entity in rule_entities:
            key = (entity.text, entity.entity_type)
            if key not in seen:
                seen.add(key)
                merged.append(entity)
        
        for entity in ltp_entities:
            key = (entity.text, entity.entity_type)
            if key not in seen:
                seen.add(key)
                merged.append(entity)
        
        return merged
