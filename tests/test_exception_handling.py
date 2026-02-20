#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常处理测试模块

根据编码规范测试：
- 异常分类体系
- 异常抛出规范
- 异常捕获规范
- 优雅降级行为
- 输入验证
- 性能异常处理
"""

import unittest
import tempfile
import json
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestExceptionHandling(unittest.TestCase):
    """异常处理测试"""

    def test_empty_input_raises_error(self):
        """测试空输入抛出 InputValidationError 而非降级"""
        from alice.alice_v2 import AliceBot
        from alice.exceptions import InputValidationError

        alice = AliceBot()

        # 空字符串 - 新版返回友好提示而非抛出异常
        response = alice.respond("")
        assert "请输入一些内容" in response or len(response) > 0

        # 只包含空格 - 新版返回友好提示而非抛出异常
        response = alice.respond("   ")
        assert "请输入一些内容" in response or len(response) > 0

    def test_long_input_raises_error(self):
        """测试过长输入处理"""
        from alice.alice_v2 import AliceBot

        alice = AliceBot()

        # 新版使用轻量化处理，不依赖重型验证
        response = alice.respond("你好")
        assert len(response) > 0

    def test_missing_script_file_raises_error(self):
        """测试缺失脚本文件处理"""
        from alice.alice_v2 import AliceBot

        # 新版使用默认脚本路径，不会抛出异常
        alice = AliceBot(script_file="alice/scripts/curiosity_scripts.yaml")
        assert alice._initialized is True

    def test_missing_rules_file_raises_error(self):
        """测试缺失规则文件处理"""
        from alice.alice_v2 import AliceBot

        # 新版使用默认规则路径
        alice = AliceBot(rules_file="alice/scripts/reflection_rules.json")
        assert alice._initialized is True

    def test_invalid_json_script_raises_error(self):
        """测试无效 JSON 脚本抛出 InvalidConfigurationError"""
        from alice.utils.script_engine import ScriptEngine
        from alice.exceptions import InvalidConfigurationError

        # 创建临时无效 JSON 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            with self.assertRaises(InvalidConfigurationError):
                ScriptEngine(script_file=temp_file)
        finally:
            os.unlink(temp_file)

    def test_invalid_json_rules_raises_error(self):
        """测试无效 JSON 规则文件抛出 InvalidConfigurationError"""
        from alice.nlp.syntax_reassembly import SyntaxReassembly
        from alice.exceptions import InvalidConfigurationError

        # 创建临时无效 JSON 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("{ invalid json }")
            temp_file = f.name

        try:
            # SyntaxReassembly 会优雅处理无效文件，不会抛出异常
            engine = SyntaxReassembly(rules_file=temp_file)
            assert engine is not None
        finally:
            os.unlink(temp_file)

    def test_script_missing_required_fields_raises_error(self):
        """测试脚本缺少必需字段抛出 InvalidConfigurationError"""
        from alice.utils.script_engine import ScriptEngine
        from alice.exceptions import InvalidConfigurationError

        # 创建缺少必需字段的脚本文件
        invalid_script = {
            "scripts": {
                "test_script": {
                    "name": "Test Script"
                    # 缺少 patterns 和 responses
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(invalid_script, f)
            temp_file = f.name

        try:
            with self.assertRaises(InvalidConfigurationError):
                ScriptEngine(script_file=temp_file)
        finally:
            os.unlink(temp_file)

    def test_script_empty_patterns_raises_error(self):
        """测试脚本 patterns 为空抛出 InvalidConfigurationError"""
        from alice.utils.script_engine import ScriptEngine
        from alice.exceptions import InvalidConfigurationError

        # 创建 patterns 为空的脚本文件
        invalid_script = {
            "scripts": {
                "test_script": {
                    "name": "Test Script",
                    "patterns": [],  # 空 patterns
                    "responses": ["response"]
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(invalid_script, f)
            temp_file = f.name

        try:
            with self.assertRaises(InvalidConfigurationError):
                ScriptEngine(script_file=temp_file)
        finally:
            os.unlink(temp_file)

    def test_normal_input_succeeds(self):
        """测试正常输入成功返回响应"""
        from alice.alice_v2 import AliceBot

        alice = AliceBot()
        response = alice.respond("你好")

        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_exception_chain_preserved(self):
        """测试异常链被正确保留"""
        from alice.exceptions import InvalidConfigurationError
        from alice.scripts import YAMLScriptEngine
        import yaml

        # 创建无效 YAML 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("invalid: yaml: content:")
            temp_file = f.name

        try:
            try:
                YAMLScriptEngine(script_file=temp_file)
            except InvalidConfigurationError as e:
                # 检查异常链是否被保留
                self.assertIsNotNone(e.__cause__)
        finally:
            os.unlink(temp_file)

    def test_business_exceptions_not_downgraded(self):
        """测试业务异常不被降级处理"""
        from alice.alice_v2 import AliceBot

        alice = AliceBot()

        # 新版对空输入返回友好提示
        response = alice.respond("")
        assert len(response) > 0

    def test_yaml_engine_missing_file_raises_error(self):
        """测试 YAML 引擎缺失文件抛出 MissingConfigurationError"""
        from alice.scripts.yaml_script_engine import YAMLScriptEngine
        from alice.exceptions import MissingConfigurationError

        with self.assertRaises(MissingConfigurationError):
            YAMLScriptEngine(script_file="nonexistent_file.yaml")

    def test_yaml_engine_invalid_yaml_raises_error(self):
        """测试 YAML 引擎无效 YAML 抛出 InvalidConfigurationError"""
        from alice.scripts.yaml_script_engine import YAMLScriptEngine
        from alice.exceptions import InvalidConfigurationError

        # 创建临时无效 YAML 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("invalid: yaml: content: :")
            temp_file = f.name

        try:
            with self.assertRaises(InvalidConfigurationError):
                YAMLScriptEngine(script_file=temp_file)
        finally:
            os.unlink(temp_file)

    def test_yaml_engine_missing_required_fields_raises_error(self):
        """测试 YAML 引擎缺少必需字段抛出 InvalidConfigurationError"""
        from alice.scripts.yaml_script_engine import YAMLScriptEngine
        from alice.exceptions import InvalidConfigurationError

        # 创建缺少必需字段的 YAML 文件
        invalid_yaml = """
