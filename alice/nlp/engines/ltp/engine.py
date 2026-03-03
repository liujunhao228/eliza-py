#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎主模块
==============

增强版 LTP 引擎实现，支持完整的 NLP 分析功能。
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Dict, Any, Tuple

from alice.nlp.base import (
    SyntaxAnalyzer,
    Entity,
    NlpResult,
    SyntaxStructure,
)
from alice.exceptions import DependencyError

from .config import LtpConfig
from .models import (
    TaskType,
    Token,
    LtpFullResult,
    DependencyRelation,
)
from .handlers import (
    BaseTaskHandler,
    CWSTaskHandler,
    POSTaskHandler,
    NERTaskHandler,
    DEPTaskHandler,
    SRLTaskHandler,
    SDPTaskHandler,
)
from .validators import (
    PosTagValidator,
    DependencyValidator,
    SemanticRoleValidator,
    SemanticDepValidator,
)
from .exceptions import LtpError, ModelLoadError, AnalysisError

logger = logging.getLogger(__name__)

# =============================================================================
# 依赖检查与导入
# =============================================================================

try:
    from ltp import LTP
    LTP_AVAILABLE = True
    LTP_VERSION = getattr(LTP, '__version__', 'unknown')
except ImportError:
    LTP_AVAILABLE = False
    LTP_VERSION = None
    logger.warning("LTP 未安装，功能不可用（安装：pip install ltp>=4.2.10）")


