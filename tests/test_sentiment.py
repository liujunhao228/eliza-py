#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情感分析模块单元测试

测试覆盖：
- 规则词典情感分析器
- 情感分析结果数据类
- 情感标签转换
- 情感强度计算
"""

import pytest
from alice.nlp.sentiment import (
    SentimentResult,
    SentimentLabel,
    RuleSentimentEngine,
    create_sentiment_engine,
)


class TestSentimentLabel:
    """测试情感标签枚举"""

    def test_label_values(self):
        """测试标签值"""
        assert SentimentLabel.POSITIVE.value == "positive"
        assert SentimentLabel.NEGATIVE.value == "negative"
        assert SentimentLabel.NEUTRAL.value == "neutral"
        assert SentimentLabel.MIXED.value == "mixed"


class TestSentimentResult:
    """测试情感分析结果数据类"""

    def test_score_to_label_positive(self):
        """测试正面分数转换"""
        assert SentimentResult.score_to_label(0.5) == SentimentLabel.POSITIVE
        assert SentimentResult.score_to_label(0.8) == SentimentLabel.POSITIVE
        assert SentimentResult.score_to_label(0.21) == SentimentLabel.POSITIVE

    def test_score_to_label_negative(self):
        """测试负面分数转换"""
        assert SentimentResult.score_to_label(-0.5) == SentimentLabel.NEGATIVE
        assert SentimentResult.score_to_label(-0.8) == SentimentLabel.NEGATIVE
        assert SentimentResult.score_to_label(-0.21) == SentimentLabel.NEGATIVE

    def test_score_to_label_neutral(self):
        """测试中性分数转换"""
        assert SentimentResult.score_to_label(0.0) == SentimentLabel.NEUTRAL
        assert SentimentResult.score_to_label(0.05) == SentimentLabel.NEUTRAL
        assert SentimentResult.score_to_label(-0.05) == SentimentLabel.NEUTRAL

    def test_score_to_label_mixed(self):
        """测试混合分数转换"""
        assert SentimentResult.score_to_label(0.1) == SentimentLabel.MIXED
        assert SentimentResult.score_to_label(-0.1) == SentimentLabel.MIXED

    def test_to_dict(self):
        """测试转换为字典"""
        result = SentimentResult(
            text="测试文本",
            score=0.8,
            label=SentimentLabel.POSITIVE,
            confidence=0.9,
        )
        result_dict = result.to_dict()

        assert result_dict["text"] == "测试文本"
        assert result_dict["score"] == 0.8
        assert result_dict["label"] == "positive"
        assert result_dict["confidence"] == 0.9


class TestRuleSentimentEngine:
    """测试规则词典情感分析引擎"""

    @pytest.fixture
    def engine(self):
        """创建测试引擎"""
        return RuleSentimentEngine()

    def test_engine_available(self, engine):
        """测试引擎可用性"""
        assert engine.is_available is True

    def test_analyze_positive(self, engine):
        """测试正面情感分析"""
        result = engine.analyze("我很开心")
        
        assert result.text == "我很开心"
        assert result.score > 0
        assert result.label == SentimentLabel.POSITIVE
        assert "开心" in result.keywords

    def test_analyze_negative(self, engine):
        """测试负面情感分析"""
        result = engine.analyze("我很难过")
        
        assert result.text == "我很难过"
        assert result.score < 0
        assert result.label == SentimentLabel.NEGATIVE
        assert "难过" in result.keywords

    def test_analyze_neutral(self, engine):
        """测试中性情感分析"""
        result = engine.analyze("今天天气不错")
        
        assert result.text == "今天天气不错"
        # 中性或轻微正面
        assert -0.2 <= result.score <= 0.2

    def test_analyze_mixed(self, engine):
        """测试混合情感分析"""
        result = engine.analyze("我又开心又难过")
        
        assert result.text == "我又开心又难过"
        # 混合情感，分数接近 0
        assert -0.2 <= result.score <= 0.2
        assert "开心" in result.keywords
        assert "难过" in result.keywords

    def test_analyze_with_degree_adverb(self, engine):
        """测试程度副词加权"""
        result_normal = engine.analyze("开心")
        result_strong = engine.analyze("我非常开心")
        
        # 有程度副词时分数应该更高或相等（因为分数限制在 [-1, 1]）
        # 注意：由于分数限制，可能两者都是 1.0，但 metadata 中应该有程度副词信息
        assert result_strong.score >= result_normal.score
        # 检查 metadata 中是否有程度副词加权信息
        assert result_strong.metadata.get('degree_score', 0) >= result_normal.metadata.get('degree_score', 0)

    def test_analyze_with_emotions(self, engine):
        """测试细粒度情感分析"""
        result = engine.analyze("我很愤怒")
        
        assert result.emotions is not None
        assert "anger" in result.emotions

    def test_get_label(self, engine):
        """测试获取情感标签"""
        assert engine.get_label(0.5) == SentimentLabel.POSITIVE
        assert engine.get_label(-0.5) == SentimentLabel.NEGATIVE
        assert engine.get_label(0.0) == SentimentLabel.NEUTRAL

    def test_get_intensity(self, engine):
        """测试获取情感强度"""
        # 测试有程度副词的情况
        strong_result = engine.analyze("我非常开心")
        moderate_result = engine.analyze("比较开心")
        weak_result = engine.analyze("有点开心")
        
        assert engine.get_intensity(strong_result) == "strong"
        assert engine.get_intensity(moderate_result) in ["moderate", "weak"]
        assert engine.get_intensity(weak_result) == "weak"

    def test_is_positive(self, engine):
        """测试正面判断"""
        result = engine.analyze("我很高兴")
        assert engine.is_positive(result) is True
        assert engine.is_negative(result) is False

    def test_is_negative(self, engine):
        """测试负面判断"""
        result = engine.analyze("我很生气")
        assert engine.is_negative(result) is True
        assert engine.is_positive(result) is False

    def test_add_positive_words(self, engine):
        """测试添加正面词"""
        # 添加一个单字词，确保在字符级别分词时也能被识别
        engine.add_positive_words({"棒"})
        result = engine.analyze("棒")
        assert result.score > 0
        assert "棒" in result.keywords

    def test_add_negative_words(self, engine):
        """测试添加负面词"""
        # 添加一个单字词，确保在字符级别分词时也能被识别
        engine.add_negative_words({"糟"})
        result = engine.analyze("糟")
        assert result.score < 0
        assert "糟" in result.keywords


class TestSentimentEngineFactory:
    """测试情感分析引擎工厂"""

    def test_create_rule_engine(self):
        """测试创建规则引擎"""
        engine = create_sentiment_engine(mode='rule')
        assert isinstance(engine, RuleSentimentEngine)
        assert engine.is_available is True

    def test_create_auto_engine(self):
        """测试创建自动引擎"""
        engine = create_sentiment_engine(mode='auto')
        assert engine.is_available is True

    def test_create_hybrid_engine(self):
        """测试创建混合引擎"""
        from alice.nlp.sentiment import HybridSentimentEngine
        
        engine = create_sentiment_engine(mode='hybrid', engines=['rule'])
        assert isinstance(engine, HybridSentimentEngine)
        assert engine.is_available is True


class TestSentimentIntegration:
    """测试情感分析集成"""

    def test_full_pipeline_positive(self):
        """测试完整正面情感分析流程"""
        engine = create_sentiment_engine(mode='rule')

        test_cases = [
            "开心",
            "高兴",
            "美好",
        ]

        for text in test_cases:
            result = engine.analyze(text)
            assert result.label == SentimentLabel.POSITIVE, f"Failed for: {text}"

    def test_full_pipeline_negative(self):
        """测试完整负面情感分析流程"""
        engine = create_sentiment_engine(mode='rule')
        
        test_cases = [
            "我今天很难过",
            "我很生气",
            "生活真痛苦",
        ]
        
        for text in test_cases:
            result = engine.analyze(text)
            assert result.label == SentimentLabel.NEGATIVE, f"Failed for: {text}"

    def test_emotion_detection(self):
        """测试情感类型检测"""
        engine = create_sentiment_engine(mode='rule')
        
        # 测试喜悦
        result = engine.analyze("我很快乐")
        assert "joy" in result.emotions
        
        # 测试愤怒
        result = engine.analyze("我很愤怒")
        assert "anger" in result.emotions
        
        # 测试悲伤
        result = engine.analyze("我很悲伤")
        assert "sadness" in result.emotions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
