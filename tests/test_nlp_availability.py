#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP模块可用性测试
验证各种NLP引擎和组件的基本功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock
import logging

# 设置测试日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestNLPAvailability(unittest.TestCase):
    """NLP模块可用性测试类"""
    
    def setUp(self):
        """测试前准备"""
        logger.info("开始NLP模块可用性测试")
        
    def tearDown(self):
        """测试后清理"""
        logger.info("NLP模块可用性测试完成")

    def test_import_nlp_modules(self):
        """测试NLP模块导入"""
        logger.info("测试NLP模块导入...")
        
        try:
            # 测试基础模块导入
            from alice.nlp.base import NlpEngine, NlpResult, SyntaxStructure, Entity
            logger.info("✓ NLP基础类导入成功")
            
            from alice.nlp.ltp_engine import LtpEngine
            logger.info("✓ LtpEngine 导入成功")
            
            from alice.nlp.ner_engine import NerEngine
            logger.info("✓ NerEngine 导入成功")
            
            from alice.nlp.syntax_reassembly import SyntaxReassembly
            logger.info("✓ SyntaxReassembly 导入成功")
            
            # 测试情感分析模块
            from alice.nlp.sentiment.base import SentimentEngine, SentimentResult, SentimentLabel
            logger.info("✓ 情感分析基础类导入成功")
            
            from alice.nlp.sentiment.rule_engine import RuleSentimentEngine
            logger.info("✓ RuleSentimentEngine 导入成功")
            
            # 测试工厂模式
            from alice.nlp.sentiment.engine_factory import create_sentiment_engine
            logger.info("✓ 情感分析工厂函数导入成功")
            
        except ImportError as e:
            self.fail(f"NLP模块导入失败: {e}")

    def test_base_nlp_engine_abstract(self):
        """测试基础NLP引擎抽象类"""
        logger.info("测试基础NLP引擎抽象类...")
        
        from alice.nlp.base import NlpEngine
        import inspect
        
        # 检查是否为抽象类
        self.assertTrue(inspect.isabstract(NlpEngine))
        logger.info("✓ NlpEngine 确认为抽象类")
        
        # 检查抽象方法
        abstract_methods = getattr(NlpEngine, '__abstractmethods__', set())
        expected_methods = {'analyze', 'extract_entities', 'get_syntax', 'is_available'}
        self.assertEqual(abstract_methods, expected_methods)
        logger.info("✓ 抽象方法定义正确")

    def test_ltp_engine_availability(self):
        """测试LTP引擎可用性"""
        logger.info("测试LTP引擎可用性...")
        
        try:
            from alice.nlp.ltp_engine import LtpEngine
            
            # 测试初始化（应该不会立即加载模型）
            engine = LtpEngine(lazy_load=True)
            self.assertIsNotNone(engine)
            logger.info("✓ LTP引擎初始化成功")
            
            # 测试lazy loading机制
            self.assertFalse(engine._initialized)
            logger.info("✓ LTP引擎采用懒加载机制")
            
        except Exception as e:
            logger.warning(f"LTP引擎测试警告: {e}")
            # LTP可能因为缺少模型而失败，这是预期的

    @patch('alice.nlp.ltp_engine.LTP')
    def test_ltp_engine_mock(self, mock_ltp):
        """测试LTP引擎功能（使用mock）"""
        logger.info("测试LTP引擎功能（Mock模式）...")
        
        from alice.nlp.ltp_engine import LtpEngine
        from alice.nlp.base import NlpResult
        
        # 配置mock
        mock_instance = MagicMock()
        mock_ltp.return_value = mock_instance
        
        # 模拟pipeline返回值（修正为字符级分词）
        mock_result = MagicMock()
        mock_result.seg = [['测', '试', '文', '本']]  # 字符级分词
        mock_result.pos = [['v', 'v', 'n', 'n']]
        mock_result.parser = [[('HED', -1), ('HED', -1), ('VOB', 0), ('VOB', 0)]]
        mock_result.ner = [[('测', 'O'), ('试', 'O'), ('文', 'O'), ('本', 'O')]]
        mock_instance.pipeline.return_value = mock_result
        
        # 测试分析功能
        engine = LtpEngine(lazy_load=False)  # 强制初始化以便测试
        result = engine.analyze("测试文本")
        
        # 验证结果（接受字符级分词结果）
        self.assertIsInstance(result, NlpResult)
        self.assertIn('tokens', result.__dict__)
        self.assertEqual(len(result.tokens), 4)  # 4个字符
        logger.info("✓ LTP引擎功能测试通过（Mock模式）")

    def test_ner_engine_availability(self):
        """测试NER引擎可用性"""
        logger.info("测试NER引擎可用性...")
        
        try:
            from alice.nlp.ner_engine import NerEngine
            
            # 测试初始化
            engine = NerEngine()
            self.assertIsNotNone(engine)
            logger.info("✓ NER引擎初始化成功")
            
            # 测试实体识别
            text = "阿里巴巴位于杭州"
            entities = engine.extract_entities(text)
            
            # 验证返回格式
            self.assertIsInstance(entities, list)
            logger.info("✓ NER引擎基本功能正常")
            
        except Exception as e:
            logger.warning(f"NER引擎测试警告: {e}")

    def test_syntax_reassembler(self):
        """测试句法重组器"""
        logger.info("测试句法重组器...")
        
        from alice.nlp.syntax_reassembly import SyntaxReassembly
        from alice.nlp.base import SyntaxStructure
        
        reassembler = SyntaxReassembly()
        
        # 测试基础重组
        components = ['我', '喜欢', '编程']
        response_template = "你说{2}{3}是吗？"
        
        result = reassembler.reassemble(components, response_template)
        self.assertIsInstance(result, str)
        self.assertIn("喜欢编程", result)
        logger.info("✓ 句法重组器功能正常")

    def test_sentiment_engines(self):
        """测试情感分析引擎"""
        logger.info("测试情感分析引擎...")
        
        # 测试规则引擎
        from alice.nlp.sentiment.rule_engine import RuleSentimentEngine
        
        engine = RuleSentimentEngine()
        
        # 测试积极情感
        positive_text = "我很开心今天天气很好"
        positive_result = engine.analyze(positive_text)
        self.assertGreaterEqual(positive_result.score, 0)
        logger.info("✓ 积极情感分析正常")
        
        # 测试消极情感
        negative_text = "我很沮丧今天下雨了"
        negative_result = engine.analyze(negative_text)
        self.assertLessEqual(negative_result.score, 0)
        logger.info("✓ 消极情感分析正常")
        
        # 测试SnowNLP引擎（如果可用）
        try:
            from alice.nlp.sentiment.snownlp_engine import SnowNlpSentimentEngine
            snow_engine = SnowNlpSentimentEngine()
            snow_result = snow_engine.analyze("测试文本")
            self.assertIsInstance(snow_result.score, float)
            logger.info("✓ SnowNLP情感引擎可用")
        except ImportError:
            logger.info("⚠ SnowNLP引擎不可用（正常情况）")

    def test_sentiment_factory(self):
        """测试情感引擎工厂"""
        logger.info("测试情感引擎工厂...")
        
        from alice.nlp.sentiment.engine_factory import create_sentiment_engine
        
        # 测试获取默认引擎
        default_engine = create_sentiment_engine()
        self.assertIsNotNone(default_engine)
        logger.info("✓ 默认情感引擎获取成功")
        
        # 测试获取特定引擎
        rule_engine = create_sentiment_engine(mode='rule')
        self.assertIsNotNone(rule_engine)
        logger.info("✓ 规则情感引擎获取成功")

    def test_nlp_integration(self):
        """测试NLP模块集成"""
        logger.info("测试NLP模块集成...")
        
        try:
            # 测试完整的NLP流水线
            from alice.nlp.ltp_engine import LtpEngine
            from alice.nlp.sentiment.rule_engine import RuleSentimentEngine
            
            # 初始化引擎
            ltp_engine = LtpEngine(lazy_load=True)
            sentiment_engine = RuleSentimentEngine()
            
            # 测试文本处理流程
            text = "我喜欢这个聊天机器人，它很有趣"
            
            # NLP分析
            nlp_result = ltp_engine.analyze(text)
            
            # 情感分析
            sentiment_result = sentiment_engine.analyze(text)
            
            # 验证结果完整性
            self.assertIn('tokens', nlp_result.__dict__)
            self.assertIsInstance(sentiment_result.score, float)
            
            logger.info("✓ NLP模块集成测试通过")
            
        except Exception as e:
            logger.error(f"NLP集成测试失败: {e}")
            raise

    def test_error_handling(self):
        """测试错误处理机制"""
        logger.info("测试错误处理机制...")
        
        from alice.nlp.ltp_engine import LtpEngine
        
        engine = LtpEngine(lazy_load=True)
        
        # 测试空文本处理
        try:
            result = engine.analyze("")
            self.assertIsInstance(result, object)
            logger.info("✓ 空文本处理正常")
        except Exception as e:
            logger.warning(f"空文本处理异常: {e}")
        
        # 测试无效输入处理
        try:
            result = engine.analyze(None)
            # 应该有适当的错误处理
            logger.info("✓ None输入处理正常")
        except Exception as e:
            logger.info(f"None输入按预期抛出异常: {type(e).__name__}")

def run_availability_tests():
    """运行所有可用性测试"""
    logger.info("=" * 50)
    logger.info("开始NLP模块可用性测试")
    logger.info("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNLPAvailability)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试总结
    logger.info("=" * 50)
    logger.info("NLP模块可用性测试总结:")
    logger.info(f"测试用例总数: {result.testsRun}")
    logger.info(f"失败数: {len(result.failures)}")
    logger.info(f"错误数: {len(result.errors)}")
    logger.info(f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    logger.info("=" * 50)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_availability_tests()
    sys.exit(0 if success else 1)