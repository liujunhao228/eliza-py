#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 重构版测试用例

测试新的模块化架构是否正常工作。
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from alice.alice_v2 import AliceBot
from alice.plugins import PluginManager, CuriosityPlugin, BasePlugin, PluginResult
from alice.managers import ConfigManager, ContextManager
from alice.core import DialogueEngine, IntentMatcher, ResponseGenerator
from alice.processors import TextPreprocessor, SemanticAnalyzer
from alice.cache import IntelligentCache


class TestPluginManager:
    """测试插件管理器"""

    def test_register_plugin(self):
        """测试插件注册"""
        manager = PluginManager()
        
        class TestPlugin(BasePlugin):
            def initialize(self):
                return True
            
            def process_input(self, text, context):
                return PluginResult(success=True, response="test response")
        
        success = manager.register_plugin(
            name="test",
            plugin_class=TestPlugin,
            config={"test": "config"},
        )
        
        assert success is True
        plugins = manager.list_plugins()
        assert any(p["name"] == "test" for p in plugins)

    def test_process_input(self):
        """测试处理输入"""
        manager = PluginManager()
        
        class TestPlugin(BasePlugin):
            def initialize(self):
                return True
            
            def process_input(self, text, context):
                return PluginResult(success=True, response=f"echo: {text}")
        
        manager.register_plugin("test", TestPlugin)
        manager.initialize_all()
        
        results = manager.process_input("hello", {})
        
        assert len(results) > 0
        assert results[0].response == "echo: hello"


class TestConfigManager:
    """测试配置管理器"""

    def test_get_set(self):
        """测试获取设置配置"""
        config = ConfigManager()
        
        config.set("test.key", "value")
        assert config.get("test.key") == "value"
        
        assert config.get("nonexistent", "default") == "default"

    def test_plugin_config(self):
        """测试插件配置"""
        config = ConfigManager()
        
        config.set("plugin.test_plugin", {"priority": 50})
        
        plugin_config = config.get("plugin.test_plugin")
        assert plugin_config["priority"] == 50


class TestContextManager:
    """测试上下文管理器"""

    def test_update_context(self):
        """测试更新上下文"""
        context = ContextManager()
        
        context.update(
            user_input="你好",
            bot_response="你好！有什么可以帮你的吗？",
            entities=[("time", "今天")],
            sentiment=0.5,
            intent="greeting",
        )
        
        summary = context.get_context_summary()
        assert summary["total_turns"] == 1

    def test_get_recent_turns(self):
        """测试获取最近对话"""
        context = ContextManager()
        
        context.update("你好", "你好")
        context.update("再见", "再见")
        
        recent = context.get_recent_turns(n=1)
        assert len(recent) == 1
        assert recent[0].user_input == "再见"


class TestTextPreprocessor:
    """测试文本预处理器"""

    def test_standardize_text(self):
        """测试文本标准化"""
        preprocessor = TextPreprocessor()
        
        text = "你好，世界！"
        standardized = preprocessor.standardize_text(text)
        
        assert "," in standardized
        assert "!" in standardized

    def test_segment_text(self):
        """测试分词"""
        preprocessor = TextPreprocessor()
        
        text = "我喜欢编程"
        tokens = preprocessor.segment_text(text)
        
        assert len(tokens) > 0


class TestSemanticAnalyzer:
    """测试语义分析器"""

    def test_analyze(self):
        """测试语义分析"""
        analyzer = SemanticAnalyzer()
        
        text = "我今天很开心"
        result = analyzer.analyze(text)
        
        assert "tokens" in result
        assert "sentiment" in result
        assert "intent" in result
        assert "entities" in result

    def test_sentiment_analysis(self):
        """测试情感分析"""
        analyzer = SemanticAnalyzer()
        
        # 使用包含明确情感词的句子
        positive_text = "开心快乐幸福"
        negative_text = "难过痛苦生气"
        
        pos_result = analyzer.analyze(positive_text)
        neg_result = analyzer.analyze(negative_text)
        
        # 检查情感分数范围
        assert pos_result["sentiment"] >= 0
        assert neg_result["sentiment"] <= 0


class TestIntentMatcher:
    """测试意图匹配器"""

    def test_match_greeting(self):
        """测试问候意图匹配"""
        matcher = IntentMatcher()
        
        match = matcher.match("你好")
        
        assert match.intent == "greeting"
        assert match.confidence > 0.7

    def test_match_question(self):
        """测试问题意图匹配"""
        matcher = IntentMatcher()
        
        match = matcher.match("为什么这样？")
        
        assert match.intent == "question"


class TestResponseGenerator:
    """测试响应生成器"""

    def test_generate_greeting(self):
        """测试生成问候响应"""
        generator = ResponseGenerator()
        
        response = generator.generate(
            user_input="你好",
            semantic_info={},
            intent="greeting",
        )
        
        assert len(response) > 0
        assert any(word in response for word in ["你好", "嗨", "你好"])

    def test_generate_fallback(self):
        """测试回退响应"""
        generator = ResponseGenerator()
        
        response = generator.generate(
            user_input="一些随机的话",
            semantic_info={},
            intent="general",
        )
        
        assert len(response) > 0


class TestIntelligentCache:
    """测试智能缓存"""

    def test_set_get(self):
        """测试设置获取缓存"""
        cache = IntelligentCache(max_size=10)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = IntelligentCache()
        
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """测试 TTL 过期"""
        cache = IntelligentCache(default_ttl=1)
        
        cache.set("key", "value", ttl=1)
        assert cache.get("key") == "value"
        
        # 等待过期
        import time
        time.sleep(1.1)
        
        assert cache.get("key") is None

    def test_lru_eviction(self):
        """测试 LRU 驱逐"""
        cache = IntelligentCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # 应该驱逐 key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"


class TestAliceBot:
    """测试 Alice 机器人"""

    def test_initialization(self):
        """测试初始化"""
        bot = AliceBot(enable_plugins=False)
        
        assert bot._initialized is True

    def test_respond(self):
        """测试响应"""
        bot = AliceBot(enable_plugins=False)
        
        response = bot.respond("你好")
        
        assert len(response) > 0
        assert isinstance(response, str)

    def test_reset(self):
        """测试重置"""
        bot = AliceBot(enable_plugins=False)
        
        bot.respond("你好")
        bot.reset()
        
        summary = bot.get_conversation_summary()
        assert summary["total_turns"] == 0

    def test_stats(self):
        """测试统计信息"""
        bot = AliceBot(enable_plugins=False)
        
        bot.respond("你好")
        
        stats = bot.get_stats()
        assert "cache" in stats
        assert "monitor" in stats
        assert "dialogue_engine" in stats


class TestDialogueEngine:
    """测试对话引擎"""

    def test_initialization(self):
        """测试初始化"""
        engine = DialogueEngine(enable_plugins=False)
        
        success = engine.initialize()
        assert success is True

    def test_respond(self):
        """测试响应生成"""
        engine = DialogueEngine(enable_plugins=False)
        engine.initialize()
        
        response = engine.respond("你好")
        
        assert len(response) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
