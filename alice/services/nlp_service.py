#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享 NLP 服务

为所有 Bot 实例提供共享的 NLP 处理能力
使用单例模式确保资源不被重复创建
"""

import logging
from typing import Any, Dict, Optional

from alice.nlp.factory import NlpFactory, NlpPipeline
from alice.nlp.base import NlpResult

logger = logging.getLogger(__name__)


class NlpService:
    """
    共享 NLP 服务（单例模式）
    
    职责:
    - 统一管理 NLP 引擎的创建和生命周期
    - 为多个 Bot 实例提供共享的 NLP 处理能力
    - 避免 LTP 等重型模型的重复加载
    """
    
    _instance: Optional['NlpService'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        enable_ltp: bool = True,
    ):
        """
        初始化 NLP 服务
        
        Args:
            config: NLP 配置字典
            enable_ltp: 是否启用 LTP
        """
        # 避免重复初始化
        if self._initialized:
            return
            
        self._config = config or {}
        self._enable_ltp = enable_ltp
        
        # 创建 NLP 工厂（单例）
        self._factory = NlpFactory(config=config)
        
        # 创建 NLP 流水线
        self._pipeline = self._create_pipeline()
        
        self._initialized = True
        logger.info("NLP 服务已初始化（单例）")
    
    def _create_pipeline(self) -> NlpPipeline:
        """创建 NLP 流水线"""
        components = []
        
        if self._enable_ltp:
            components.append('ltp')
        else:
            components.append('jieba')
        
        return self._factory.create_pipeline(components)
    
    def process(self, text: str) -> NlpResult:
        """
        处理文本
        
        Args:
            text: 待处理文本
            
        Returns:
            NLP 分析结果
        """
        return self._pipeline.process(text)
    
    def get_factory(self) -> NlpFactory:
        """获取 NLP 工厂"""
        return self._factory
    
    def get_pipeline(self) -> NlpPipeline:
        """获取 NLP 流水线"""
        return self._pipeline
    
    def is_available(self) -> bool:
        """检查 NLP 服务是否可用"""
        return self._pipeline is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled": self._initialized,
            "ltp_enabled": self._enable_ltp,
            "pipeline_available": self._pipeline is not None,
        }
    
    @classmethod
    def get_instance(
        cls,
        config: Optional[Dict[str, Any]] = None,
        enable_ltp: bool = True,
    ) -> 'NlpService':
        """
        获取 NLP 服务单例实例
        
        Args:
            config: NLP 配置
            enable_ltp: 是否启用 LTP
            
        Returns:
            NLP 服务实例
        """
        if cls._instance is None or not cls._instance._initialized:
            cls._instance = cls(config=config, enable_ltp=enable_ltp)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（用于测试）"""
        if cls._instance is not None:
            cls._instance._initialized = False
        cls._instance = None


# 便捷函数
def get_nlp_service(config: Optional[Dict[str, Any]] = None, enable_ltp: bool = True) -> NlpService:
    """获取 NLP 服务单例"""
    return NlpService.get_instance(config=config, enable_ltp=enable_ltp)
