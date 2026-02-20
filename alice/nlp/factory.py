#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP 引擎工厂 - 统一创建和管理 NLP 引擎

分词策略:
- 仅使用分词功能时：使用 jieba
- 使用高级功能（句法分析、命名实体识别）时：使用 LTP（分词也顺便用 LTP 来做）

增强功能:
- 支持 LTP 完整配置（device、batch_size、max_length 等）
- 支持 SRL（语义角色标注）和 SDP（语义依存分析）
- 支持 LtpFullResult 完整结果类型
"""

import logging
from typing import Dict, Optional, Any, List

from alice.nlp.base import (
    Segmenter,
    SyntaxAnalyzer,
    EntityRecognizer,
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

            except Exception as e:
                logger.warning(f"引擎处理失败：{type(engine).__name__}, 错误：{e}")

        return result


class NlpFactory:
    """
    NLP 引擎工厂

    分词策略:
    - 仅使用分词功能时：使用 jieba
    - 使用高级功能（句法分析、命名实体识别）时：使用 LTP（分词也顺便用 LTP 来做）

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
                - use_ltp_for_advanced: 是否对高级功能使用 LTP（默认 False）
                - ltp_model_path: LTP 模型路径
                - ltp_lazy_load: LTP 懒加载（默认 True）
                - ltp_device: LTP 运行设备（'cpu', 'cuda', 'cuda:0' 等），None 自动选择
                - ltp_batch_size: LTP 批处理大小（默认 32）
                - ltp_max_length: LTP 最大序列长度（默认 512）
                - ltp_enable_srl: 是否启用语义角色标注（默认 False）
                - ltp_enable_sdp: 是否启用语义依存分析（默认 False）
        """
        self.config = config or {}
        self._cache: Dict[str, Any] = {}

    def create_segmenter(self, use_ltp: bool = False) -> Segmenter:
        """
        创建分词器

        Args:
            use_ltp: 是否使用 LTP 进行分词（仅当需要高级功能时设为 True）

        Returns:
            分词器
        """
        cache_key = 'segmenter_ltp' if use_ltp else 'segmenter_jieba'
        if cache_key in self._cache:
            return self._cache[cache_key]

        if use_ltp:
            # 使用 LTP 分词
            from alice.nlp.engines.ltp_engine import LtpEngine
            engine = self._create_ltp_engine()
        else:
            # 使用 jieba 分词
            from alice.nlp.engines.jieba_engine import JiebaEngine
            engine = JiebaEngine()

        self._cache[cache_key] = engine
        return engine

    def _create_ltp_engine(self, **kwargs) -> Any:
        """
        创建 LTP 引擎（内部方法，统一配置处理）

        Args:
            **kwargs: 额外配置参数

        Returns:
            LtpEngine 实例
        """
        from alice.nlp.engines.ltp_engine import LtpEngine

        model_path = self.config.get('ltp_model_path')
        device = self.config.get('ltp_device')
        batch_size = self.config.get('ltp_batch_size', 32)
        max_length = self.config.get('ltp_max_length', 512)
        lazy_load = self.config.get('ltp_lazy_load', True)
        enable_srl = self.config.get('ltp_enable_srl', False)
        enable_sdp = self.config.get('ltp_enable_sdp', False)

        # 允许 kwargs 覆盖配置
        if 'model_path' in kwargs:
            model_path = kwargs['model_path']
        if 'device' in kwargs:
            device = kwargs['device']
        if 'batch_size' in kwargs:
            batch_size = kwargs['batch_size']
        if 'max_length' in kwargs:
            max_length = kwargs['max_length']
        if 'lazy_load' in kwargs:
            lazy_load = kwargs['lazy_load']
        if 'enable_srl' in kwargs:
            enable_srl = kwargs['enable_srl']
        if 'enable_sdp' in kwargs:
            enable_sdp = kwargs['enable_sdp']

        return LtpEngine(
            model_path=model_path,
            device=device,
            batch_size=batch_size,
            max_length=max_length,
            lazy_load=lazy_load,
            enable_srl=enable_srl,
            enable_sdp=enable_sdp,
        )
    
    def create_syntax_analyzer(self, **kwargs) -> Optional[SyntaxAnalyzer]:
        """
        创建句法分析器

        Args:
            **kwargs: 额外配置参数

        Returns:
            句法分析器，失败时返回 None
        """
        if 'syntax_analyzer' in self._cache:
            return self._cache['syntax_analyzer']

        use_ltp = self.config.get('use_ltp', False)

        if not use_ltp:
            logger.info("LTP 未启用，跳过句法分析器创建")
            return None

        try:
            engine = self._create_ltp_engine(**kwargs)
            self._cache['syntax_analyzer'] = engine
            return engine

        except Exception as e:
            logger.warning(f"LTP 不可用：{e}")
            return None
    
    def create_entity_recognizer(
        self,
        use_ltp: bool = True,
        **kwargs,
    ) -> Optional[SyntaxAnalyzer]:
        """
        创建实体识别器

        注意：实体识别功能已集成到 LTP 引擎中，此方法返回 LTP 引擎实例

        Args:
            use_ltp: 是否使用 LTP 进行实体识别（默认 True）
            **kwargs: 额外配置参数

        Returns:
            LTP 引擎实例，如果 use_ltp=False 则返回 None
        """
        if not use_ltp:
            logger.warning("不支持独立实体识别引擎，请使用 LTP 引擎")
            return None

        # 使用 LTP 引擎进行实体识别
        return self.create_syntax_analyzer(**kwargs)

    def create_pipeline(
        self,
        components: List[str],
        **kwargs,
    ) -> NlpPipeline:
        """
        创建处理流水线

        分词策略:
        - 仅使用分词功能时：使用 jieba
        - 使用高级功能（句法分析、命名实体识别）时：使用 LTP（分词也顺便用 LTP 来做）

        Args:
            components: 组件列表
                - 'jieba': 分词（使用 jieba）
                - 'syntax': 句法分析（需要 LTP，分词也用 LTP）
                - 'ner': 实体识别（可使用 LTP，分词也用 LTP）
                - 'ltp': 完整 LTP 分析（包含分词、词性、实体、句法）
            **kwargs: 额外配置参数（传递给 LTP 引擎）

        Returns:
            NLP 流水线
        """
        engines = []

        # 检查是否使用高级功能（句法分析或 LTP 增强的 NER）
        use_advanced = 'syntax' in components or 'ner' in components or 'ltp' in components

        # 如果不需要高级功能，使用 jieba 分词
        if not use_advanced and 'jieba' in components:
            try:
                engines.append(self.create_segmenter(use_ltp=False))
            except Exception as e:
                logger.warning(f"创建分词器失败：jieba, 错误：{e}")

        for component in components:
            try:
                if component == 'jieba':
                    # 如果已使用高级功能，跳过 jieba（LTP 会处理分词）
                    if use_advanced:
                        logger.debug("使用高级功能，跳过 jieba 分词，由 LTP 处理分词")
                        continue
                    engines.append(self.create_segmenter(use_ltp=False))
                elif component == 'syntax':
                    analyzer = self.create_syntax_analyzer(**kwargs)
                    if analyzer:
                        engines.append(analyzer)
                elif component == 'ner':
                    engines.append(self.create_entity_recognizer(use_ltp=True, **kwargs))
                elif component == 'ltp':
                    # 完整 LTP 分析
                    ltp_engine = self._create_ltp_engine(**kwargs)
                    engines.append(ltp_engine)
                else:
                    logger.warning(f"未知组件：{component}")
            except Exception as e:
                logger.warning(f"创建组件失败：{component}, 错误：{e}")

        return NlpPipeline(engines)

    def create_full_ltp_engine(self, **kwargs) -> Any:
        """
        创建完整功能的 LTP 引擎（支持 SRL、SDP 等高级功能）

        Args:
            **kwargs: 配置参数
                - enable_srl: 启用语义角色标注
                - enable_sdp: 启用语义依存分析
                - device: 运行设备
                - batch_size: 批处理大小
                - max_length: 最大序列长度

        Returns:
            LtpEngine 实例
        """
        return self._create_ltp_engine(**kwargs)
    
    def clear_cache(self):
        """清除缓存的引擎"""
        self._cache.clear()
