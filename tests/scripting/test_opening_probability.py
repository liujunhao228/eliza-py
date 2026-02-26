#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开场白概率配置测试
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from alice.bots.lightweight_alice_bot import LightweightAliceBot
from alice.services.shared_nlp_service import SharedNLPService
from config.types import OpeningConfig


class TestOpeningProbability(unittest.TestCase):
    """开场白概率测试"""

    def setUp(self):
        """测试前准备"""
        # 模拟 NLP 服务
        self.nlp_service = MagicMock(spec=SharedNLPService)

    def test_strategy_always(self):
        """测试 always 策略：总是返回开场白"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=0.0,  # 即使概率为 0
            strategy="always",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 多次调用都应该返回开场白
        for _ in range(10):
            msg = bot.get_opening_message()
            self.assertIsNotNone(msg)

    def test_strategy_never(self):
        """测试 never 策略：从不返回开场白"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=1.0,  # 即使概率为 1
            strategy="never",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 多次调用都应该返回 None
        for _ in range(10):
            msg = bot.get_opening_message()
            self.assertIsNone(msg)

    def test_strategy_random_probability_1(self):
        """测试 random 策略：概率 1.0 总是通过"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=1.0,
            strategy="random",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 概率 1.0 应该总是返回开场白
        for _ in range(100):
            msg = bot.get_opening_message()
            self.assertIsNotNone(msg)

    def test_strategy_random_probability_0(self):
        """测试 random 策略：概率 0.0 从不通过"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=0.0,
            strategy="random",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 概率 0.0 应该总是返回 None
        for _ in range(100):
            msg = bot.get_opening_message()
            self.assertIsNone(msg)

    def test_strategy_random_probability_0_5(self):
        """测试 random 策略：概率 0.5 约 50% 通过"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=0.5,
            strategy="random",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 统计通过次数
        hits = 0
        trials = 1000
        for _ in range(trials):
            msg = bot.get_opening_message()
            if msg is not None:
                hits += 1

        # 验证通过率在 40%-60% 之间（允许一定波动）
        rate = hits / trials
        self.assertGreater(rate, 0.4)
        self.assertLess(rate, 0.6)

    def test_strategy_first_only(self):
        """测试 first_only 策略：第一次检测后保持一致"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=0.5,
            strategy="first_only",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 获取第一次结果
        first_msg = bot.get_opening_message()

        # 后续调用应该与第一次结果一致
        for _ in range(10):
            msg = bot.get_opening_message()
            if first_msg is not None:
                self.assertIsNotNone(msg)
            else:
                self.assertIsNone(msg)

    def test_disabled_opening(self):
        """测试 enabled=false"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=False,
            probability=1.0,
            strategy="always",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        # 应该返回 None
        msg = bot.get_opening_message()
        self.assertIsNone(msg)

    def test_should_send_opening(self):
        """测试 should_send_opening 方法"""
        # always 策略
        cfg_always = OpeningConfig(enabled=True, strategy="always")
        bot_always = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg_always,
            enable_logging=False,
        )
        self.assertTrue(bot_always.should_send_opening())

        # never 策略
        cfg_never = OpeningConfig(enabled=True, strategy="never")
        bot_never = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg_never,
            enable_logging=False,
        )
        self.assertFalse(bot_never.should_send_opening())

        # disabled
        cfg_disabled = OpeningConfig(enabled=False)
        bot_disabled = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg_disabled,
            enable_logging=False,
        )
        self.assertFalse(bot_disabled.should_send_opening())

    def test_get_opening_config(self):
        """测试 get_opening_config 方法"""
        cfg = OpeningConfig(
            script=Path("scripts/opening.yaml"),
            enabled=True,
            probability=0.8,
            strategy="random",
        )
        bot = LightweightAliceBot(
            nlp_service=self.nlp_service,
            opening_config=cfg,
            enable_logging=False,
        )

        returned_cfg = bot.get_opening_config()
        self.assertIsNotNone(returned_cfg)
        self.assertEqual(returned_cfg.probability, 0.8)
        self.assertEqual(returned_cfg.strategy, "random")


class TestOpeningConfigValidation(unittest.TestCase):
    """OpeningConfig 配置验证测试"""

    def test_invalid_probability_high(self):
        """测试概率 > 1.0 抛出异常"""
        with self.assertRaises(ValueError):
            OpeningConfig(probability=1.5)

    def test_invalid_probability_low(self):
        """测试概率 < 0.0 抛出异常"""
        with self.assertRaises(ValueError):
            OpeningConfig(probability=-0.1)

    def test_invalid_strategy(self):
        """测试无效策略抛出异常"""
        with self.assertRaises(ValueError):
            OpeningConfig(strategy="invalid")

    def test_valid_probability_boundary(self):
        """测试边界值有效"""
        # 0.0 应该有效
        cfg = OpeningConfig(probability=0.0)
        self.assertEqual(cfg.probability, 0.0)

        # 1.0 应该有效
        cfg = OpeningConfig(probability=1.0)
        self.assertEqual(cfg.probability, 1.0)

    def test_valid_strategies(self):
        """测试所有有效策略"""
        for strategy in ["random", "first_only", "always", "never"]:
            cfg = OpeningConfig(strategy=strategy)
            self.assertEqual(cfg.strategy, strategy)


if __name__ == '__main__':
    unittest.main()
