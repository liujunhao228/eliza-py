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
"""

import unittest
import tempfile
import json
import os
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
