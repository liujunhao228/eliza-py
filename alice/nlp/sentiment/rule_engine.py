#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则词典情感分析器 - 轻量级实现

基于情感词典和规则进行情感分析：
- 快速响应，不依赖外部模型
- 支持程度副词、否定词处理
- 支持细粒度情感分类
"""

import logging
import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

from alice.nlp.sentiment.base import SentimentEngine, SentimentResult, SentimentLabel
from alice.processors.text_processor import TextPreprocessor

logger = logging.getLogger(__name__)


class RuleSentimentEngine(SentimentEngine):
    """
    规则词典情感分析引擎

    特性:
    - 基于情感词典和规则
    - 支持程度副词加权
    - 支持否定词反转
    - 支持细粒度情感分类（喜、怒、哀、惧等）
    """

    # 正面情感词库
    POSITIVE_WORDS: Set[str] = {
        # 基本正面词
        "好", "棒", "优", "美", "善", "佳", "妙",
        "喜欢", "爱", "爱慕", "喜爱", "热爱",
        "开心", "快乐", "高兴", "愉快", "欢乐", "喜悦",
        "幸福", "满足", "满意", "欣慰", "自豪",
        "兴奋", "激动", "激动", "振奋", "鼓舞",
        "轻松", "安心", "踏实", "温暖", "温馨",
        "成功", "优秀", "出色", "完美", "精彩",
        "感谢", "感激", "感动", "温柔", "善良",
        "希望", "期待", "渴望", "向往", "乐观",
        "自信", "勇敢", "坚强", "聪明", "智慧",
        "顺利", "如意", "吉祥", "美好", "和谐",
        # 添加单字情感词以适配基础分词模式
        "乐", "喜", "欢", "兴", "奋", "愉", "悦",
        "福", "满", "安", "成", "优", "秀", "精", "彩",
        "感", "谢", "温", "暖", "希", "望", "自", "信",
        "勇", "敢", "坚", "强", "聪", "明", "智", "慧",
        "顺", "利", "吉", "祥", "美", "好", "和", "谐",
    }

    # 负面情感词库
    NEGATIVE_WORDS: Set[str] = {
        # 基本负面词
        "坏", "差", "劣", "丑", "恶", "糟", "烂",
        "讨厌", "恨", "厌恶", "嫌弃", "反感",
        "难过", "伤心", "悲伤", "悲痛", "痛苦",
        "生气", "愤怒", "恼火", "烦躁", "郁闷",
        "焦虑", "紧张", "害怕", "恐惧", "惊慌",
        "失望", "绝望", "沮丧", "颓废", "消沉",
        "累", "疲惫", "疲倦", "困", "烦", "烦恼",
        "压力", "压抑", "委屈", "孤独", "寂寞",
        "失败", "糟糕", "错误", "问题", "麻烦",
        "讨厌", "可恶", "可恨", "恶心", "肮脏",
        "后悔", "遗憾", "抱歉", "抱歉", "内疚",
        "危险", "威胁", "伤害", "损失", "灾难",
        # 添加单字负面情感词
        "坏", "差", "劣", "丑", "恶", "糟", "烂",
        "厌", "恨", "难", "伤", "悲", "痛", "苦",
        "气", "怒", "恼", "焦", "紧", "怕", "恐",
        "失", "绝", "沮", "颓", "消", "累", "压",
        "危", "险", "威", "胁", "伤", "害", "损",
    }

    # 程度副词（用于加权）
    DEGREE_ADVERBS: Dict[str, float] = {
        # 极度
        "非常": 2.0, "极其": 2.0, "格外": 2.0, "分外": 2.0,
        "特别": 2.0, "十分": 2.0, "相当": 2.0,
        "太": 1.8, "真": 1.8, "好": 1.5, "挺": 1.5,
        # 中度
        "比较": 1.3, "较为": 1.3, "有点": 0.8, "有些": 0.8,
        "略微": 0.6, "稍微": 0.6, "稍稍": 0.6,
        # 不足
        "不够": 0.5, "不太": 0.5, "不算": 0.5,
    }

    # 否定词
    NEGATION_WORDS: Set[str] = {
        "不", "没", "没有", "别", "勿", "莫", "非", "无", "未", "甭",
    }

    # 情感类别映射（细粒度情感）
    EMOTION_CATEGORIES: Dict[str, str] = {
        # 喜悦
        "开心": "joy", "快乐": "joy", "高兴": "joy", "愉快": "joy",
        "欢喜": "joy", "喜悦": "joy", "兴奋": "joy", "激动": "joy",
        "幸福": "joy", "满足": "joy", "满意": "joy", "欣慰": "joy",
        # 愤怒
        "生气": "anger", "愤怒": "anger", "恼火": "anger",
        "烦躁": "anger", "郁闷": "anger", "恼怒": "anger",
        # 悲伤
        "难过": "sadness", "伤心": "sadness", "悲伤": "sadness",
        "悲痛": "sadness", "痛苦": "sadness", "沮丧": "sadness",
        "失望": "sadness", "绝望": "sadness", "委屈": "sadness",
        # 恐惧
        "害怕": "fear", "恐惧": "fear", "紧张": "fear",
        "惊慌": "fear", "恐慌": "fear", "担忧": "fear",
        # 焦虑
        "焦虑": "anxiety", "担心": "anxiety", "不安": "anxiety",
        "忧虑": "anxiety", "压力": "anxiety",
        # 厌恶
        "讨厌": "disgust", "厌恶": "disgust", "嫌弃": "disgust",
        "恶心": "disgust", "反感": "disgust",
        # 惊讶
        "惊讶": "surprise", "吃惊": "surprise", "震惊": "surprise",
        "意外": "surprise",
    }

    def __init__(self, custom_positive: Optional[Set[str]] = None,
                 custom_negative: Optional[Set[str]] = None):
        """
        初始化规则情感分析引擎

        Args:
            custom_positive: 自定义正面词库
            custom_negative: 自定义负面词库
        """
        self.preprocessor = TextPreprocessor()

        # 合并自定义词库
        self.positive_words = set(self.POSITIVE_WORDS)
        self.negative_words = set(self.NEGATIVE_WORDS)

        if custom_positive:
            self.positive_words.update(custom_positive)
        if custom_negative:
            self.negative_words.update(custom_negative)

        # 构建正则模式
        self._build_patterns()

    def _build_patterns(self) -> None:
        """构建匹配模式"""
        # 程度副词模式
        self.degree_pattern = re.compile(
            r'(' + '|'.join(re.escape(k) for k in self.DEGREE_ADVERBS.keys()) + r')'
        )

        # 否定词模式
        self.negation_pattern = re.compile(
            r'(' + '|'.join(re.escape(w) for w in self.NEGATION_WORDS) + r')'
        )

        # 情感词模式
        all_emotion_words = self.positive_words | self.negative_words
        sorted_words = sorted(all_emotion_words, key=len, reverse=True)
        self.emotion_pattern = re.compile(
            r'(' + '|'.join(re.escape(w) for w in sorted_words) + r')'
        )

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return True

    def analyze(self, text: str) -> SentimentResult:
        """
        分析文本情感

        Args:
            text: 待分析文本

        Returns:
            情感分析结果
        """
        # 文本预处理
        standardized_text = self.preprocessor.standardize_text(text)
        words = self.preprocessor.segment_text(standardized_text)

        # 基础情感分析
        base_score, keywords = self._analyze_base_sentiment(words)

        # 程度副词加权
        degree_score = self._analyze_degree_adverbs(standardized_text, base_score)

        # 否定词处理
        final_score = self._analyze_negation(standardized_text, degree_score)

        # 细粒度情感分析
        emotions = self._analyze_emotions(keywords)

        # 计算置信度
        confidence = self._calculate_confidence(keywords, len(words))

        # 确定情感标签
        label = SentimentResult.score_to_label(final_score)

        return SentimentResult(
            text=text,
            score=final_score,
            label=label,
            confidence=confidence,
            emotions=emotions,
            keywords=keywords,
            metadata={
                'base_score': base_score,
                'degree_score': degree_score,
                'word_count': len(words),
            }
        )

    def _analyze_base_sentiment(
        self,
        words: List[str],
    ) -> Tuple[float, List[str]]:
        """
        分析基础情感分数

        Args:
            words: 分词结果

        Returns:
            (基础分数，情感关键词列表)
        """
        pos_count = 0
        neg_count = 0
        keywords = []

        for word in words:
            if word in self.positive_words:
                pos_count += 1
                keywords.append(word)
            elif word in self.negative_words:
                neg_count += 1
                keywords.append(word)

        total = pos_count + neg_count
        if total == 0:
            return 0.0, []

        # 计算基础分数 (-1.0 到 1.0)
        score = (pos_count - neg_count) / total
        return score, keywords

    def _analyze_degree_adverbs(
        self,
        text: str,
        base_score: float,
    ) -> float:
        """
        分析程度副词加权

        Args:
            text: 文本
            base_score: 基础情感分数

        Returns:
            加权后的情感分数（限制在 -1.0 到 1.0 范围内）
        """
        if base_score == 0:
            return 0.0

        # 找到最大的程度副词权重
        max_multiplier = 1.0
        
        # 按长度排序，优先匹配长词
        sorted_adverbs = sorted(self.DEGREE_ADVERBS.keys(), key=len, reverse=True)
        
        for adverb in sorted_adverbs:
            if adverb in text:
                multiplier = self.DEGREE_ADVERBS[adverb]
                max_multiplier = max(max_multiplier, multiplier)

        # 应用加权，但限制在 [-1.0, 1.0] 范围内
        weighted_score = base_score * max_multiplier
        return max(-1.0, min(1.0, weighted_score))

    def _analyze_negation(
        self,
        text: str,
        score: float,
    ) -> float:
        """
        分析否定词

        Args:
            text: 文本
            score: 当前情感分数

        Returns:
            否定后的情感分数
        """
        # 检查是否有否定词（排除程度副词中的否定成分）
        # 先移除程度副词再检查否定词
        cleaned_text = text
        
        # 移除程度副词以避免误判
        for adverb in self.DEGREE_ADVERBS.keys():
            cleaned_text = cleaned_text.replace(adverb, "")
        
        # 检查剩余文本中是否有否定词
        has_negation = bool(self.negation_pattern.search(cleaned_text))

        if has_negation:
            # 否定词反转情感极性
            # 注意：这里使用简化的反转逻辑
            # 实际应用中需要更复杂的上下文分析
            if abs(score) > 0.3:  # 只有情感较强时才反转
                return -score * 0.8  # 反转并减弱

        return score

    def _analyze_emotions(
        self,
        keywords: List[str],
    ) -> Dict[str, float]:
        """
        分析细粒度情感

        Args:
            keywords: 情感关键词

        Returns:
            情感强度字典
        """
        emotions: Dict[str, float] = {}

        for keyword in keywords:
            emotion_type = self.EMOTION_CATEGORIES.get(keyword)
            if emotion_type:
                emotions[emotion_type] = emotions.get(emotion_type, 0) + 1

        # 归一化
        total = sum(emotions.values())
        if total > 0:
            for emotion in emotions:
                emotions[emotion] /= total

        return emotions

    def _calculate_confidence(
        self,
        keywords: List[str],
        total_words: int,
    ) -> float:
        """
        计算置信度

        Args:
            keywords: 情感关键词
            total_words: 总词数

        Returns:
            置信度 (0.0 到 1.0)
        """
        if not keywords:
            return 0.5

        # 基于关键词密度计算置信度
        density = len(keywords) / max(total_words, 1)

        # 基础置信度 + 密度奖励
        base_confidence = 0.6
        density_bonus = min(density * 2, 0.4)

        return min(base_confidence + density_bonus, 1.0)

    def get_label(self, score: float) -> SentimentLabel:
        """
        获取情感标签

        Args:
            score: 情感分数

        Returns:
            情感标签
        """
        return SentimentResult.score_to_label(score)

    def get_dominant_emotion(
        self,
        emotions: Dict[str, float],
    ) -> Optional[str]:
        """
        获取主导情感

        Args:
            emotions: 情感强度字典

        Returns:
            主导情感类型
        """
        if not emotions:
            return None

        return max(emotions, key=emotions.get)

    def add_positive_words(self, words: Set[str]) -> None:
        """添加正面情感词"""
        self.positive_words.update(words)
        self._build_patterns()

    def add_negative_words(self, words: Set[str]) -> None:
        """添加负面情感词"""
        self.negative_words.update(words)
        self._build_patterns()

    def get_intensity(self, result: SentimentResult) -> str:
        """
        获取情感强度（考虑程度副词）

        Args:
            result: 情感分析结果

        Returns:
            强度描述
        """
        # 直接在原始文本中查找程度副词
        text = result.text
        
        # 按长度排序，优先匹配长词
        sorted_adverbs = sorted(self.DEGREE_ADVERBS.keys(), key=len, reverse=True)
        
        max_multiplier = 1.0
        for adverb in sorted_adverbs:
            if adverb in text:
                multiplier = self.DEGREE_ADVERBS[adverb]
                max_multiplier = max(max_multiplier, multiplier)
                break  # 找到第一个匹配的就停止（因为已按长度排序）
        
        if max_multiplier >= 1.8:
            return "strong"
        elif max_multiplier >= 1.3:
            return "moderate"
        else:
            return "weak"

    def get_emotion_description(self, result: SentimentResult) -> str:
        """
        获取情感描述

        Args:
            result: 情感分析结果

        Returns:
            情感描述字符串
        """
        if result.label == SentimentLabel.NEUTRAL:
            return "中性"

        intensity = self.get_intensity(result)
        intensity_map = {
            "strong": "非常",
            "moderate": "比较",
            "weak": "有点",
        }

        intensity_str = intensity_map.get(intensity, "有点")

        if result.emotions:
            dominant = self.get_dominant_emotion(result.emotions)
            emotion_map = {
                "joy": "开心",
                "anger": "生气",
                "sadness": "难过",
                "fear": "害怕",
                "anxiety": "焦虑",
                "disgust": "讨厌",
                "surprise": "惊讶",
            }
            emotion_str = emotion_map.get(dominant, "")
            if emotion_str:
                return f"{intensity_str}{emotion_str}"

        label_map = {
            SentimentLabel.POSITIVE: "正面",
            SentimentLabel.NEGATIVE: "负面",
        }
        return f"{intensity_str}{label_map.get(result.label, '中性')}"
