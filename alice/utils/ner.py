#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命名实体识别模块 - NER (Named Entity Recognition)
支持多种实体类型的识别和追踪
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

# 模块级 logger
logger = logging.getLogger(__name__)


class EntityType(Enum):
    """实体类型枚举"""
    # 人称代词
    PRONOUN = "pronoun"
    # 人名
    PERSON = "person"
    # 称谓/关系
    TITLE = "title"
    # 地名
    LOCATION = "location"
    # 机构
    ORGANIZATION = "organization"
    # 时间
    TIME = "time"
    # 日期
    DATE = "date"
    # 数字/数量
    NUMBER = "number"
    # 情感
    EMOTION = "emotion"
    # 通用
    GENERAL = "general"


@dataclass
class Entity:
    """命名实体数据类"""
    text: str                    # 实体文本
    entity_type: EntityType      # 实体类型
    start_pos: int = 0          # 在原文中的起始位置
    end_pos: int = 0            # 在原文中的结束位置
    confidence: float = 1.0     # 置信度
    metadata: Dict = field(default_factory=dict)

    def to_tuple(self) -> Tuple[str, str]:
        """转换为 (类型，文本) 元组"""
        return (self.entity_type.value, self.text)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'text': self.text,
            'type': self.entity_type.value,
            'start': self.start_pos,
            'end': self.end_pos,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class NERConfig:
    """NER 配置类"""

    # 人称代词
    PRONOUNS = {
        '我', '你', '他', '她', '它', '咱', '您',
        '我们', '你们', '他们', '她们', '它们', '咱们',
        '我自己', '你自己', '他自己', '她自己', '它自己',
        '我自己们', '你自己们', '人家', '别人', '大家', '各位',
        '彼此', '互相', '谁', '什么', '哪', '哪些'
    }

    # 称谓/关系词
    TITLES = {
        # 家庭成员
        '爸爸', '妈妈', '父亲', '母亲', '爸', '妈', '爹', '娘',
        '儿子', '女儿', '哥', '姐', '弟', '妹', '哥哥', '姐姐', '弟弟', '妹妹',
        '爷爷', '奶奶', '外公', '外婆', '祖父', '祖母',
        '叔叔', '阿姨', '舅舅', '舅妈', '姑姑', '姑父', '姨妈', '姨父',
        '老公', '老婆', '丈夫', '妻子', '男朋友', '女朋友', '对象',
        '孙子', '孙女', '外孙', '外孙女', '媳妇', '女婿',
        '亲戚', '家人', '亲属', '亲人',

        # 社会关系
        '朋友', '好友', '闺蜜', '兄弟', '哥们', '姐们', '死党',
        '同事', '同学', '同窗', '室友', '舍友',
        '老师', '教授', '导师', '教练', '师傅', '徒弟',
        '老板', '上司', '领导', '经理', '总监', '总裁',
        '员工', '下属', '秘书', '助理',
        '医生', '护士', '律师', '警察', '司机', '服务员',
        '邻居', '房东', '租客', '客户', '顾客', '乘客',

        # 通用称谓
        '人', '人们', '某人', '有人', '任何人', '每个人',
        '这个人', '那个人', '这些人', '那些人',
        '这位', '那位', '小', '老'  # 用于匹配小 + 姓，老 + 姓
    }

    # 地点相关
    LOCATIONS = {
        '家', '家里', '家中', '老家', '故乡', '家乡',
        '学校', '公司', '单位', '办公室', '办公室', '工厂',
        '医院', '诊所', '药店',
        '餐厅', '饭店', '酒店', '宾馆', '咖啡馆', '酒吧',
        '商店', '超市', '商场', '市场', '书店',
        '公园', '广场', '电影院', '剧院', '博物馆', '图书馆',
        '车站', '机场', '地铁站', '公交站',
        '银行', '邮局', '派出所', '政府',
        '国内', '国外', '本地', '外地', '这里', '那里', '哪里',
        '北京', '上海', '广州', '深圳', '成都', '杭州', '南京', '武汉',
        '中国', '美国', '日本', '韩国', '英国', '法国', '德国'
    }

    # 组织机构
    ORGANIZATIONS = {
        '公司', '企业', '集团', '工厂', '单位',
        '学校', '大学', '学院', '中学', '小学', '幼儿园',
        '医院', '诊所',
        '政府', '部门', '局', '委员会', '协会', '学会',
        '银行', '基金', '交易所',
        '团队', '组织', '机构', '中心', '基地'
    }

    # 时间词
    TIME_WORDS = {
        '现在', '目前', '当前', '此刻', '这时', '当时',
        '今天', '昨天', '明天', '后天', '大后天', '大前天',
        '今早', '明早', '昨晚', '明晚',
        '早上', '上午', '中午', '下午', '晚上', '深夜', '凌晨',
        '刚才', '刚刚', '刚才', '方才',
        '最近', '近来', '近期', '近来',
        '以前', '之前', '过去', '曾经', '当年',
        '以后', '之后', '将来', '未来', '今后', '往后',
        '同时', '当时', '那时', '这时候', '那会儿',
        '总是', '经常', '常常', '偶尔', '有时', '时常',
        '马上', '立刻', '立即', '很快', '迟早',
        '每天', '每周', '每月', '每年', '天天', '年年',
        '周一', '周二', '周三', '周四', '周五', '周六', '周日',
        '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日',
        '周末', '工作日', '假期', '节假日'
    }

    # 日期词
    DATE_WORDS = {
        '年', '月', '日', '号', '周', '星期',
        '初', '上旬', '中旬', '下旬',
        '世纪', '年代', '时代', '时期', '时候',
        '春节', '夏天', '秋天', '冬天', '春天',
        '元旦', '清明', '端午', '中秋', '国庆', '圣诞',
        '生日', '纪念日', '节日'
    }

    # 情感词
    EMOTION_WORDS = {
        # 正面
        '开心', '高兴', '快乐', '幸福', '满意', '喜欢', '爱',
        '兴奋', '激动', '喜悦', '欣慰', '自豪', '骄傲',
        '轻松', '舒服', '愉快', '爽', '棒', '好', '优秀',
        '感谢', '感激', '感动', '温暖', '安心', '放心',
        # 负面
        '难过', '伤心', '痛苦', '悲伤', '悲痛', '伤心',
        '生气', '愤怒', '恼火', '烦躁', '郁闷', '憋屈',
        '焦虑', '紧张', '害怕', '恐惧', '担心', '忧虑',
        '失望', '绝望', '沮丧', '失落', '灰心',
        '累', '困', '烦', '糟糕', '差', '讨厌', '恨',
        '孤独', '寂寞', '空虚', '无聊', '无奈', '无助'
    }

    # 情感程度副词
    DEGREE_ADVERBS = {
        '很', '非常', '特别', '极其', '十分', '太', '最',
        '比较', '有点', '有些', '稍微', '略微', '挺',
        '超级', '格外', '异常', '尤为', '尤其', '相当'
    }


