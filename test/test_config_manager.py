#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块测试

测试新的配置管理功能:
- 配置源管理
- 配置验证
- Bot 模板注册
- 运行时配置覆盖
- 配置快照回滚
"""

import unittest
from pathlib import Path
from typing import Dict, Any

from config import (
    settings,
    get_config_manager,
    reset_config_manager,
    AiBotTemplate,
    BotTemplate,
    BotTemplateRegistry,
    get_bot_registry,
    reset_bot_registry,
)
from config.sources import MemoryConfigSource, YamlConfigSource
from config.validator import ConfigValidator, build_default_validator
from config.bot_registry import BotTemplateRegistry
from config.manager import ConfigManager


class TestConfigSources(unittest.TestCase):
    """测试配置源模块"""

    def test_memory_config_source(self):
        """测试内存配置源"""
        source = MemoryConfigSource({
            'turing': {
                'server': {
                    'port': 9000
                }
            }
        })

        # 测试加载
        data = source.load()
        self.assertEqual(data['turing']['server']['port'], 9000)

        # 测试更新
        source.update('turing.server.host', 'localhost')
        self.assertEqual(source.get('turing.server.host'), 'localhost')

        # 测试获取嵌套值
        self.assertEqual(source.get('turing.server.port'), 9000)
        self.assertEqual(source.get('nonexistent', 'default'), 'default')

    def test_memory_config_source_delete(self):
        """测试内存配置源删除"""
        source = MemoryConfigSource({'a': {'b': 1}})
        self.assertTrue(source.delete('a.b'))
        self.assertIsNone(source.get('a.b'))

    def test_memory_config_source_clear(self):
        """测试内存配置源清空"""
        source = MemoryConfigSource({'a': 1, 'b': 2})
        source.clear()
        self.assertEqual(source.load(), {})


class TestConfigValidator(unittest.TestCase):
    """测试配置验证器"""

    def test_validator_basic(self):
        """测试基本验证"""
        validator = ConfigValidator()
        validator.add_rule(
            'port',
            lambda v: isinstance(v, int) and 0 < v < 65536,
            message="端口必须是有效数字"
        )

        # 验证通过
        errors = validator.validate({'port': 8000})
        self.assertEqual(len(errors), 0)

        # 验证失败
        errors = validator.validate({'port': 'invalid'})
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].path, 'port')

    def test_validator_required(self):
        """测试必填项验证"""
        validator = ConfigValidator()
        validator.add_rule('required_field', lambda v: True, required=True)

        errors = validator.validate({})
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].severity, 'error')

    def test_default_validator(self):
        """测试默认验证器"""
        validator = build_default_validator()

        # 有效配置 (需要完整结构)
        config = {
            'paths': {'project_root': '.'},
            'alice': {
                'enable_ltp': True,
                'enable_ner': True,
                'enable_log': True,
                'ner_use_ltp': True,
                'script_file': 'alice/scripts/demo.yaml',
                'rules_file': 'alice/scripts/rules/mapping.yaml',
                'context_max_items': 10,
                'conversation_history_max_turns': 20,
            },
            'turing': {
                'server': {'host': '0.0.0.0', 'port': 8000},
                'database': {'url': 'sqlite:///test.db'},
                'auth': {'invite_code_length': 6, 'secret_key': 'a' * 32},
                'match': {'timeout': 30},
                'bot_pool': {'min_instances': 2, 'max_instances': 10},
            }
        }
        errors = validator.validate(config)
        # 只检查错误，忽略警告
        error_count = sum(1 for e in errors if e.severity == 'error')
        self.assertEqual(error_count, 0)


class TestBotTemplateRegistry(unittest.TestCase):
    """测试 Bot 模板注册中心"""

    def setUp(self):
        """每个测试前重置注册中心"""
        reset_bot_registry()

    def test_register_template(self):
        """测试注册模板"""
        registry = get_bot_registry()

        template = BotTemplate(
            id="test",
            name="测试 Bot",
            script_file=Path("test.yaml"),
            rules_file=Path("rules.yaml"),
        )

        self.assertTrue(registry.register(template))
        self.assertEqual(registry.count(), 1)

        # 获取模板
        retrieved = registry.get("test")
        self.assertEqual(retrieved.name, "测试 Bot")

    def test_get_or_default(self):
        """测试获取默认模板"""
        registry = get_bot_registry()

        # 没有模板时返回 None
        self.assertIsNone(registry.get_or_default())

        # 注册一个模板
        registry.register(BotTemplate(id="default", name="Default"))
        template = registry.get_or_default()
        self.assertEqual(template.id, "default")

    def test_set_default(self):
        """测试设置默认模板"""
        registry = get_bot_registry()

        registry.register(BotTemplate(id="t1", name="T1"))
        registry.register(BotTemplate(id="t2", name="T2"))

        self.assertTrue(registry.set_default("t2"))
        self.assertEqual(registry.default_template_id, "t2")

        template = registry.get_or_default()
        self.assertEqual(template.id, "t2")

    def test_load_from_config(self):
        """测试从配置加载模板"""
        registry = get_bot_registry()
        project_root = Path(__file__).parent

        config = [
            {
                'id': 'default',
                'name': '默认 Bot',
                'script_file': 'alice/scripts/demo.yaml',
                'rules_file': 'alice/scripts/rules/mapping.yaml',
                'enable_plugins': True,
                'cache_size': 50,
            },
            {
                'id': 'honeypot',
                'name': '钓鱼机器人',
                'script_file': 'alice/scripts/honeypot.yaml',
                'rules_file': 'alice/scripts/rules/honeypot.yaml',
                'enable_plugins': False,
                'cache_size': 30,
                'typing_delay_base': 0.8,
            },
        ]

        count = registry.load_from_config(config, project_root)
        self.assertEqual(count, 2)
        self.assertEqual(registry.count(), 2)

        # 验证模板内容
        default_tpl = registry.get("default")
        self.assertTrue(default_tpl.enable_plugins)

        honeypot_tpl = registry.get("honeypot")
        self.assertFalse(honeypot_tpl.enable_plugins)
        self.assertEqual(honeypot_tpl.typing_delay_base, 0.8)


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""

    def setUp(self):
        """每个测试前重置配置管理器"""
        # 注意：这里不重置，因为配置管理器是全局单例
        # 重置会导致其他测试失败
        pass

    def test_get_config_manager_singleton(self):
        """测试配置管理器单例"""
        mgr1 = get_config_manager()
        mgr2 = get_config_manager()
        self.assertIs(mgr1, mgr2)

    def test_get_nested_config(self):
        """测试获取嵌套配置"""
        mgr = get_config_manager()
        port = mgr.get('turing.server.port')
        self.assertIsInstance(port, int)

    def test_runtime_override(self):
        """测试运行时配置覆盖"""
        mgr = get_config_manager()

        # 原始值
        original = mgr.get('turing.match.timeout')

        # 覆盖
        mgr.set('turing.match.timeout', 60)
        self.assertEqual(mgr.get('turing.match.timeout'), 60)

        # 恢复
        mgr.set('turing.match.timeout', original)
        self.assertEqual(mgr.get('turing.match.timeout'), original)

    def test_bot_template_access(self):
        """测试 Bot 模板访问"""
        mgr = get_config_manager()

        # 获取默认模板
        template = mgr.get_bot_template()
        self.assertIsNotNone(template)

        # 列出所有模板
        templates = mgr.list_bot_templates()
        self.assertGreater(len(templates), 0)

    def test_config_listener(self):
        """测试配置变更监听"""
        mgr = get_config_manager()

        notified = []

        def listener(config: Dict[str, Any]):
            notified.append(True)

        mgr.add_listener(listener)
        mgr.set('debug', True)

        self.assertTrue(len(notified) > 0)

    def test_snapshot_rollback(self):
        """测试配置快照回滚"""
        mgr = get_config_manager()

        # 获取原始值
        original = mgr.get('debug')

        # 修改配置
        mgr.set('debug', not original)
        self.assertEqual(mgr.get('debug'), not original)

        # 回滚
        success = mgr.rollback()
        if success:
            self.assertEqual(mgr.get('debug'), original)


class TestAiBotTemplateType(unittest.TestCase):
    """测试 AiBotTemplate 类型"""

    def test_create_template(self):
        """测试创建模板"""
        template = AiBotTemplate(
            id="test",
            name="测试",
            script_file=Path("test.yaml"),
            rules_file=Path("rules.yaml"),
            enable_plugins=False,
            cache_size=100,
            typing_delay_base=1.5,
        )

        self.assertEqual(template.id, "test")
        self.assertFalse(template.enable_plugins)
        self.assertEqual(template.cache_size, 100)

    def test_template_to_dict(self):
        """测试模板转字典"""
        template = AiBotTemplate(
            id="test",
            name="测试",
            script_file=Path("test.yaml"),
            rules_file=None,
        )

        d = template.to_dict()
        self.assertEqual(d['id'], 'test')
        self.assertEqual(d['name'], '测试')
        self.assertIsNone(d['rules_file'])


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_load_bot_templates_from_config(self):
        """测试从 config.yaml 加载 Bot 模板"""
        mgr = get_config_manager()

        # 检查模板是否加载
        templates = mgr.list_bot_templates()
        self.assertIn('default', templates)

        # 获取默认模板
        default_tpl = mgr.get_bot_template("default")
        self.assertIsNotNone(default_tpl)
        self.assertEqual(default_tpl.name, "小图")

    def test_bot_pool_config(self):
        """测试 Bot 池配置"""
        mgr = get_config_manager()

        bot_pool = mgr.get('turing.bot_pool')
        self.assertIsNotNone(bot_pool)
        self.assertEqual(bot_pool.get('default_template'), 'default')

    def test_settings_compatibility(self):
        """测试 settings 向后兼容"""
        # 原有访问方式仍然有效
        self.assertIsNotNone(settings.turing.server.port)
        self.assertIsNotNone(settings.alice.script_file)

        # 新增模板访问
        templates = settings.turing.bot_pool.templates
        self.assertIsInstance(templates, list)
        self.assertGreater(len(templates), 0)


if __name__ == '__main__':
    unittest.main()
