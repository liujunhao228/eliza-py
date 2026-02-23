"""
共享 NLP 服务

为图灵测试平台提供共享的 NLP 能力，支持高并发场景。

特性：
- 单例模式，确保只有一个 LTP 模型实例
- 线程安全访问
- 结果缓存，提高性能
- 优雅降级，LTP 不可用时使用 jieba
"""

import threading
import time
from typing import Optional, Dict, Any
from functools import lru_cache
from loguru import logger

# 导入 AliceBot 的 NLP 模块
# 注意：需要先确保项目路径正确
import sys
sys.path.insert(0, "/f/eliza-py")

from config import settings


class SharedNLPService:
    """
    共享 NLP 服务（单例）

    提供线程安全的 NLP 能力，支持高并发场景。
    """

    _instance: Optional["SharedNLPService"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化服务"""
        if self._initialized:
            return

        self._initialized = True
        self._ltp_available = False
        self._jieba_available = False
        self._ltp_model = None
        self._ltp_lock = threading.RLock()
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.RLock()
        self._cache_hits = 0
        self._cache_misses = 0

        # 初始化 NLP 引擎
        self._initialize_nlp()

    def _initialize_nlp(self):
        """初始化 NLP 引擎"""
        logger.info("正在初始化共享 NLP 服务...")

        # 尝试初始化 LTP
        if settings.turing.nlp_service.enable_ltp:
            try:
                self._initialize_ltp()
            except Exception as e:
                logger.warning(f"LTP 初始化失败: {e}，将使用 jieba")
                self._ltp_available = False
        else:
            logger.info("LTP 已禁用，将使用 jieba")

        # 初始化 jieba
        try:
            import jieba
            self._jieba_available = True
            logger.info("jieba 初始化成功")
        except ImportError as e:
            logger.warning(f"jieba 初始化失败: {e}")
            self._jieba_available = False

        if not self._ltp_available and not self._jieba_available:
            raise RuntimeError("没有可用的 NLP 引擎")

        logger.info(f"✅ NLP 服务初始化完成")
        logger.info(f"   - LTP: {'✅' if self._ltp_available else '❌'}")
        logger.info(f"   - jieba: {'✅' if self._jieba_available else '❌'}")
        logger.info(f"   - 缓存大小: {settings.NLP_CACHE_SIZE}")
        logger.info(f"   - 缓存过期时间: {settings.NLP_CACHE_TTL}秒")

    def _initialize_ltp(self):
        """初始化 LTP"""
        try:
            from ltp import LTP

            # LTP 模型初始化可能较慢
            logger.info("正在加载 LTP 模型...")
            self._ltp_model = LTP()

            # 测试 LTP 是否可用
            test_result = self._ltp_model.pipeline("测试文本")
            if test_result:
                self._ltp_available = True
                logger.info("✅ LTP 初始化成功")
            else:
                raise RuntimeError("LTP 模型测试失败")

        except ImportError:
            raise RuntimeError("LTP 未安装")
        except Exception as e:
            raise RuntimeError(f"LTP 初始化失败: {e}")

    def _get_cache_key(self, text: str, operation: str) -> str:
        """生成缓存键"""
        return f"{operation}:{text}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取结果"""
        with self._cache_lock:
            if key in self._cache:
                cached_data, timestamp = self._cache[key]
                # 检查是否过期
                if time.time() - timestamp < settings.NLP_CACHE_TTL:
                    self._cache_hits += 1
                    return cached_data
                else:
                    # 过期，删除
                    del self._cache[key]

        self._cache_misses += 1
        return None

    def _set_cache(self, key: str, value: Any):
        """设置缓存"""
        with self._cache_lock:
            # 如果缓存已满，删除最旧的一半
            if len(self._cache) >= settings.NLP_CACHE_SIZE:
                keys_to_delete = list(self._cache.keys())[:settings.NLP_CACHE_SIZE // 2]
                for k in keys_to_delete:
                    del self._cache[k]

            self._cache[key] = (value, time.time())

    def _cleanup_cache(self):
        """清理过期缓存"""
        with self._cache_lock:
            current_time = time.time()
            keys_to_delete = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp > settings.NLP_CACHE_TTL
            ]
            for key in keys_to_delete:
                del self._cache[key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._cache_lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (
                self._cache_hits / total_requests * 100
                if total_requests > 0 else 0
            )

            return {
                "cache_size": len(self._cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate": f"{hit_rate:.2f}%",
            }

    def segment(self, text: str) -> list[str]:
        """
        文本分词

        Args:
            text: 要分词的文本

        Returns:
            分词结果列表
        """
        cache_key = self._get_cache_key(text, "segment")
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # 使用 LTP 分词
        if self._ltp_available:
            with self._ltp_lock:
                try:
                    result = self._ltp_model.pipeline(text)
                    words = result["cws"]
                    self._set_cache(cache_key, words)
                    return words
                except Exception as e:
                    logger.warning(f"LTP 分词失败，降级到 jieba: {e}")

        # 降级到 jieba
        if self._jieba_available:
            import jieba
            words = list(jieba.cut(text))
            self._set_cache(cache_key, words)
            return words

        # 都不可用，按字符分割
        words = list(text)
        self._set_cache(cache_key, words)
        return words

    def get_entities(self, text: str) -> list[tuple[str, str, int, int]]:
        """
        命名实体识别

        Args:
            text: 要识别的文本

        Returns:
            实体列表，每个实体为 (文本, 类型, 开始位置, 结束位置)
        """
        cache_key = self._get_cache_key(text, "ner")
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # 使用 LTP 进行 NER
        if self._ltp_available:
            with self._ltp_lock:
                try:
                    result = self._ltp_model.pipeline(text)
                    entities = [
                        (entity["text"], entity["type"], entity["start"], entity["end"])
                        for entity in result.get("ner", [])
                    ]
                    self._set_cache(cache_key, entities)
                    return entities
                except Exception as e:
                    logger.warning(f"LTP NER 失败: {e}")

        # LTP 不可用，返回空列表
        self._set_cache(cache_key, [])
        return []

    def get_pos_tags(self, text: str) -> list[tuple[str, str]]:
        """
        词性标注

        Args:
            text: 要标注的文本

        Returns:
            词性列表，每个词性为 (词, 词性标签)
        """
        cache_key = self._get_cache_key(text, "pos")
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # 使用 LTP 进行词性标注
        if self._ltp_available:
            with self._ltp_lock:
                try:
                    result = self._ltp_model.pipeline(text)
                    words = result["cws"]
                    pos_tags = result["pos"]
                    pos_pairs = list(zip(words, pos_tags))
                    self._set_cache(cache_key, pos_pairs)
                    return pos_pairs
                except Exception as e:
                    logger.warning(f"LTP 词性标注失败: {e}")

        # LTP 不可用，使用简单的词性标注
        # 这里简化处理，返回 (词, "n") 的格式
        words = self.segment(text)
        pos_pairs = [(word, "n") for word in words]
        self._set_cache(cache_key, pos_pairs)
        return pos_pairs

    def analyze_syntax(self, text: str) -> dict[str, Any]:
        """
        句法分析

        Args:
            text: 要分析的文本

        Returns:
            包含分词、词性、依存句法等信息的字典
        """
        cache_key = self._get_cache_key(text, "syntax")
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # 使用 LTP 进行句法分析
        if self._ltp_available:
            with self._ltp_lock:
                try:
                    result = self._ltp_model.pipeline(text)
                    syntax_info = {
                        "cws": result["cws"],
                        "pos": result["pos"],
                        "dep": result["dep"],
                        "sdp": result.get("sdp", []),
                    }
                    self._set_cache(cache_key, syntax_info)
                    return syntax_info
                except Exception as e:
                    logger.warning(f"LTP 句法分析失败: {e}")

        # LTP 不可用，返回基本信息
        words = self.segment(text)
        syntax_info = {
            "cws": words,
            "pos": ["n"] * len(words),
            "dep": [],
            "sdp": [],
        }
        self._set_cache(cache_key, syntax_info)
        return syntax_info

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "ltp_available": self._ltp_available,
            "jieba_available": self._jieba_available,
            "cache_stats": self.get_cache_stats(),
            "cache_enabled": settings.NLP_CACHE_SIZE > 0,
        }


# =============================================================================
# 全局服务实例
# =============================================================================

_nlp_service_instance: Optional[SharedNLPService] = None
_nlp_service_lock = threading.Lock()


def get_nlp_service() -> SharedNLPService:
    """
    获取共享 NLP 服务实例（懒加载）

    Returns:
        SharedNLPService 实例
    """
    global _nlp_service_instance

    if _nlp_service_instance is None:
        with _nlp_service_lock:
            if _nlp_service_instance is None:
                _nlp_service_instance = SharedNLPService()

    return _nlp_service_instance


def reset_nlp_service():
    """重置 NLP 服务（主要用于测试）"""
    global _nlp_service_instance

    with _nlp_service_lock:
        _nlp_service_instance = None