class LtpEngine(SyntaxAnalyzer):
    """
    增强版 LTP 引擎

    支持任务:
    - CWS: 中文分词
    - POS: 词性标注
    - NER: 命名实体识别（人名、地名、机构名）
    - DEP: 依存句法分析（14 种依存关系）
    - SRL: 语义角色标注（需显式开启）
    - SDP: 语义依存分析（需显式开启）

    使用示例:
        >>> config = LtpConfig(enable_srl=True, enable_sdp=True)
        >>> engine = LtpEngine(config)
        >>> result = engine.analyze_full("小明在北京大学读书")
        >>> print(result.to_json())
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
        enable_srl: bool = False,
        enable_sdp: bool = False,
    ):
        """
        初始化 LTP 引擎

        Args:
            model_path: 模型路径，None 使用官方默认模型
            device: 运行设备 ('cpu', 'cuda', 'cuda:0' 等)，None 自动选择
            batch_size: 批处理大小，默认 32
            max_length: 最大序列长度，默认 512
            enable_srl: 是否启用语义角色标注，默认关闭
            enable_sdp: 是否启用语义依存分析，默认关闭

        注意:
            - 模型首次加载较慢（约 5-10 秒）
            - SRL 和 SDP 会增加计算开销，建议按需开启
        """
        if not LTP_AVAILABLE:
            raise DependencyError(
                "LTP 库未安装",
                suggestion="pip install ltp>=4.2.10"
            )

        self.config = LtpConfig(
            model_path=model_path,
            device=device,
            batch_size=batch_size,
            max_length=max_length,
            enable_srl=enable_srl,
            enable_sdp=enable_sdp,
        )

        self._ltp: Optional[LTP] = None
        self._initialized = False

        # 注册任务处理器
        self._handlers: Dict[TaskType, BaseTaskHandler] = {
            TaskType.CWS: CWSTaskHandler(),
            TaskType.POS: POSTaskHandler(),
            TaskType.NER: NERTaskHandler(),
            TaskType.DEP: DEPTaskHandler(),
            TaskType.SRL: SRLTaskHandler(),
            TaskType.SDP: SDPTaskHandler(),
        }

        # 性能统计
        self._stats: Dict[str, Any] = {
            'total_calls': 0,
            'failed_calls': 0,
            'avg_time_ms': 0.0,
        }

        # 初始化时立即加载模型
        self._load_model()

    def _load_model(self) -> bool:
        """加载 LTP 模型"""
        if self._initialized:
            return True

        try:
            load_kwargs = {}
            if self.config.model_path:
                load_kwargs['path'] = self.config.model_path
            if self.config.device:
                load_kwargs['device'] = self.config.device

            self._ltp = LTP(**load_kwargs)
            self._initialized = True

            logger.info(
                f"LTP 模型加载成功 | "
                f"版本：{LTP_VERSION} | "
                f"设备：{self.config.device or 'auto'} | "
                f"路径：{self.config.model_path or '默认'}"
            )
            return True

        except Exception as e:
            logger.error(f"LTP 模型加载失败：{e}", exc_info=True)
            raise ModelLoadError(f"无法加载 LTP 模型：{e}") from e

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        if not LTP_AVAILABLE:
            return False
        return self._initialized and self._ltp is not None

    @property
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._initialized and self._ltp is not None

    @property
    def stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self._stats.copy()

    def _ensure_loaded(self) -> bool:
        """确保模型已加载"""
        if not self._initialized:
            return self._load_model()
        return True

    def analyze_full(self, text: str) -> LtpFullResult:
        """
        完整分析（增强接口）

        Args:
            text: 待分析文本

        Returns:
            LtpFullResult: 完整分析结果
        """
        if not self._ensure_loaded():
            raise AnalysisError("模型未加载")

        if not text or not text.strip():
            return LtpFullResult(text=text)

        start_time = time.time()

        try:
            tasks = self.config.get_enabled_tasks()

            if not tasks:
                logger.warning("未启用任何分析任务")
                return LtpFullResult(text=text)

            # 执行 LTP 管道
            ltp_output = self._ltp.pipeline([text], tasks=tasks)

            # 构建结果
            result = self._build_result(ltp_output, text)

            # 更新统计
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)

            logger.debug(f"分析完成 | 文本长度：{len(text)} | 耗时：{elapsed:.2f}ms")

            return result

        except Exception as e:
            self._update_stats(0, success=False)
            logger.error(f"分析失败：{e}", exc_info=True)
            raise AnalysisError(f"文本分析失败：{e}") from e

    def _build_result(self, ltp_output: Any, text: str) -> LtpFullResult:
        """构建完整结果对象"""
        result = LtpFullResult(text=text, raw_output=ltp_output)

        # 1. 分词 (基础)
        if self.config.enable_cws:
            result.tokens = self._handlers[TaskType.CWS].process(
                ltp_output, text, []
            )

        # 2. 词性标注
        if self.config.enable_pos and result.tokens:
            result.pos_tags = self._handlers[TaskType.POS].process(
                ltp_output, text, result.tokens
            )

        # 3. 命名实体识别
        if self.config.enable_ner and result.tokens:
            result.entities = self._handlers[TaskType.NER].process(
                ltp_output, text, result.tokens
            )

        # 4. 依存句法分析
        if self.config.enable_dep and result.tokens:
            result.dependencies = self._handlers[TaskType.DEP].process(
                ltp_output, text, result.tokens
            )

        # 5. 语义角色标注 (SRL)
        if self.config.enable_srl and result.tokens:
            result.semantic_roles = self._handlers[TaskType.SRL].process(
                ltp_output, text, result.tokens
            )

        # 6. 语义依存分析 (SDP)
        if self.config.enable_sdp and result.tokens:
            result.semantic_deps = self._handlers[TaskType.SDP].process(
                ltp_output, text, result.tokens
            )

        # 验证标注集（如果启用）
        if self.config.enable_validation:
            self._validate_result(result)

        return result

    def _validate_result(self, result: LtpFullResult) -> None:
        """验证分析结果的标注集完整性"""
        has_error = False

        # 验证词性标注
        if result.pos_tags:
            invalid_pos = PosTagValidator.validate(result.pos_tags)
            if invalid_pos and self.config.validation_strict:
                has_error = True
                logger.warning(f"发现 {len(invalid_pos)} 个无效词性标签")

        # 验证依存关系
        if result.dependencies:
            invalid_dep = DependencyValidator.validate(result.dependencies)
            if invalid_dep and self.config.validation_strict:
                has_error = True
                logger.warning(f"发现 {len(invalid_dep)} 个无效依存关系")

        # 验证语义角色
        if result.semantic_roles:
            invalid_role = SemanticRoleValidator.validate(result.semantic_roles)
            if invalid_role and self.config.validation_strict:
                has_error = True
                logger.warning(f"发现 {len(invalid_role)} 个无效语义角色")

        # 验证语义依存
        if result.semantic_deps and result.semantic_deps.edges:
            invalid_sdp = SemanticDepValidator.validate(result.semantic_deps.edges)
            if invalid_sdp and self.config.validation_strict:
                has_error = True
                logger.warning(f"发现 {len(invalid_sdp)} 个无效语义依存关系")

        if has_error and self.config.validation_strict:
            raise AnalysisError("标注集验证失败")

    def _update_stats(self, elapsed_ms: float, success: bool):
        """更新性能统计"""
        self._stats['total_calls'] += 1
        if not success:
            self._stats['failed_calls'] += 1

        # 移动平均
        n = self._stats['total_calls']
        self._stats['avg_time_ms'] = (
            (self._stats['avg_time_ms'] * (n - 1) + elapsed_ms) / n
        )

    # =====================================================================
    # 标准接口（兼容旧版）
    # =====================================================================

    def analyze(self, text: str) -> NlpResult:
        """标准分析接口（向后兼容）"""
        try:
            full_result = self.analyze_full(text)
            syntax = self._convert_to_syntax_structure(full_result)

            return NlpResult(
                text=text,
                tokens=[t.text for t in full_result.tokens] or list(text),
                entities=full_result.entities,
                syntax=syntax,
            )

        except Exception as e:
            logger.error(f"标准分析失败：{e}")
            return self._fallback_analyze(text)

    def _convert_to_syntax_structure(self,
                                     result: LtpFullResult) -> SyntaxStructure:
        """转换为旧版 SyntaxStructure"""
        words = [t.text for t in result.tokens]
        poses = [p.pos for p in result.pos_tags] if result.pos_tags else ['n'] * len(words)

        # 提取主谓宾
        subject = predicate = obj = ""
        modifiers: Dict[str, List[str]] = {}
        dependencies: List[Dict[str, Any]] = []

        for dep in result.dependencies:
            word = dep.token.text
            if dep.relation == 'SBV':
                subject = word
            elif dep.relation == 'VOB':
                obj = word
            elif dep.relation == 'HED':
                predicate = word
            elif dep.relation in ['ATT', 'ADV']:
                head_idx = dep.head_idx
                if 0 <= head_idx < len(words):
                    head_word = words[head_idx]
                    modifiers.setdefault(head_word, []).append(word)
            
            # 将依存关系转换为字典格式
            dependencies.append({
                'word': dep.token.text,
                'relation': dep.relation,
                'head': dep.head_idx,
                'desc': dep.description,
            })

        return SyntaxStructure(
            words=words,
            poses=poses,
            subject=subject,
            predicate=predicate,
            object=obj,
            modifiers=modifiers,
            dependencies=dependencies,
        )

    def _fallback_analyze(self, text: str) -> NlpResult:
        """降级分析（字符级）"""
        tokens = list(text)
        return NlpResult(
            text=text,
            tokens=tokens,
            syntax=SyntaxStructure(words=tokens),
        )

    # =====================================================================
    # 便捷方法
    # =====================================================================

    def segment(self, text: str) -> List[str]:
        """仅分词"""
        result = self.analyze_full(text)
        return [t.text for t in result.tokens]

    def pos_tag(self, text: str) -> List[Tuple[str, str]]:
        """分词 + 词性标注"""
        result = self.analyze_full(text)
        return [(p.token.text, p.pos) for p in result.pos_tags]

    def extract_entities(self, text: str) -> List[Entity]:
        """仅实体识别"""
        result = self.analyze_full(text)
        return result.entities

    def parse_dependency(self, text: str) -> List[DependencyRelation]:
        """依存句法分析"""
        result = self.analyze_full(text)
        return result.dependencies

    def extract_triples(self, text: str) -> List[Tuple[str, str, str]]:
        """提取主谓宾三元组"""
        result = self.analyze_full(text)
        triples = []

        predicates = {}
        subjects = {}
        objects = {}

        for dep in result.dependencies:
            if dep.relation == 'HED':
                predicates[dep.token.idx] = dep.token.text
            elif dep.relation == 'SBV':
                head_idx = dep.head_idx
                if head_idx in predicates:
                    subjects[predicates[head_idx]] = dep.token.text
            elif dep.relation == 'VOB':
                head_idx = dep.head_idx
                if head_idx in predicates:
                    objects[predicates[head_idx]] = dep.token.text

        for pred in predicates:
            subj = subjects.get(pred, '')
            obj = objects.get(pred, '')
            if subj or obj:
                triples.append((subj, pred, obj))

        return triples

    # =====================================================================
    # 状态管理
    # =====================================================================

    @classmethod
    def clear_cache(cls):
        """清除 LTP 缓存（用于恢复）"""
        pass

    def reset(self):
        """重置引擎状态"""
        self._ltp = None
        self._initialized = False
        self._stats = {
            'total_calls': 0,
            'failed_calls': 0,
            'avg_time_ms': 0.0,
        }
        logger.info("LTP 引擎已重置")


__all__ = ['LtpEngine', 'LTP_AVAILABLE', 'LTP_VERSION']