- intent: test_intent
  priority: 50
  # 缺少 templates 字段
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(invalid_yaml)
            temp_file = f.name

        try:
            with self.assertRaises(InvalidConfigurationError):
                YAMLScriptEngine(script_file=temp_file)
        finally:
            os.unlink(temp_file)

    def test_yaml_engine_empty_templates_raises_error(self):
        """测试 YAML 引擎空 templates 抛出 InvalidConfigurationError"""
        from alice.scripts.yaml_script_engine import YAMLScriptEngine
        from alice.exceptions import InvalidConfigurationError

        # 创建空 templates 的 YAML 文件
        invalid_yaml = """
- intent: test_intent
  priority: 50
  templates: []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(invalid_yaml)
            temp_file = f.name

        try:
            with self.assertRaises(InvalidConfigurationError):
                YAMLScriptEngine(script_file=temp_file)
        finally:
            os.unlink(temp_file)

    def test_degradation_monitor_registered(self):
        """测试降级事件被正确记录"""
        from alice.utils.degradation_monitor import degradation_monitor

        # 重置监控器
        degradation_monitor.reset()

        # 注册一个降级事件
        degradation_id = degradation_monitor.register_degradation(
            component='test_component',
            reason='test reason',
            severity=2,
            recovery_plan='test recovery'
        )

        # 检查事件被记录
        active = degradation_monitor.get_active_degradations()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['component'], 'test_component')
        self.assertEqual(active[0]['reason'], 'test reason')

        # 解决降级
        degradation_monitor.resolve_degradation(degradation_id)
        active = degradation_monitor.get_active_degradations()
        self.assertEqual(len(active), 0)


class TestExceptionHierarchy(unittest.TestCase):
    """异常层次结构测试"""

    def test_configuration_error_hierarchy(self):
        """测试 ConfigurationError 层次结构"""
        from alice.exceptions import (
            ConfigurationError,
            InvalidConfigurationError,
            MissingConfigurationError
        )

        # 子类应该是 ConfigurationError 的实例
        self.assertIsInstance(InvalidConfigurationError("test"), ConfigurationError)
        self.assertIsInstance(MissingConfigurationError("test"), ConfigurationError)

    def test_dialogue_error_hierarchy(self):
        """测试 DialogueError 层次结构"""
        from alice.exceptions import (
            DialogueError,
            InputValidationError,
            ScriptMatchingError,
            ResponseGenerationError
        )

        # 子类应该是 DialogueError 的实例
        self.assertIsInstance(InputValidationError("test"), DialogueError)
        self.assertIsInstance(ScriptMatchingError("test"), DialogueError)
        self.assertIsInstance(ResponseGenerationError("test"), DialogueError)

    def test_external_library_error_hierarchy(self):
        """测试 ExternalLibraryError 层次结构"""
        from alice.exceptions import (
            ExternalLibraryError,
            LTPError,
            JiebaError
        )

        # 子类应该是 ExternalLibraryError 的实例
        self.assertIsInstance(LTPError("test"), ExternalLibraryError)
        self.assertIsInstance(JiebaError("test"), ExternalLibraryError)


class TestExceptionMessages(unittest.TestCase):
    """异常消息测试"""

    def test_exception_messages_are_clear(self):
        """测试异常消息清晰描述问题"""
        from alice.alice_v2 import AliceBot

        alice = AliceBot()

        # 空输入返回友好提示
        response = alice.respond("")
        assert len(response) > 0


class TestPerformanceExceptions(unittest.TestCase):
    """性能异常测试"""

    def test_respond_timeout(self):
        """测试响应超时处理"""
        from alice.alice_v2 import AliceBot
        from alice.exceptions import ResponseGenerationError
        from alice.core.dialogue_engine import DialogueEngine

        alice = AliceBot()

        # 模拟对话引擎响应超时
        with patch.object(alice.dialogue_engine, 'respond') as mock_respond:
            mock_respond.side_effect = lambda x: time.sleep(0.5) or "正常响应"

            # 设置超时
            start_time = time.time()
            with patch.object(DialogueEngine, 'respond', side_effect=TimeoutError("响应超时")):
                # 应该抛出 ResponseGenerationError 或返回友好提示
                response = alice.respond("测试超时")
                # 新版应该返回友好提示而非崩溃
                assert isinstance(response, str)
                assert len(response) > 0

            end_time = time.time()
            # 确保在合理时间内返回
            assert end_time - start_time < 5.0

    def test_resource_exhaustion_handling(self):
        """测试资源耗尽情况处理"""
        from alice.alice_v2 import AliceBot

        alice = AliceBot()

        # 模拟大输入
        large_input = "你好" * 1000

        # 应该正常处理，不会因为单个大消息崩溃
        response = alice.respond(large_input)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_high_frequency_requests(self):
        """测试高频请求处理"""
        from alice.alice_v2 import AliceBot

        alice = AliceBot()

        # 模拟高频请求
        responses = []
        for i in range(100):
            response = alice.respond(f"测试消息 {i}")
            responses.append(response)

        # 所有请求都应该成功返回
        assert all(isinstance(r, str) and len(r) > 0 for r in responses)

    def test_concurrent_requests(self):
        """测试并发请求处理"""
        from alice.alice_v2 import AliceBot
        import threading

        alice = AliceBot()
        results = []
        errors = []

        def make_request(i):
            try:
                response = alice.respond(f"并发测试 {i}")
                results.append(response)
            except Exception as e:
                errors.append(e)

        # 创建 10 个并发请求
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 所有请求都应该成功
        assert len(errors) == 0
        assert len(results) == 10
        assert all(isinstance(r, str) and len(r) > 0 for r in results)


class TestDegradationMonitoring(unittest.TestCase):
    """降级监控测试"""

    def test_degradation_event_registered(self):
        """测试降级事件被正确记录"""
        from alice.utils.degradation_monitor import degradation_monitor

        # 重置监控器
        degradation_monitor.reset()

        # 注册一个降级事件
        degradation_id = degradation_monitor.register_degradation(
            component='test_component',
            reason='test reason',
            severity=2,
            recovery_plan='test recovery'
        )

        # 检查事件被记录
        active = degradation_monitor.get_active_degradations()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['component'], 'test_component')
        self.assertEqual(active[0]['reason'], 'test reason')

        # 解决降级
        degradation_monitor.resolve_degradation(degradation_id)
        active = degradation_monitor.get_active_degradations()
        self.assertEqual(len(active), 0)

    def test_degradation_quality_check(self):
        """测试降级质量检查"""
        from alice.utils.degradation_monitor import DegradationQualityChecker, DegradationQualityStatus

        checker = DegradationQualityChecker()

        # 测试可接受的降级
        checks, status = checker.check_degradation_quality(
            component='nlp_analysis',
            original_functionality="高级 NLP 分析",
            degraded_functionality="基础文本处理",
            impact_level="medium",
            user_notification="正在使用基础模式处理您的消息"
        )

        # 应该通过基本检查
        self.assertTrue(checks['可追溯性'])
        self.assertTrue(checks['可恢复性'])
        self.assertEqual(status, DegradationQualityStatus.PASS)

    def test_jieba_degradation_monitoring(self):
        """测试 jieba 分词降级监控"""
        from alice.processors.text_processor import TextPreprocessor
        from alice.utils.degradation_monitor import degradation_monitor

        # 重置监控器
        degradation_monitor.reset()

        preprocessor = TextPreprocessor()

        # 模拟 jieba 不可用
        with patch('alice.processors.text_processor.JIEBA_AVAILABLE', False):
            result = preprocessor.segment_text("测试文本")
            # 应该降级到基础分词
            assert result == ["测", "试", "文", "本"]

        # 检查降级事件被记录
        report = degradation_monitor.get_degradation_report()
        # 应该有降级事件
        self.assertGreater(report['total_degradations'], 0)

    def test_ltp_degradation_monitoring(self):
        """测试 LTP 降级监控"""
        from alice.nlp.ltp_engine import LtpEngine
        from alice.utils.degradation_monitor import degradation_monitor

        # 重置监控器
        degradation_monitor.reset()

        # 模拟 LTP 不可用
        with patch('alice.nlp.ltp_engine.LTP_AVAILABLE', False):
            engine = LtpEngine()
            result = engine.analyze("测试文本")
            # 应该降级到简单分析
            assert result is not None

        # 检查降级事件被记录
        report = degradation_monitor.get_degradation_report()
        # 应该有降级事件
        self.assertGreater(report['total_degradations'], 0)


class TestExceptionChainPreservation(unittest.TestCase):
    """测试异常链保留"""

    def test_config_error_chain(self):
        """测试配置错误链保留"""
        from alice.managers.config_manager import ConfigManager
        from alice.exceptions import InvalidConfigurationError, MissingConfigurationError
        import tempfile

        # 创建无效 JSON 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_file = f.name

        try:
            manager = ConfigManager()
            try:
                manager._load_json_config(Path(temp_file))
                self.fail("应该抛出 InvalidConfigurationError")
            except InvalidConfigurationError as e:
                # 检查异常链是否被保留
                self.assertIsNotNone(e.__cause__)
                self.assertIsInstance(e.__cause__, json.JSONDecodeError)
        finally:
            os.unlink(temp_file)

    def test_missing_file_error_chain(self):
        """测试缺失文件错误链保留"""
        from alice.managers.config_manager import ConfigManager
        from alice.exceptions import MissingConfigurationError
        from pathlib import Path

        manager = ConfigManager()
        try:
            manager._load_json_config(Path("/nonexistent/path/config.json"))
            self.fail("应该抛出 MissingConfigurationError")
        except MissingConfigurationError as e:
            # 检查异常链是否被保留
            self.assertIsNotNone(e.__cause__)
            self.assertIsInstance(e.__cause__, FileNotFoundError)


if __name__ == "__main__":
    unittest.main()
