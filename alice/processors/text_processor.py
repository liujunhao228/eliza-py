#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本预处理器 - 只负责文本标准化
"""

import logging
import re

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """
    文本预处理器
    
    功能:
    - 文本标准化（全角转半角、标点统一）
    - 文本清洗
    
    注意:
    - 分词功能已移除
    """
    
    def __init__(self) -> None:
        """初始化"""
        # 全角转半角映射
        self.fullwidth_map = {
            chr(0xFF01 + i): chr(0x21 + i) for i in range(94)
        }
        self.fullwidth_map[" "] = " "
        
        # 中文标点映射
        self.punctuation_map = {
            "，": ",",
            "。": ".",
            "！": "!",
            "？": "?",
            "；": ";",
            "：": ":",
            "、": ",",
        }
    
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
        
        # 标点统一
        for full, half in self.punctuation_map.items():
            text = text.replace(full, half)
        
        # 去除多余空格
        text = re.sub(r"\s+", " ", text.strip())
        
        return text
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
        
        Returns:
            清洗后的文本
        """
        # 去除特殊字符（保留中文、英文、数字、基本标点）
        text = re.sub(
            r"[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：''\s]",
            "",
            text
        )
        text = re.sub(r"\s+", " ", text.strip())
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """标准化空白字符"""
        return re.sub(r"\s+", " ", text).strip()
