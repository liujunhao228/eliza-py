#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重构后的 SharedNLPService
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alice.services.shared_nlp_service import SharedNLPService
from alice.nlp.base import NlpResult, SyntaxStructure, Entity
from alice.nlp.base import EntityType
from alice.exceptions import InputValidationError, TextProcessingError


class TestSharedNLPService(unittest.TestCase):
    """测试 SharedNLPService 类"""

    def setUp(self):
        """测试前准备"""
        # 创建服务实例
        self.service = SharedNLPService()
        
        # 模拟 LTP 引擎
        self.mock_ltp_engine = MagicMock()
        self.mock_ltp_engine.is_available = True
        self.mock_ltp_engine.analyze.return_value = NlpResult(
            text="测试文本",
            tokens=["测试", "文本"],
            syntax=SyntaxStructure(words=["测试", "文本"]),
            entities=[Entity("测试", EntityType.GENERAL, 0, 2)]
        )
        self.mock_ltp_engine.extract_entities.return_value = [
            Entity("测试", EntityType.GENERAL, 0, 2)
        ]

    def test_singleton_pattern(self):
        """测试单例模式"""
        instance1 = SharedNLPService()
        instance2 = SharedNLPService()
        self.assertIs(instance1, instance2)

    def test_input_validation(self):
        """测试输入验证"""
        # 测试空输入
        with self.assertRaises(InputValidationError):
            self.service.tokenize("")
        
        # 测试非字符串输入
        with self.assertRaises(InputValidationError):
            self.service.tokenize(123)
        
        # 测试过长输入
        long_text = "a" * 10001
        with self.assertRaises(InputValidationError):
            self.service.tokenize(long_text)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_ltp_initialization_success(self, mock_ltp_engine_class):
        """测试 LTP 引擎初始化成功"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        self.service.initialize_ltp(enable_ltp=True)
        self.assertIsNotNone(self.service._ltp_engine)
        self.assertTrue(self.service._ltp_engine.is_available)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_ltp_initialization_failure(self, mock_ltp_engine_class):
        """测试 LTP 引擎初始化失败"""
        mock_ltp_engine_class.side_effect = Exception("模型加载失败")
        
        self.service.initialize_ltp(enable_ltp=True)
        self.assertIsNone(self.service._ltp_engine)

    def test_tokenize_without_ltp(self):
        """测试没有 LTP 时的分词功能"""
        result = self.service.tokenize("测试文本")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_analyze_with_ltp(self, mock_ltp_engine_class):
        """测试有 LTP 时的分析功能"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        self.service.initialize_ltp(enable_ltp=True)
        result = self.service.analyze("测试文本")
        
        self.assertIsInstance(result, NlpResult)
        self.assertEqual(result.text, "测试文本")
        self.assertTrue(len(result.tokens) > 0)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_analyze_without_ltp(self, mock_ltp_engine_class):
        """测试没有 LTP 时的降级分析"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        # 初始化 LTP 然后禁用
        self.service.initialize_ltp(enable_ltp=True)
        self.service._ltp_engine = None
        
        result = self.service.analyze("测试文本")
        
        self.assertIsInstance(result, NlpResult)
        self.assertEqual(result.text, "测试文本")
        self.assertTrue(len(result.tokens) > 0)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_analyze_syntax_with_ltp(self, mock_ltp_engine_class):
        """测试有 LTP 时的句法分析"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        self.service.initialize_ltp(enable_ltp=True)
        result = self.service.analyze_syntax("测试文本")
        
        self.assertIsInstance(result, SyntaxStructure)
        self.assertTrue(len(result.words) > 0)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_analyze_syntax_without_ltp(self, mock_ltp_engine_class):
        """测试没有 LTP 时的降级句法分析"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        # 初始化 LTP 然后禁用
        self.service.initialize_ltp(enable_ltp=True)
        self.service._ltp_engine = None
        
        result = self.service.analyze_syntax("测试文本")
        
        self.assertIsInstance(result, SyntaxStructure)
        self.assertTrue(len(result.words) > 0)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_extract_entities_with_ltp(self, mock_ltp_engine_class):
        """测试有 LTP 时的实体抽取"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        self.service.initialize_ltp(enable_ltp=True)
        result = self.service.extract_entities("测试文本")
        
        self.assertIsInstance(result, list)
        if result:  # 如果有结果，验证实体类型
            self.assertIsInstance(result[0], Entity)

    @patch('alice.services.shared_nlp_service.LtpEngine')
    def test_extract_entities_without_ltp(self, mock_ltp_engine_class):
        """测试没有 LTP 时的降级实体抽取"""
        mock_ltp_engine_class.return_value = self.mock_ltp_engine
        
        # 初始化 LTP 然后禁用
        self.service.initialize_ltp(enable_ltp=True)
        self.service._ltp_engine = None
        
        result = self.service.extract_entities("测试文本")
        
        self.assertIsInstance(result, list)
        # 降级时应该返回空列表
        self.assertEqual(len(result), 0)

    def test_cache_functionality(self):
        """测试缓存功能"""
        # 设置缓存
        self.service.set_cached_result("test_key", "test_value", ttl=1)
        
        # 获取缓存
        result = self.service.get_cached_result("test_key")
        self.assertEqual(result, "test_value")
        
        # 清除缓存
        self.service.clear_cache()
        result = self.service.get_cached_result("test_key")
        self.assertIsNone(result)

    def test_cache_expiration(self):
        """测试缓存过期"""
        # 设置很短 TTL 的缓存
        self.service.set_cached_result("test_key", "test_value", ttl=0.1)
        
        # 立即获取，应该有值
        result = self.service.get_cached_result("test_key")
        self.assertEqual(result, "test_value")
        
        # 等待过期
        import time
        time.sleep(0.2)
        
        # 再次获取，应该为空
        result = self.service.get_cached_result("test_key")
        self.assertIsNone(result)

    def test_stats_functionality(self):
        """测试统计功能"""
        # 重置统计信息（因为单例模式，统计可能在其他测试中被修改）
        self.service._stats = {
            'total_calls': 0,
            'failed_calls': 0,
            'avg_time_ms': 0.0,
        }
        
        # 初始状态
        stats = self.service.get_stats()
        self.assertEqual(stats['total_calls'], 0)
        self.assertEqual(stats['failed_calls'], 0)
        
        # 执行一些操作
        self.service.tokenize("测试")
        
        # 检查统计
        stats = self.service.get_stats()
        self.assertEqual(stats['total_calls'], 1)
        self.assertEqual(stats['failed_calls'], 0)

    @patch('alice.services.shared_nlp_service.degradation_monitor')
    def test_degradation_monitoring(self, mock_degradation_monitor):
        """测试降级监控"""
        # 测试没有 LTP 时的降级记录
        self.service._ltp_engine = None
        self.service.analyze("测试文本")
        
        # 检查是否调用了降级监控
        mock_degradation_monitor.register_degradation.assert_called()


if __name__ == '__main__':
    unittest.main()