class RuleBasedNER:
    """
    基于规则的命名实体识别器

    特点:
    - 不依赖外部模型，轻量快速
    - 支持多种实体类型识别
    - 可配置和扩展
    """

    def __init__(self, config: Optional[NERConfig] = None):
        """
        初始化 NER 识别器

        Args:
            config: NER 配置对象，None 则使用默认配置
        """
        self.config = config or NERConfig()
        self._compile_patterns()

    def _compile_patterns(self):
        """编译正则表达式模式"""
        # 人名模式：小/老 + 姓
        self.surname_pattern = re.compile(r'[小老][张王李赵刘陈杨黄周吴徐孙朱马胡郭何高郑罗]')

        # 数字模式
        self.number_pattern = re.compile(r'\d+(?:\.\d+)?(?:万|千|百|十|亿)?')

        # 日期模式：YYYY-MM-DD, YYYY 年 MM 月 DD 日
        self.date_pattern = re.compile(
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?'
        )

        # 时间模式：HH:MM, HH 点 MM 分
        self.time_pattern = re.compile(
            r'\d{1,2}[:点]\d{2}(?:分)?'
        )

    def extract(self, text: str) -> List[Entity]:
        """
        从文本中提取命名实体

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        entities = []

        # 1. 提取人称代词
        entities.extend(self._extract_pronouns(text))

        # 2. 提取称谓/关系
        entities.extend(self._extract_titles(text))

        # 3. 提取人名
        entities.extend(self._extract_person_names(text))

        # 4. 提取地点
        entities.extend(self._extract_locations(text))

        # 5. 提取组织机构
        entities.extend(self._extract_organizations(text))

        # 6. 提取时间
        entities.extend(self._extract_time(text))

        # 7. 提取日期
        entities.extend(self._extract_date(text))

        # 8. 提取数字
        entities.extend(self._extract_numbers(text))

        # 9. 提取情感
        entities.extend(self._extract_emotions(text))

        # 按位置排序
        entities.sort(key=lambda e: (e.start_pos, -len(e.text)))

        # 去重（重叠的实体只保留一个）
        entities = self._remove_overlapping(entities)

        return entities

    def _extract_pronouns(self, text: str) -> List[Entity]:
        """提取人称代词"""
        entities = []
        for pronoun in self.config.PRONOUNS:
            start = 0
            while True:
                pos = text.find(pronoun, start)
                if pos == -1:
                    break
                entities.append(Entity(
                    text=pronoun,
                    entity_type=EntityType.PRONOUN,
                    start_pos=pos,
                    end_pos=pos + len(pronoun),
                    confidence=1.0
                ))
                start = pos + len(pronoun)
        return entities

    def _extract_titles(self, text: str) -> List[Entity]:
        """提取称谓/关系词"""
        entities = []
        for title in self.config.TITLES:
            start = 0
            while True:
                pos = text.find(title, start)
                if pos == -1:
                    break
                # 避免与代词重复
                if text[pos:pos + len(title)] in self.config.PRONOUNS:
                    start = pos + 1
                    continue
                entities.append(Entity(
                    text=title,
                    entity_type=EntityType.TITLE,
                    start_pos=pos,
                    end_pos=pos + len(title),
                    confidence=0.9
                ))
                start = pos + len(title)
        return entities

    def _extract_person_names(self, text: str) -> List[Entity]:
        """提取人名"""
        entities = []

        # 匹配 小/老 + 姓
        for match in self.surname_pattern.finditer(text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.PERSON,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))

        return entities

    def _extract_locations(self, text: str) -> List[Entity]:
        """提取地点"""
        entities = []
        for location in self.config.LOCATIONS:
            start = 0
            while True:
                pos = text.find(location, start)
                if pos == -1:
                    break
                entities.append(Entity(
                    text=location,
                    entity_type=EntityType.LOCATION,
                    start_pos=pos,
                    end_pos=pos + len(location),
                    confidence=0.85
                ))
                start = pos + len(location)
        return entities

    def _extract_organizations(self, text: str) -> List[Entity]:
        """提取组织机构"""
        entities = []
        for org in self.config.ORGANIZATIONS:
            start = 0
            while True:
                pos = text.find(org, start)
                if pos == -1:
                    break
                entities.append(Entity(
                    text=org,
                    entity_type=EntityType.ORGANIZATION,
                    start_pos=pos,
                    end_pos=pos + len(org),
                    confidence=0.8
                ))
                start = pos + len(org)
        return entities

    def _extract_time(self, text: str) -> List[Entity]:
        """提取时间"""
        entities = []

        # 匹配时间词
        for time_word in self.config.TIME_WORDS:
            start = 0
            while True:
                pos = text.find(time_word, start)
                if pos == -1:
                    break
                entities.append(Entity(
                    text=time_word,
                    entity_type=EntityType.TIME,
                    start_pos=pos,
                    end_pos=pos + len(time_word),
                    confidence=0.9
                ))
                start = pos + len(time_word)

        # 匹配具体时间格式
        for match in self.time_pattern.finditer(text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.TIME,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))

        return entities

    def _extract_date(self, text: str) -> List[Entity]:
        """提取日期"""
        entities = []

        # 匹配日期词
        for date_word in self.config.DATE_WORDS:
            start = 0
            while True:
                pos = text.find(date_word, start)
                if pos == -1:
                    break
                # 检查是否有数字前缀（如 5 年，3 月）
                if pos > 0 and text[pos - 1].isdigit():
                    # 将数字和日期词合并
                    num_start = pos - 1
                    while num_start > 0 and text[num_start - 1].isdigit():
                        num_start -= 1
                    date_text = text[num_start:pos] + date_word
                    entities.append(Entity(
                        text=date_text,
                        entity_type=EntityType.DATE,
                        start_pos=num_start,
                        end_pos=pos + len(date_word),
                        confidence=0.9
                    ))
                else:
                    entities.append(Entity(
                        text=date_word,
                        entity_type=EntityType.DATE,
                        start_pos=pos,
                        end_pos=pos + len(date_word),
                        confidence=0.7
                    ))
                start = pos + len(date_word)

        # 匹配日期格式
        for match in self.date_pattern.finditer(text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.DATE,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))

        return entities

    def _extract_numbers(self, text: str) -> List[Entity]:
        """提取数字"""
        entities = []
        for match in self.number_pattern.finditer(text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.NUMBER,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.9
            ))
        return entities

    def _extract_emotions(self, text: str) -> List[Entity]:
        """提取情感词"""
        entities = []
        for emotion in self.config.EMOTION_WORDS:
            start = 0
            while True:
                pos = text.find(emotion, start)
                if pos == -1:
                    break
                # 检查是否有程度副词
                degree = ""
                for adv in self.config.DEGREE_ADVERBS:
                    if pos >= len(adv) and text[pos - len(adv):pos] == adv:
                        degree = adv
                        break

                entity_text = degree + emotion if degree else emotion
                entity_start = pos - len(degree) if degree else pos

                entities.append(Entity(
                    text=entity_text,
                    entity_type=EntityType.EMOTION,
                    start_pos=entity_start,
                    end_pos=entity_start + len(entity_text),
                    confidence=0.85,
                    metadata={'degree': degree, 'base_emotion': emotion}
                ))
                start = pos + len(emotion)
        return entities

    def _remove_overlapping(self, entities: List[Entity]) -> List[Entity]:
        """
        移除重叠的实体，保留优先级高的

        Args:
            entities: 实体列表

        Returns:
            去重后的实体列表
        """
        if not entities:
            return entities

        # 按起始位置排序，长度长的优先
        entities.sort(key=lambda e: (e.start_pos, -(e.end_pos - e.start_pos)))

        result = []
        last_end = -1

        for entity in entities:
            if entity.start_pos >= last_end:
                result.append(entity)
                last_end = entity.end_pos
            elif entity.end_pos > last_end:
                # 部分重叠，保留更长的
                if result and (entity.end_pos - entity.start_pos) > (result[-1].end_pos - result[-1].start_pos):
                    result[-1] = entity
                    last_end = entity.end_pos

        return result


class LTPBasedNER(RuleBasedNER):
    """
    基于 LTP 的命名实体识别器（增强版）

    在规则基础上，使用 LTP 进行更精确的实体识别
    """

    def __init__(self, config: Optional[NERConfig] = None):
        super().__init__(config)
        self.ltp_parser = None
        self._ltp_available = False

    def initialize_ltp(self) -> bool:
        """
        初始化 LTP 模型

        Returns:
            是否成功初始化
        """
        if self._ltp_available:
            return True

        try:
            from alice.utils.ltp_parser import LTPParser
            self.ltp_parser = LTPParser()
            self._ltp_available = True
            logger.info("LTP 初始化成功")
            return True
        except Exception as e:
            logger.warning(f"LTP 初始化失败：{e}，将使用规则-based NER")
            return False

    def extract(self, text: str, use_ltp: bool = True) -> List[Entity]:
        """
        从文本中提取命名实体

        Args:
            text: 输入文本
            use_ltp: 是否使用 LTP（如果可用）

        Returns:
            实体列表
        """
        # 首先使用规则提取
        entities = super().extract(text)

        # 如果 LTP 可用且启用，融合 LTP 结果
        if use_ltp and self._ltp_available and self.ltp_parser:
            ltp_entities = self._extract_with_ltp(text)
            entities = self._merge_entities(entities, ltp_entities)

        return entities

    def _extract_with_ltp(self, text: str) -> List[Entity]:
        """使用 LTP 提取实体"""
        entities = []
        try:
            # 获取 LTP 的 NER 结果
            ner_result = self.ltp_parser.get_ner(text)
            for entity_text, entity_type in ner_result:
                start = text.find(entity_text)
                if start != -1:
                    entities.append(Entity(
                        text=entity_text,
                        entity_type=self._map_ltp_type(entity_type),
                        start_pos=start,
                        end_pos=start + len(entity_text),
                        confidence=0.95
                    ))
        except Exception as e:
            logger.warning(f"LTP 实体提取失败：{e}")
        return entities

    def _map_ltp_type(self, ltp_type: str) -> EntityType:
        """映射 LTP 实体类型到系统类型"""
        type_mapping = {
            'Nh': EntityType.PERSON,      # 人名
            'Ni': EntityType.ORGANIZATION,  # 机构
            'ns': EntityType.LOCATION,    # 地名
            'nt': EntityType.ORGANIZATION,  # 机构团体
            'nz': EntityType.ORGANIZATION,  # 其他专有机构
            'nm': EntityType.ORGANIZATION,  # 机构名
            'nl': EntityType.LOCATION,    # 地名
        }
        return type_mapping.get(ltp_type, EntityType.GENERAL)

    def _merge_entities(self, rule_entities: List[Entity],
                        ltp_entities: List[Entity]) -> List[Entity]:
        """
        融合规则和 LTP 的实体识别结果

        Args:
            rule_entities: 规则提取的实体
            ltp_entities: LTP 提取的实体

        Returns:
            融合后的实体列表
        """
        all_entities = rule_entities + ltp_entities

        # 按位置和类型去重
        seen = set()
        merged = []

        for entity in all_entities:
            key = (entity.start_pos, entity.end_pos, entity.entity_type)
            if key not in seen:
                seen.add(key)
                merged.append(entity)

        # 再次移除重叠
        return self._remove_overlapping(merged)


# 全局 NER 实例（懒加载）
_ner_instance: Optional[RuleBasedNER] = None


def get_ner_instance(use_ltp: bool = False) -> RuleBasedNER:
    """
    获取 NER 实例（单例模式）

    Args:
        use_ltp: 是否使用 LTP 增强版

    Returns:
        NER 实例
    """
    global _ner_instance

    if _ner_instance is None:
        if use_ltp:
            _ner_instance = LTPBasedNER()
        else:
            _ner_instance = RuleBasedNER()

    return _ner_instance


def extract_entities(text: str, use_ltp: bool = False) -> List[Entity]:
    """
    便捷函数：从文本中提取实体

    Args:
        text: 输入文本
        use_ltp: 是否使用 LTP

    Returns:
        实体列表
    """
    ner = get_ner_instance(use_ltp)
    return ner.extract(text)


def extract_entities_as_tuples(text: str, use_ltp: bool = False) -> List[Tuple[str, str]]:
    """
    便捷函数：提取实体为 (类型，文本) 元组列表

    Args:
        text: 输入文本
        use_ltp: 是否使用 LTP

    Returns:
        (类型，文本) 元组列表
    """
    entities = extract_entities(text, use_ltp)
    return [e.to_tuple() for e in entities]


def extract_entities_as_dict(text: str, use_ltp: bool = False) -> Dict[str, List[str]]:
    """
    便捷函数：提取实体为按类型分组的字典

    Args:
        text: 输入文本
        use_ltp: 是否使用 LTP

    Returns:
        {实体类型：[实体文本列表]}
    """
    entities = extract_entities(text, use_ltp)
    result: Dict[str, List[str]] = {}

    for entity in entities:
        type_name = entity.entity_type.value
        if type_name not in result:
            result[type_name] = []
        result[type_name].append(entity.text)

    return result


# 测试代码
if __name__ == "__main__":
    # 测试 NER 功能
    test_texts = [
        "我昨天和我朋友小明去了北京",
        "我妈妈今天很高兴，因为我要回家了",
        "他和同事在咖啡厅聊了一个下午",
        "最近工作压力很大，经常熬夜到凌晨 2 点",
        "我觉得很开心，因为见到了好久不见的朋友",
    ]

    ner = RuleBasedNER()

    for text in test_texts:
        print(f"\n原文：{text}")
        entities = ner.extract(text)
        for entity in entities:
            print(f"  [{entity.entity_type.value}] {entity.text} "
                  f"(位置：{entity.start_pos}-{entity.end_pos}, 置信度：{entity.confidence})")
