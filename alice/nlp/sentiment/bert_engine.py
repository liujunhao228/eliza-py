#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BERT 情感分析器 - 深度学习模型实现

基于 transformers 库的中文 BERT 模型进行情感分析：
- 使用中文情感分析预训练模型
- 支持懒加载，按需加载模型
- 支持智能降级处理
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from alice.nlp.sentiment.base import SentimentEngine, SentimentResult, SentimentLabel
from alice.utils.degradation_monitor import degradation_monitor

logger = logging.getLogger(__name__)

# 尝试导入 transformers
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.info("未安装 transformers，BERT 情感分析器不可用")


# 中文情感分析模型配置
CHINESE_SENTIMENT_MODELS = {
    # 百度 ERNIE 情感分析模型
    "ernie": "nghuyong/ernie-3.0-base-zh",
    # 哈工大 BERT 情感分析模型
    "bert": "bert-base-chinese",
    # 中文情感分析专用模型（如果可用）
    "sentiment": "uer/roberta-base-finetuned-jd-binary-chinese",
}

# 默认模型
DEFAULT_MODEL = "sentiment"


class BertSentimentEngine(SentimentEngine):
    """
    BERT 情感分析引擎

    特性:
    - 基于预训练中文 BERT 模型
    - 支持懒加载
    - 支持智能降级
    - 高精度情感分析
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        model_path: Optional[str] = None,
        lazy_load: bool = True,
        device: Optional[str] = None,
    ):
        """
        初始化 BERT 情感分析引擎

        Args:
            model_name: 模型名称
            model_path: 模型路径，None 则使用默认
            lazy_load: 是否懒加载
            device: 推理设备，None 则自动选择
        """
        self._model_name = model_name
        self._model_path = model_path or model_name
        self._lazy_load = lazy_load

        # 设备选择
        if device:
            self._device = device
        else:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"

        self._tokenizer: Optional[AutoTokenizer] = None
        self._model: Optional[AutoModelForSequenceClassification] = None
        self._initialized = False

        # 情感标签映射（根据具体模型调整）
        self.label_map = {
            0: SentimentLabel.NEGATIVE,
            1: SentimentLabel.POSITIVE,
        }

        if not lazy_load:
            self._initialize()

    def _initialize(self) -> bool:
        """
        初始化模型

        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True

        if not TRANSFORMERS_AVAILABLE:
            logger.warning("transformers 库未安装，无法初始化 BERT 情感分析器")
            return False

        try:
            logger.info(f"正在加载 BERT 情感分析模型：{self._model_path}")

            # 加载分词器
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_path)

            # 加载模型
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self._model_path,
                num_labels=2,  # 二分类：正面/负面
            )
            self._model.to(self._device)
            self._model.eval()

            self._initialized = True
            logger.info(f"BERT 情感分析模型加载成功，设备：{self._device}")
            return True

        except Exception as e:
            logger.error(f"BERT 模型加载失败：{e}")
            self._tokenizer = None
            self._model = None
            return False

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        if not TRANSFORMERS_AVAILABLE:
            return False
        if self._lazy_load and not self._initialized:
            return True  # 懒加载模式下，认为可用
        return self._model is not None

    def _ensure_initialized(self) -> bool:
        """确保模型已初始化"""
        if self._initialized:
            return self._model is not None
        return self._initialize()

    def analyze(self, text: str) -> SentimentResult:
        """
        分析文本情感

        Args:
            text: 待分析文本

        Returns:
            情感分析结果
        """
        # 检查 transformers 是否可用
        if not TRANSFORMERS_AVAILABLE:
            degradation_monitor.register_degradation(
                component='bert_sentiment',
                reason='transformers 库未安装',
                severity=2,
                recovery_plan='安装 transformers 库：pip install transformers torch'
            )
            return self._fallback_analyze(text)

        # 确保模型已初始化
        if not self._ensure_initialized():
            degradation_monitor.register_degradation(
                component='bert_sentiment',
                reason='BERT 模型初始化失败',
                severity=3,
                recovery_plan='检查模型路径或网络连接'
            )
            return self._fallback_analyze(text)

        try:
            # 分词
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # 推理
            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits

            # 计算概率
            probs = torch.softmax(logits, dim=-1)[0]

            # 获取预测结果
            pred_label = torch.argmax(logits).item()
            pred_score = probs[pred_label].item()

            # 转换为统一的情感分数 (-1.0 到 1.0)
            if pred_label == 1:  # 正面
                score = pred_score
            else:  # 负面
                score = -pred_score

            # 确定情感标签
            label = self.label_map.get(pred_label, SentimentLabel.NEUTRAL)

            return SentimentResult(
                text=text,
                score=score,
                label=label,
                confidence=pred_score,
                metadata={
                    'model': self._model_name,
                    'raw_probs': probs.cpu().tolist(),
                }
            )

        except Exception as e:
            logger.warning(f"BERT 情感分析失败，降级处理：{e}")
            degradation_monitor.register_degradation(
                component='bert_sentiment_inference',
                reason=f'BERT 推理异常：{type(e).__name__}',
                severity=2,
                recovery_plan='检查输入文本格式或重启服务'
            )
            return self._fallback_analyze(text)

    def _fallback_analyze(self, text: str) -> SentimentResult:
        """
        降级分析方案

        Args:
            text: 待分析文本

        Returns:
            情感分析结果（中性）
        """
        return SentimentResult(
            text=text,
            score=0.0,
            label=SentimentLabel.NEUTRAL,
            confidence=0.5,
            metadata={'fallback': True, 'reason': 'BERT 模型不可用'},
        )

    def get_label(self, score: float) -> SentimentLabel:
        """
        获取情感标签

        Args:
            score: 情感分数

        Returns:
            情感标签
        """
        return SentimentResult.score_to_label(score)

    def analyze_with_confidence_threshold(
        self,
        text: str,
        threshold: float = 0.7,
    ) -> Optional[SentimentResult]:
        """
        带置信度阈值的情感分析

        Args:
            text: 待分析文本
            threshold: 置信度阈值

        Returns:
            情感分析结果，如果置信度低于阈值则返回 None
        """
        result = self.analyze(text)
        if result.confidence < threshold:
            return None
        return result

    def get_probability_distribution(self, text: str) -> Optional[Dict[str, float]]:
        """
        获取概率分布

        Args:
            text: 待分析文本

        Returns:
            概率分布字典
        """
        if not self.is_available:
            return None

        if not self._ensure_initialized():
            return None

        try:
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0]

            return {
                'negative': probs[0].item(),
                'positive': probs[1].item(),
            }

        except Exception as e:
            logger.error(f"获取概率分布失败：{e}")
            return None

    def batch_analyze(
        self,
        texts: List[str],
        batch_size: int = 8,
    ) -> List[SentimentResult]:
        """
        批量分析文本

        Args:
            texts: 待分析文本列表
            batch_size: 批次大小

        Returns:
            情感分析结果列表
        """
        if not self.is_available:
            return [self._fallback_analyze(text) for text in texts]

        if not self._ensure_initialized():
            return [self._fallback_analyze(text) for text in texts]

        results = []

        try:
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]

                # 批量分词
                inputs = self._tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    truncation=True,
                    padding=True,
                    max_length=512,
                )
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

                # 批量推理
                with torch.no_grad():
                    outputs = self._model(**inputs)
                    logits = outputs.logits
                    probs = torch.softmax(logits, dim=-1)

                # 处理结果
                for j, (text, prob) in enumerate(zip(batch_texts, probs)):
                    pred_label = torch.argmax(prob).item()
                    pred_score = prob[pred_label].item()

                    if pred_label == 1:
                        score = pred_score
                        label = SentimentLabel.POSITIVE
                    else:
                        score = -pred_score
                        label = SentimentLabel.NEGATIVE

                    results.append(SentimentResult(
                        text=text,
                        score=score,
                        label=label,
                        confidence=pred_score,
                    ))

        except Exception as e:
            logger.error(f"批量分析失败：{e}")
            # 降级处理
            results = [self._fallback_analyze(text) for text in texts]

        return results

    def cleanup(self) -> None:
        """清理模型资源"""
        if self._model:
            del self._model
            self._model = None
        if self._tokenizer:
            del self._tokenizer
            self._tokenizer = None
        self._initialized = False

        # 清理 CUDA 缓存
        if self._device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("BERT 情感分析模型已清理")
