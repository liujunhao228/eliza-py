#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP 引擎工厂 - 统一创建和管理 NLP 引擎
"""

import logging
from typing import Dict, Optional, Any, List

from alice.nlp.base import (
    Segmenter,
    SyntaxAnalyzer,
    EntityRecognizer,
    SentimentAnalyzer,
    NlpResult,
)

logger = logging.getLogger(__name__)


class NlpPipeline:
    """
    NLP 处理流水线
    
    按顺序执行多个引擎，合并结果
    """
    
    def __init__(self, engines: List[Any]):
        """
        初始化流水线
        
        Args:
            engines: 引擎列表
        """
        self.engines = engines
    
    def process(self, text: str) -> NlpResult:
        """
        处理文本
        
        Args:
            text: 待处理文本
        
        Returns:
            NLP 结果
        """
        result = NlpResult(text=text)
        
        for engine in self.engines:
            try:
                if not engine.is_available:
                    continue
                
                engine_result = engine.analyze(text) if hasattr(engine, 'analyze') else None
                
                if engine_result:
                    if engine_result.tokens:
                        result.tokens = engine_result.tokens
                    if engine_result.entities:
                        result.entities.extend(engine_result.entities)
                    if engine_result.syntax:
                        result.syntax = engine_result.syntax
                    result.sentiment = engine_result.sentiment or result.sentiment
                    
            except Exception as e:
                logger.warning(f"引擎处理失败：{type(engine).__name__}, 错误：{e}")
        
        return result


class NlpFactory:
    """
    NLP 引擎工厂
    
    使用示例:
        factory = NlpFactory()
        
        # 创建单个引擎
        segmenter = factory.create_segmenter()
        syntax_analyzer = factory.create_syntax_analyzer()
        
        # 创建流水线
        pipeline = factory.create_pipeline(['jieba', 'ner', 'sentiment'])
        result = pipeline.process("今天天气真好")
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化工厂
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._cache: Dict[str, Any] = {}
    
    def create_segmenter(self) -> Segmenter:
        """创建分词器"""
        if 'segmenter' in self._cache:
            return self._cache['segmenter']
        
        from alice.nlp.engines.jieba_engine import JiebaEngine
        
        engine = JiebaEngine()
        self._cache['segmenter'] = engine
        return engine
    
    def create_syntax_analyzer(self) -> Optional[SyntaxAnalyzer]:
        """创建句法分析器"""
        if 'syntax_analyzer' in self._cache:
            return self._cache['syntax_analyzer']
        
        use_ltp = self.config.get('use_ltp', False)
        
        if not use_ltp:
            logger.info("LTP 未启用，跳过句法分析器创建")
            return None
        
        try:
            from alice.nlp.engines.ltp_engine import LtpEngine
            
            model_path = self.config.get('ltp_model_path')
            lazy_load = self.config.get('ltp_lazy_load', True)
            
            engine = LtpEngine(model_path=model_path, lazy_load=lazy_load)
            self._cache['syntax_analyzer'] = engine
            return engine
            
        except Exception as e:
            logger.warning(f"LTP 不可用：{e}")
            return None
    
    def create_entity_recognizer(
        self,
        use_ltp: bool = False,
    ) -> EntityRecognizer:
        """创建实体识别器"""
        if 'entity_recognizer' in self._cache:
            return self._cache['entity_recognizer']
        
        from alice.nlp.engines.ner_engine import NerEngine
        from alice.nlp.dictionaries.dictionary_manager import DictionaryManager
        
        dict_manager = DictionaryManager()
        ltp_engine = None
        
        if use_ltp:
            ltp_engine = self.create_syntax_analyzer()
        
        engine = NerEngine(
            use_ltp=use_ltp,
            ltp_engine=ltp_engine,
            dictionary_manager=dict_manager,
        )
        self._cache['entity_recognizer'] = engine
        return engine
    
    def create_sentiment_analyzer(self) -> SentimentAnalyzer:
        """创建情感分析器"""
        if 'sentiment_analyzer' in self._cache:
            return self._cache['sentiment_analyzer']
        
        from alice.nlp.engines.sentiment_engine import SentimentEngine
        from alice.nlp.dictionaries.dictionary_manager import DictionaryManager
        
        dict_manager = DictionaryManager()
        engine = SentimentEngine(dictionary_manager=dict_manager)
        self._cache['sentiment_analyzer'] = engine
        return engine
    
    def create_pipeline(
        self,
        components: List[str],
    ) -> NlpPipeline:
        """
        创建处理流水线
        
        Args:
            components: 组件列表
                - 'jieba': 分词
                - 'syntax': 句法分析（需要 LTP）
                - 'ner': 实体识别
                - 'sentiment': 情感分析
        
        Returns:
            NLP 流水线
        """
        engines = []
        
        for component in components:
            try:
                if component == 'jieba':
                    engines.append(self.create_segmenter())
                elif component == 'syntax':
                    analyzer = self.create_syntax_analyzer()
                    if analyzer:
                        engines.append(analyzer)
                elif component == 'ner':
                    engines.append(self.create_entity_recognizer())
                elif component == 'sentiment':
                    engines.append(self.create_sentiment_analyzer())
                else:
                    logger.warning(f"未知组件：{component}")
            except Exception as e:
                logger.warning(f"创建组件失败：{component}, 错误：{e}")
        
        return NlpPipeline(engines)
    
    def clear_cache(self):
        """清除缓存的引擎"""
        self._cache.clear()
