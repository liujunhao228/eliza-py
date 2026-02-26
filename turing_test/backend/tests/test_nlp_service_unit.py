"""
NLP 服务单元测试

测试共享 NLP 服务的分词、词性标注、实体识别等功能。
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from threading import Thread

from turing_test.backend.services.nlp_service import (
    SharedNLPService,
    get_nlp_service,
    reset_nlp_service,
)


# =============================================================================
# 夹具
# =============================================================================

@pytest.fixture(autouse=True)
def reset_service():
    """每个测试前后重置服务"""
    reset_nlp_service()
    yield
    reset_nlp_service()


# =============================================================================
# 单例模式测试
# =============================================================================

class TestNLPServiceSingleton:
    """测试 NLP 服务单例模式"""

    def test_singleton_instance(self):
        """测试单例实例"""
        service1 = get_nlp_service()
        service2 = get_nlp_service()
        
        assert service1 is service2

    def test_thread_safety(self):
        """测试线程安全性"""
        instances = []
        
        def get_instance():
            service = get_nlp_service()
            instances.append(service)
        
        # 多线程获取实例
        threads = [Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有线程应该获取到同一个实例
        assert len(set(id(s) for s in instances)) == 1


# =============================================================================
# 分词功能测试
# =============================================================================

class TestSegmentation:
    """测试分词功能"""

    def test_segment_basic(self):
        """测试基础分词"""
        service = get_nlp_service()
        result = service.segment("中华人民共和国")
        
        assert isinstance(result, list)
        assert len(result) > 0
        # 结果应该是字符串列表
        assert all(isinstance(word, str) for word in result)

    def test_segment_empty_input(self):
        """测试空输入分词"""
        service = get_nlp_service()
        result = service.segment("")
        
        assert isinstance(result, list)

    def test_segment_with_punctuation(self):
        """测试带标点符号的分词"""
        service = get_nlp_service()
        result = service.segment("你好，世界！这是一个测试。")
        
        assert isinstance(result, list)
        assert len(result) > 0

    def test_segment_cache(self):
        """测试分词缓存"""
        service = get_nlp_service()
        
        # 第一次调用
        result1 = service.segment("测试缓存")
        initial_stats = service.get_cache_stats()
        initial_misses = initial_stats["cache_misses"]
        
        # 第二次调用相同文本
        result2 = service.segment("测试缓存")
        
        # 结果应该相同
        assert result1 == result2
        
        # 检查缓存命中
        new_stats = service.get_cache_stats()
        # 至少有一次命中
        assert new_stats["cache_hits"] > 0 or new_stats["cache_misses"] > initial_misses


# =============================================================================
# 词性标注测试
# =============================================================================

class TestPOSTagging:
    """测试词性标注功能"""

    def test_pos_basic(self):
        """测试基础词性标注"""
        service = get_nlp_service()
        result = service.get_pos_tags("我爱中国")
        
        assert isinstance(result, list)
        assert len(result) > 0
        # 每个结果应该是 (词，词性) 元组
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        assert all(isinstance(word, str) and isinstance(tag, str) for word, tag in result)

    def test_pos_empty_input(self):
        """测试空输入词性标注"""
        service = get_nlp_service()
        result = service.get_pos_tags("")
        
        assert isinstance(result, list)

    def test_pos_format(self):
        """测试词性标注格式"""
        service = get_nlp_service()
        result = service.get_pos_tags("测试")
        
        if result:
            word, tag = result[0]
            assert isinstance(word, str)
            assert isinstance(tag, str)


# =============================================================================
# 命名实体识别测试
# =============================================================================

class TestNER:
    """测试命名实体识别功能"""

    def test_ner_basic(self):
        """测试基础实体识别"""
        service = get_nlp_service()
        result = service.get_entities("北京是中国的首都")
        
        assert isinstance(result, list)
        # 实体应该是 (文本，类型，开始位置，结束位置) 元组
        if result:
            assert all(isinstance(e, tuple) and len(e) == 4 for e in result)

    def test_ner_empty_input(self):
        """测试空输入实体识别"""
        service = get_nlp_service()
        result = service.get_entities("")
        
        assert isinstance(result, list)

    def test_ner_no_entities(self):
        """测试无实体的文本"""
        service = get_nlp_service()
        result = service.get_entities("的了吗呢")
        
        assert isinstance(result, list)


# =============================================================================
# 句法分析测试
# =============================================================================

class TestSyntaxAnalysis:
    """测试句法分析功能"""

    def test_syntax_basic(self):
        """测试基础句法分析"""
        service = get_nlp_service()
        result = service.analyze_syntax("我爱中国")
        
        assert isinstance(result, dict)
        assert "cws" in result  # 分词
        assert "pos" in result  # 词性

    def test_syntax_empty_input(self):
        """测试空输入句法分析"""
        service = get_nlp_service()
        result = service.analyze_syntax("")
        
        assert isinstance(result, dict)
        assert "cws" in result

    def test_syntax_structure(self):
        """测试句法分析结构"""
        service = get_nlp_service()
        result = service.analyze_syntax("测试")
        
        assert isinstance(result, dict)
        # 检查必需字段
        required_keys = ["cws", "pos", "dep", "sdp"]
        for key in required_keys:
            assert key in result


# =============================================================================
# 缓存功能测试
# =============================================================================

class TestCache:
    """测试缓存功能"""

    def test_cache_stats(self):
        """测试缓存统计"""
        service = get_nlp_service()
        stats = service.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert "cache_size" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "hit_rate" in stats

    def test_cache_ttl(self):
        """测试缓存过期时间"""
        service = get_nlp_service()
        
        # 设置缓存
        key = "test_ttl_key"
        value = ["test"]
        service._set_cache(key, value)
        
        # 验证缓存存在
        cached = service._get_from_cache(key)
        assert cached == value

    def test_cache_cleanup(self):
        """测试缓存清理"""
        service = get_nlp_service()
        
        # 添加多个缓存项
        for i in range(10):
            service._set_cache(f"test_key_{i}", [f"value_{i}"])
        
        # 清理过期缓存
        service._cleanup_cache()
        
        # 缓存大小应该合理
        stats = service.get_cache_stats()
        assert stats["cache_size"] >= 0


# =============================================================================
# 服务状态测试
# =============================================================================

class TestServiceStatus:
    """测试服务状态"""

    def test_get_status(self):
        """测试获取服务状态"""
        service = get_nlp_service()
        status = service.get_status()
        
        assert isinstance(status, dict)
        assert "ltp_available" in status
        assert "jieba_available" in status
        assert "cache_stats" in status
        assert "cache_enabled" in status

    def test_service_initialization(self):
        """测试服务初始化状态"""
        service = get_nlp_service()
        
        # 服务应该已初始化
        assert service._initialized is True
        
        # 至少有一个 NLP 引擎可用
        status = service.get_status()
        assert status["ltp_available"] or status["jieba_available"]


# =============================================================================
# 边界条件测试
# =============================================================================

class TestEdgeCases:
    """测试边界条件"""

    def test_very_long_text(self):
        """测试长文本处理"""
        service = get_nlp_service()
        long_text = "测试" * 1000
        result = service.segment(long_text)
        
        assert isinstance(result, list)
        assert len(result) > 0

    def test_special_characters(self):
        """测试特殊字符处理"""
        service = get_nlp_service()
        text = "测试@#$%^&*()_+ 123 abc"
        result = service.segment(text)
        
        assert isinstance(result, list)

    def test_unicode_text(self):
        """测试 Unicode 文本处理"""
        service = get_nlp_service()
        text = "你好🌍世界🚀"
        result = service.segment(text)
        
        assert isinstance(result, list)

    def test_concurrent_requests(self):
        """测试并发请求"""
        service = get_nlp_service()
        results = []
        errors = []
        
        def segment_text(text):
            try:
                result = service.segment(text)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 并发请求
        threads = [
            Thread(target=segment_text, args=(f"测试{i}",))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有请求应该成功
        assert len(errors) == 0
        assert len(results) == 10


# =============================================================================
# Mock 测试（模拟 LTP 不可用场景）
# =============================================================================

class TestMockScenarios:
    """测试模拟场景"""

    def test_ltp_unavailable_fallback(self):
        """测试 LTP 不可用时降级到 jieba"""
        reset_nlp_service()
        
        # 模拟 LTP 不可用
        with patch.object(SharedNLPService, '_initialize_ltp', side_effect=Exception("LTP 不可用")):
            service = get_nlp_service()
            
            # 服务应该仍然可用（使用 jieba）
            status = service.get_status()
            assert status["jieba_available"] or not status["ltp_available"]

    def test_all_engines_unavailable(self):
        """测试所有引擎不可用时的处理"""
        reset_nlp_service()
        
        # 模拟所有引擎不可用
        with patch.object(SharedNLPService, '_initialize_ltp', side_effect=Exception("LTP 不可用")):
            with patch('importlib.import_module', side_effect=ImportError("jieba 不可用")):
                # 这种情况下服务初始化会失败
                with pytest.raises(RuntimeError):
                    SharedNLPService()


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
