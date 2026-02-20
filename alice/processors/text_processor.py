#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本预处理器模块

负责文本的标准化和分词处理。
"""

import logging
import re
from typing import Dict, List

from alice.utils.degradation_monitor import degradation_monitor
from alice.utils.sanitizer import sanitize_text

logger = logging.getLogger(__name__)

# 尝试导入 jieba
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，将使用基础分词模式")


class TextPreprocessor:
    """
    文本预处理器

    功能:
    - 文本标准化（全角转半角、标点统一）
    - 中文分词
    - 文本清洗
    """

    def __init__(self) -> None:
        """初始化文本预处理器"""
        # 中文标点符号映射（全角转半角）
        self.punctuation_map: Dict[str, str] = {
            "，": ",",
            "。": ".",
            "！": "!",
            "？": "?",
            "；": ";",
            "：": ":",
            '"': '"',
            "'": "'",
            "、": ",",
            "「": '"',
            "」": '"',
            "『": '"',
            "』": '"',
        }

        # 全角转半角映射
        self.fullwidth_map: Dict[str, str] = {
            chr(0xFF01 + i): chr(0x21 + i) for i in range(94)
        }
        self.fullwidth_map[" "] = " "
        self.fullwidth_map["。"] = "."

    def standardize_text(self, text: str) -> str:
        """
        文本标准化

        Args:
            text: 原始文本

        Returns:
            标准化后的文本
        """
        # 全角转半角
        for full, half in self.fullwidth_map.items():
            text = text.replace(full, half)

        # 统一标点符号
        for full, half in self.punctuation_map.items():
            text = text.replace(full, half)

        # 去除多余空格
        text = re.sub(r"\s+", " ", text.strip())

        return text

    def segment_text(self, text: str) -> List[str]:
        """
        中文分词

        Args:
            text: 待分词的文本

        Returns:
            分词结果列表
        """
        if JIEBA_AVAILABLE:
            try:
                return list(jieba.cut(text))
            except Exception as e:
                # 使用结构化日志和脱敏处理
                logger.warning(
                    "jieba 分词失败，降级到基础分词模式",
                    extra={
                        'component': 'text_processor',
                        'error_type': type(e).__name__,
                        'input_length': len(text),
                        'input_preview': sanitize_text(text[:50]),
                    },
                    exc_info=True,
                )
                degradation_monitor.register_degradation(
                    component='text_processor',
                    reason=f'jieba 分词异常：{type(e).__name__}',
                    severity=2,
                    recovery_plan='检查 jieba 库状态或重启服务',
                    original_functionality='基于 jieba 的智能中文分词',
                    degraded_functionality='基于字符的基础分词',
                    user_notification='使用简化分词模式'
                )
                # 降级到基础分词
                return list(text)
        else:
            # 基础分词：按字符分割
            logger.warning(
                "使用基础分词模式（按字符）",
                extra={
                    'component': 'text_processor',
                    'fallback_reason': 'jieba 未安装',
                }
            )
            degradation_monitor.register_degradation(
                component='text_processor',
                reason='jieba 未安装',
                severity=1,
                recovery_plan='安装 jieba: pip install jieba',
                original_functionality='基于 jieba 的智能中文分词',
                degraded_functionality='基于字符的基础分词',
                user_notification='使用简化分词模式'
            )
            return list(text)

    def clean_text(self, text: str) -> str:
        """
        清洗文本（去除特殊字符、多余空格等）

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 去除特殊字符（保留中文、英文、数字、基本标点）
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：''\s]", "", text)

        # 去除多余空格
        text = re.sub(r"\s+", " ", text.strip())

        return text

    def normalize_whitespace(self, text: str) -> str:
        """
        标准化空白字符

        Args:
            text: 原始文本

        Returns:
            标准化后的文本
        """
        # 将所有空白字符替换为单个空格
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def remove_punctuation(self, text: str) -> str:
        """
        去除标点符号

        Args:
            text: 原始文本

        Returns:
            无标点文本
        """
        # 去除中英文标点
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", "", text)
        return text.strip()
