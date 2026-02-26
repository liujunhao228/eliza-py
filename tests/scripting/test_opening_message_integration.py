#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开场白消息集成测试
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from alice.bots.lightweight_alice_bot import LightweightAliceBot
from alice.services.shared_nlp_service import SharedNLPService


class TestLightweightAliceBotOpeningMessage(unittest.TestCase):
    """LightweightAliceBot 开场白测试"""

    def setUp(self):
        """测试前准备"""
        # 模拟 NLP 服务
        self.nlp_service = MagicMock(spec=SharedNLPService)
        
        # 创建 Bot 实例，指定开场白脚本
        self.bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            script_file="scripts/yaml/demo.yaml",
            opening_script="scripts/opening.yaml",
            enable_logging=False,
            use_ltp=False,
        )

    def test_get_opening_message(self):
        """测试获取开场白"""
        msg = self.bot.get_opening_message()
        self.assertIsNotNone(msg)
        self.assertIn(msg, [
            "你好呀！",
            "在吗？",
            "哈喽～",
            "嗨，有什么可以帮你？",
            "你好，我是小图。",
        ])

    def test_get_opening_message_multiple_calls(self):
        """测试多次调用返回不同消息（随机性）"""
        messages = set()
        for _ in range(10):
            msg = self.bot.get_opening_message()
            self.assertIsNotNone(msg)
            messages.add(msg)
        
        # 验证至少获取到 2 条不同的消息
        self.assertGreater(len(messages), 1)


if __name__ == '__main__':
    unittest.main()
