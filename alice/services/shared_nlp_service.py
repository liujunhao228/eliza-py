"""
共享 NLP 服务，单例模式
统一管理所有 NLP 资源，避免重复加载
符合编码规范的异常处理、优雅降级和日志记录要求
"""

import threading
import time
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
import jieba
from alice.nlp.engines.jieba_engine import JiebaEngine
from alice.nlp.engines.ltp_engine import LtpEngine
from alice.nlp.base import (
    SyntaxAnalyzer,
    EntityRecognizer,
    NlpResult,
    SyntaxStructure,
    Entity,
)
from alice.nlp.factory import NlpFactory, NlpPipeline
from alice.nlp.engines.ltp import DependencyRelation
from alice.exceptions import (
    TextProcessingError,
    InputValidationError,
    ResponseGenerationError,
    DependencyError,
    ExternalLibraryError,
)
from alice.utils.logger import setup_logger
from alice.utils.degradation_monitor import degradation_monitor

# 设置日志记录器
logger = setup_logger(__name__)


class SharedNLPService(SyntaxAnalyzer, EntityRecognizer):
    """
    共享 NLP 服务，单例模式
    统一管理所有 NLP 资源，避免重复加载

    实现标准接口：
    - SyntaxAnalyzer: 提供句法分析功能
    - EntityRecognizer: 提供实体识别功能

    高级功能：
    - 依存分析、词性标注、三元组抽取
    - NLP 工厂和流水线创建
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._jieba_engine = JiebaEngine()
        self._ltp_engine = None  # 可选加载
        self._cache = {}
        self._cache_lock = threading.RLock()

        # NLP 工厂（懒加载）
        self._factory: Optional[NlpFactory] = None

        # 性能统计
        self._stats = {
            'total_calls': 0,
            'failed_calls': 0,
            'avg_time_ms': 0.0,
        }

    @property
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._jieba_engine.is_available and (
            self._ltp_engine is None or self._ltp_engine.is_available
        )

    def initialize_ltp(self, enable_ltp: bool = False):
        """初始化 LTP 引擎"""
        if enable_ltp:
            try:
                self._ltp_engine = LtpEngine()
                if not self._ltp_engine.is_available:
                    logger.warning("LTP 引擎初始化失败，将使用基础模式")
                    self._ltp_engine = None
                    # 记录降级事件
                    degradation_monitor.register_degradation(
                        component='ltp_initialization',
                        reason='LTP 引擎初始化失败',
                        severity=2,
                        recovery_plan='检查 LTP 模型文件和依赖',
                        original_functionality='完整的 LTP 分析功能',
                        degraded_functionality='仅使用 jieba 基础分词',
                        user_notification='系统正在使用基础分词模式'
                    )
                else:
                    logger.info("LTP 引擎初始化成功")
            except Exception as e:
                logger.error(f"LTP 引擎初始化失败：{e}")
                self._ltp_engine = None
                # 记录降级事件
                degradation_monitor.register_degradation(
                    component='ltp_initialization',
                    reason=f'LTP 引擎初始化失败：{str(e)}',
                    severity=2,
                    recovery_plan='检查 LTP 依赖和环境配置',
                    original_functionality='完整的 LTP 分析功能',
                    degraded_functionality='仅使用 jieba 基础分词',
                    user_notification='系统正在使用基础分词模式'
                )

    def _validate_input(self, text: str, operation: str) -> None:
        """验证输入参数"""
        if not isinstance(text, str):
            raise InputValidationError(
                f"{operation}输入文本必须是字符串类型",
                context={'operation': operation, 'input_type': type(text).__name__}
            )

        if not text.strip():
            raise InputValidationError(
                f"{operation}输入文本不能为空",
                context={'operation': operation, 'input_length': len(text)}
            )

        if len(text) > 10000:
            raise InputValidationError(
                f"{operation}输入文本过长，请限制在 10000 字符以内",
                context={'operation': operation, 'input_length': len(text)}
            )

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

    def _basic_analyze(self, text: str) -> NlpResult:
        """基础分析（仅分词）"""
        start_time = time.time()

        try:
            tokens = self._jieba_engine.segment(text)

            # 更新统计
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)

            # logger.log_performance 已移除

            return NlpResult(
                text=text,
                tokens=tokens,
                syntax=SyntaxStructure(words=tokens)
            )

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"基础分析失败：{e}")
            raise TextProcessingError(f"基础分析处理失败：{e}") from e

    def tokenize(self, text: str) -> List[str]:
        """分词"""
        self._validate_input(text, "分词")

        start_time = time.time()

        try:
            result = self._jieba_engine.segment(text)

            # 更新统计
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)

            # logger.log_performance 已移除

            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"分词失败：{e}")
            raise TextProcessingError(f"分词处理失败：{e}") from e

    def analyze(self, text: str) -> NlpResult:
        """标准分析接口（分词 + 词性 + 句法 + 实体）"""
        self._validate_input(text, "分析")

        start_time = time.time()

        try:
            # 优先使用 LTP
            if self._ltp_engine and self._ltp_engine.is_available:
                result = self._ltp_engine.analyze(text)
            else:
                # 降级到基础分析
                result = self._basic_analyze(text)
                # 记录降级事件
                degradation_monitor.register_degradation(
                    component='full_analysis',
                    reason='LTP 引擎不可用，使用基础分析模式',
                    severity=1,
                    recovery_plan='检查 LTP 引擎状态',
                    original_functionality='完整的 LTP 分析功能',
                    degraded_functionality='基础分词功能',
                    user_notification='系统正在使用基础分析模式'
                )

            # 更新统计
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)

            # logger.log_performance 已移除

            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"分析失败：{e}")
            raise TextProcessingError(f"文本分析失败：{e}") from e

    def analyze_full(self, text: str) -> NlpResult:
        """完整分析接口（与 LTP 引擎兼容）"""
        return self.analyze(text)

    def analyze_syntax(self, text: str) -> SyntaxStructure:
        """句法分析

        Raises:
            DependencyError: LTP 引擎不可用时抛出
        """
        self._validate_input(text, "句法分析")

        start_time = time.time()

        if not self._ltp_engine or not self._ltp_engine.is_available:
            # 句法分析属于核心功能，不可降级
            logger.error("LTP 引擎不可用，无法进行句法分析")
            raise DependencyError(
                "LTP 引擎不可用，句法分析功能无法使用",
                suggestion="请检查 LTP 依赖和模型配置"
            )

        try:
            result = self._ltp_engine.analyze(text)
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)
            return result.syntax

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"句法分析失败：{e}")
            raise ResponseGenerationError(f"句法分析处理失败：{e}") from e

    def recognize(self, text: str) -> List[Entity]:
        """实体识别（实现 EntityRecognizer 接口）"""
        return self.extract_entities(text)

    def extract_entities(self, text: str) -> List[Entity]:
        """实体抽取

        Raises:
            DependencyError: LTP 引擎不可用时抛出
        """
        self._validate_input(text, "实体抽取")

        start_time = time.time()

        if not self._ltp_engine or not self._ltp_engine.is_available:
            # 实体识别属于核心功能，不可降级
            logger.error("LTP 引擎不可用，无法进行实体识别")
            raise DependencyError(
                "LTP 引擎不可用，实体识别功能无法使用",
                suggestion="请检查 LTP 依赖和模型配置"
            )

        try:
            result = self._ltp_engine.extract_entities(text)
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"实体抽取失败：{e}")
            raise ResponseGenerationError(f"实体抽取处理失败：{e}") from e

    def get_cached_result(self, key: str) -> Optional[Any]:
        """获取缓存结果（支持 TTL）"""
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached:
                # 检查是否过期
                if time.time() < cached['expire_time']:
                    return cached['value']
                else:
                    # 缓存过期，删除
                    del self._cache[key]
            return None

    def set_cached_result(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存结果（支持 TTL）"""
        with self._cache_lock:
            self._cache[key] = {
                'value': value,
                'expire_time': time.time() + ttl
            }

    def clear_cache(self):
        """清除所有缓存"""
        with self._cache_lock:
            self._cache.clear()
            logger.info("缓存已清除")

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self._stats.copy()

    # =====================================================================
    # LTP 高级语义分析接口
    # =====================================================================

    def pos_tag(self, text: str) -> List[Tuple[str, str]]:
        """
        词性标注

        Args:
            text: 待分析文本

        Returns:
            [(词，词性), ...] 列表

        Raises:
            TextProcessingError: 处理失败时抛出
            DependencyError: LTP 引擎不可用时抛出
        """
        self._validate_input(text, "词性标注")

        start_time = time.time()

        if not self._ltp_engine or not self._ltp_engine.is_available:
            # 词性标注属于核心功能，不可降级
            logger.error("LTP 引擎不可用，无法进行词性标注")
            raise DependencyError(
                "LTP 引擎不可用，词性标注功能无法使用",
                suggestion="请检查 LTP 依赖和模型配置"
            )

        try:
            result = self._ltp_engine.pos_tag(text)
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"词性标注失败：{e}")
            raise TextProcessingError(f"词性标注处理失败：{e}") from e

    def parse_dependency(self, text: str) -> List[DependencyRelation]:
        """
        依存句法分析

        Args:
            text: 待分析文本

        Returns:
            依存关系列表

        Raises:
            TextProcessingError: 处理失败时抛出
            DependencyError: LTP 引擎不可用时抛出
        """
        self._validate_input(text, "依存分析")

        start_time = time.time()

        if not self._ltp_engine or not self._ltp_engine.is_available:
            # 依存分析属于核心功能，不可降级
            logger.error("LTP 引擎不可用，无法进行依存分析")
            raise DependencyError(
                "LTP 引擎不可用，依存句法分析功能无法使用",
                suggestion="请检查 LTP 依赖和模型配置"
            )

        try:
            result = self._ltp_engine.parse_dependency(text)
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"依存分析失败：{e}")
            raise TextProcessingError(f"依存句法分析失败：{e}") from e

    def extract_triples(self, text: str) -> List[Tuple[str, str, str]]:
        """
        提取主谓宾三元组

        Args:
            text: 待分析文本

        Returns:
            [(主语，谓语，宾语), ...] 列表

        Raises:
            TextProcessingError: 处理失败时抛出
            DependencyError: LTP 引擎不可用时抛出
        """
        self._validate_input(text, "三元组抽取")

        start_time = time.time()

        if not self._ltp_engine or not self._ltp_engine.is_available:
            # 三元组抽取属于核心功能，不可降级
            logger.error("LTP 引擎不可用，无法抽取三元组")
            raise DependencyError(
                "LTP 引擎不可用，三元组抽取功能无法使用",
                suggestion="请检查 LTP 依赖和模型配置"
            )

        try:
            result = self._ltp_engine.extract_triples(text)
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=False)
            logger.error(f"三元组抽取失败：{e}")
            raise TextProcessingError(f"三元组抽取失败：{e}") from e

    # =====================================================================
    # NLP 工厂接口
    # =====================================================================

    def get_factory(self, config: Optional[Dict[str, Any]] = None) -> NlpFactory:
        """
        获取 NLP 工厂实例

        Args:
            config: 工厂配置字典
                - use_ltp_for_advanced: 是否对高级功能使用 LTP
                - ltp_model_path: LTP 模型路径
                - ltp_device: LTP 运行设备
                - ltp_batch_size: LTP 批处理大小
                - ltp_max_length: LTP 最大序列长度
                - ltp_enable_srl: 是否启用语义角色标注
                - ltp_enable_sdp: 是否启用语义依存分析

        Returns:
            NlpFactory 实例
        """
        if self._factory is None:
            self._factory = NlpFactory(config)
        elif config is not None:
            # 配置变更时重新创建工厂
            self._factory = NlpFactory(config)

        return self._factory

    def create_pipeline(
        self,
        components: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> NlpPipeline:
        """
        创建 NLP 处理流水线

        Args:
            components: 组件列表
                - 'jieba': 分词（使用 jieba）
                - 'syntax': 句法分析（需要 LTP）
                - 'ner': 实体识别（使用 LTP）
                - 'ltp': 完整 LTP 分析
            config: 可选的工厂配置

        Returns:
            NlpPipeline 实例

        Raises:
            TextProcessingError: 创建失败时抛出
        """
        try:
            factory = self.get_factory(config)
            return factory.create_pipeline(components)

        except Exception as e:
            logger.error(f"创建流水线失败：{e}")
            raise TextProcessingError(f"NLP 流水线创建失败：{e}") from e

    def get_degradation_report(self) -> Dict[str, Any]:
        """获取降级报告"""
        return degradation_monitor.get_degradation_report()

    def shutdown(self):
        """
        关闭 NLP 服务，清理资源
        
        清理内容:
        - 清除所有缓存
        - 释放 LTP 引擎资源
        - 重置工厂实例
        """
        logger.info("正在关闭 NLP 服务...")
        
        # 清除缓存
        with self._cache_lock:
            self._cache.clear()
            logger.debug("NLP 缓存已清除")
        
        # 重置工厂实例
        self._factory = None
        
        # 关闭 LTP 引擎（如果有）
        if self._ltp_engine is not None:
            try:
                if hasattr(self._ltp_engine, 'shutdown'):
                    self._ltp_engine.shutdown()
                logger.debug("LTP 引擎已关闭")
            except Exception as e:
                logger.warning(f"关闭 LTP 引擎时出错：{e}")
        
        # 关闭 jieba 引擎（如果有）
        if self._jieba_engine is not None:
            try:
                if hasattr(self._jieba_engine, 'shutdown'):
                    self._jieba_engine.shutdown()
                logger.debug("jieba 引擎已关闭")
            except Exception as e:
                logger.warning(f"关闭 jieba 引擎时出错：{e}")
        
        logger.info("✅ NLP 服务已关闭")
