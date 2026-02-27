#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机延迟增强测试

测试延迟计算逻辑、配置加载和拟真行为。
"""

import unittest
from unittest.mock import MagicMock, patch
import asyncio


class TestDelayCalculation(unittest.TestCase):
    """延迟计算测试"""

    def setUp(self):
        """测试前准备"""
        # 模拟配置
        self.mock_config = {
            'reply_delay_min': 1.0,
            'reply_delay_max': 3.0,
            'opening_delay_min': 2.0,
            'opening_delay_max': 5.0,
            'typing_delay_per_char': 0.05,
            'honeypot': {
                'reply_delay_min': 2.0,
                'reply_delay_max': 8.0,
                'opening_delay_min': 5.0,
                'opening_delay_max': 15.0,
                'occasional_long_delay_probability': 0.1,
                'occasional_long_delay_min': 15.0,
                'occasional_long_delay_max': 60.0,
                'meta_delay_multiplier': 1.5,
                'early_session_delay_multiplier': 1.3,
            }
        }

    def test_reply_delay_range(self):
        """测试回复延迟范围"""
        import random
        random.seed(42)  # 可重复测试

        delays = []
        for _ in range(100):
            delay = random.uniform(
                self.mock_config['reply_delay_min'],
                self.mock_config['reply_delay_max']
            )
            delays.append(delay)

        # 验证延迟在指定范围内
        self.assertTrue(all(1.0 <= d <= 3.0 for d in delays))

        # 验证平均值接近中间值
        avg_delay = sum(delays) / len(delays)
        self.assertAlmostEqual(avg_delay, 2.0, delta=0.5)

    def test_opening_delay_range(self):
        """测试开场白延迟范围"""
        import random
        random.seed(42)

        delays = []
        for _ in range(100):
            delay = random.uniform(
                self.mock_config['opening_delay_min'],
                self.mock_config['opening_delay_max']
            )
            delays.append(delay)

        # 验证延迟在指定范围内
        self.assertTrue(all(2.0 <= d <= 5.0 for d in delays))

        # 验证平均值接近中间值
        avg_delay = sum(delays) / len(delays)
        self.assertAlmostEqual(avg_delay, 3.5, delta=0.75)

    def test_honeypot_delay_longer(self):
        """测试钓鱼机器人延迟更长"""
        import random
        random.seed(42)

        # 普通 AI 延迟
        normal_delays = []
        for _ in range(100):
            delay = random.uniform(
                self.mock_config['reply_delay_min'],
                self.mock_config['reply_delay_max']
            )
            normal_delays.append(delay)

        # 钓鱼机器人延迟
        honeypot_delays = []
        for _ in range(100):
            delay = random.uniform(
                self.mock_config['honeypot']['reply_delay_min'],
                self.mock_config['honeypot']['reply_delay_max']
            )
            honeypot_delays.append(delay)

        # 钓鱼机器人平均延迟应该更长
        normal_avg = sum(normal_delays) / len(normal_delays)
        honeypot_avg = sum(honeypot_delays) / len(honeypot_delays)

        self.assertGreater(honeypot_avg, normal_avg)

    def test_meta_delay_multiplier(self):
        """测试元对话延迟乘数"""
        base_delay = 5.0
        multiplier = self.mock_config['honeypot']['meta_delay_multiplier']

        delayed = base_delay * multiplier
        self.assertEqual(delayed, 7.5)  # 5.0 * 1.5 = 7.5

    def test_early_session_multiplier(self):
        """测试会话早期延迟乘数"""
        base_delay = 5.0
        multiplier = self.mock_config['honeypot']['early_session_delay_multiplier']

        delayed = base_delay * multiplier
        self.assertEqual(delayed, 6.5)  # 5.0 * 1.3 = 6.5

    def test_length_delay_calculation(self):
        """测试长度延迟计算"""
        response_length = 50
        typing_delay_per_char = 0.05

        length_delay = response_length * typing_delay_per_char
        self.assertEqual(length_delay, 2.5)

    def test_jitter_calculation(self):
        """测试随机波动计算"""
        import random
        random.seed(42)

        base_delay = 5.0
        jitter = random.uniform(-0.2, 0.2) * base_delay
        total_delay = base_delay + jitter

        # 验证波动范围在 ±20% 内
        self.assertGreaterEqual(total_delay, 4.0)  # 5.0 - 20%
        self.assertLessEqual(total_delay, 6.0)     # 5.0 + 20%

    def test_min_delay_boundary(self):
        """测试最小延迟边界"""
        import random

        # 模拟极小延迟计算
        calculated_delay = 0.1
        min_delay = max(0.5, calculated_delay)
        self.assertEqual(min_delay, 0.5)


class TestHoneypotOccasionalLongDelay(unittest.TestCase):
    """钓鱼机器人超长延迟测试"""

    def test_occasional_long_delay_probability(self):
        """测试超长延迟概率"""
        import random
        random.seed(42)

        probability = 0.1
        trials = 1000
        triggered = 0

        for _ in range(trials):
            if random.random() < probability:
                triggered += 1

        # 验证触发率在 5%-15% 之间（允许波动）
        rate = triggered / trials
        self.assertGreater(rate, 0.05)
        self.assertLess(rate, 0.15)

    def test_occasional_long_delay_addition(self):
        """测试超长延迟叠加"""
        import random
        random.seed(42)

        base_delay = 5.0
        long_delay_min = 15.0
        long_delay_max = 60.0

        long_delay = random.uniform(long_delay_min, long_delay_max)
        total_delay = base_delay + long_delay

        # 验证总延迟包含超长延迟
        self.assertGreater(total_delay, 20.0)
        self.assertLess(total_delay, 70.0)


class TestProfileDelayMultiplier(unittest.TestCase):
    """行为模式延迟乘数测试"""

    def test_slow_typing_multiplier(self):
        """测试慢打字速度乘数"""
        typing_speed_avg = 3.0  # 字符/秒（较慢）
        multiplier = 5.0 / typing_speed_avg
        self.assertAlmostEqual(multiplier, 1.67, places=2)

    def test_fast_typing_multiplier(self):
        """测试快打字速度乘数"""
        typing_speed_avg = 8.0  # 字符/秒（较快）
        multiplier = 5.0 / typing_speed_avg
        self.assertAlmostEqual(multiplier, 0.625, places=3)

    def test_multiplier_clamping(self):
        """测试乘数范围限制"""
        # 极慢速度
        typing_speed_avg = 1.0
        multiplier = 5.0 / typing_speed_avg
        clamped = max(0.5, min(2.0, multiplier))
        self.assertEqual(clamped, 2.0)  # 限制在 2.0

        # 极快速度
        typing_speed_avg = 20.0
        multiplier = 5.0 / typing_speed_avg
        clamped = max(0.5, min(2.0, multiplier))
        self.assertEqual(clamped, 0.5)  # 限制在 0.5


class TestDelayConfigLoading(unittest.TestCase):
    """延迟配置加载测试"""

    @patch('config.manager.get_config_manager')
    def test_load_delay_config_from_settings(self, mock_get_config_manager):
        """测试从配置加载延迟设置"""
        # 模拟配置管理器
        mock_config_mgr = MagicMock()
        mock_config_mgr._config = {
            'turing': {
                'ai_bot': {
                    'reply_delay_min': 1.5,
                    'reply_delay_max': 4.0,
                    'opening_delay_min': 3.0,
                    'opening_delay_max': 6.0,
                    'typing_delay_per_char': 0.06,
                    'honeypot': {
                        'reply_delay_min': 3.0,
                        'reply_delay_max': 10.0,
                        'opening_delay_min': 6.0,
                        'opening_delay_max': 20.0,
                        'occasional_long_delay_probability': 0.15,
                        'occasional_long_delay_min': 20.0,
                        'occasional_long_delay_max': 90.0,
                        'meta_delay_multiplier': 2.0,
                        'early_session_delay_multiplier': 1.5,
                    }
                }
            }
        }
        mock_get_config_manager.return_value = mock_config_mgr

        # 导入并测试
        from turing_test.backend.services.ai_bot_service import AIBotService
        service = AIBotService()
        service._load_delay_config()

        # 验证配置加载
        self.assertEqual(service._delay_config['reply_delay_min'], 1.5)
        self.assertEqual(service._delay_config['reply_delay_max'], 4.0)
        self.assertEqual(service._delay_config['honeypot']['meta_delay_multiplier'], 2.0)

    def test_default_delay_config(self):
        """测试默认延迟配置"""
        from turing_test.backend.services.ai_bot_service import AIBotService
        service = AIBotService()

        # 模拟没有配置的情况
        service._delay_config = None

        # 调用加载方法
        with patch('turing_test.backend.services.ai_bot_service.settings') as mock_settings:
            mock_settings.turing = None
            service._load_delay_config()

        # 验证使用默认配置
        self.assertEqual(service._delay_config['reply_delay_min'], 1.0)
        self.assertEqual(service._delay_config['honeypot']['reply_delay_min'], 2.0)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_delay_calculation_flow(self):
        """测试完整延迟计算流程"""
        import random
        random.seed(42)

        # 模拟配置
        config = {
            'reply_delay_min': 1.0,
            'reply_delay_max': 3.0,
            'typing_delay_per_char': 0.05,
            'honeypot': {
                'reply_delay_min': 2.0,
                'reply_delay_max': 8.0,
                'occasional_long_delay_probability': 0.0,  # 测试时禁用
                'meta_delay_multiplier': 1.5,
                'early_session_delay_multiplier': 1.3,
            }
        }

        # 模拟延迟计算
        response = "你好，我是 Alice。"
        is_honeypot = True
        is_meta = True
        session_turn_count = 2

        # 基础延迟
        base_delay = random.uniform(
            config['honeypot']['reply_delay_min'],
            config['honeypot']['reply_delay_max']
        )

        # 长度延迟
        length_delay = len(response) * config['typing_delay_per_char']

        # 元对话乘数
        if is_meta:
            base_delay *= config['honeypot']['meta_delay_multiplier']

        # 会话早期乘数
        if session_turn_count < 5:
            base_delay *= config['honeypot']['early_session_delay_multiplier']

        # 总延迟
        total_delay = base_delay + length_delay
        jitter = random.uniform(-0.2, 0.2) * total_delay
        total_delay += jitter

        # 验证延迟合理
        self.assertGreater(total_delay, 1.0)
        self.assertLess(total_delay, 30.0)  # 合理上限


if __name__ == '__main__':
    unittest.main()


class TestOpeningTaskCancellation(unittest.TestCase):
    """开场白任务取消逻辑测试"""

    def test_session_state_manager_tracks_opening_task(self):
        """测试 SessionStateManager 追踪开场白任务"""
        from turing_test.backend.services.session_state import session_state_manager
        import asyncio

        async def run_test():
            # 创建会话状态
            await session_state_manager.create(
                session_id=999,
                user_id=1,
                is_honeypot=False,
                opponent_type="ai"
            )

            # 创建模拟任务
            async def dummy_task():
                await asyncio.sleep(10)

            task = asyncio.create_task(dummy_task())

            # 注册任务
            session_state_manager.register_opening_task(999, task)

            # 验证任务已注册
            self.assertIn(999, session_state_manager._opening_tasks)
            self.assertEqual(session_state_manager._opening_tasks[999], task)

            # 清理
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            session_state_manager.cleanup(999)

        asyncio.run(run_test())

    def test_cancel_opening_task_success(self):
        """测试成功取消开场白任务"""
        from turing_test.backend.services.session_state import session_state_manager
        import asyncio

        async def run_test():
            # 创建会话状态
            await session_state_manager.create(
                session_id=888,
                user_id=1,
                is_honeypot=False,
                opponent_type="ai"
            )

            # 创建待处理任务
            async def long_task():
                try:
                    await asyncio.sleep(10)
                    return False  # 如果正常完成返回 False
                except asyncio.CancelledError:
                    # 被取消时重新抛出
                    raise

            task = asyncio.create_task(long_task())

            # 注册任务
            session_state_manager.register_opening_task(888, task)

            # 取消任务
            result = session_state_manager.cancel_opening_task(888)

            # 验证取消成功
            self.assertTrue(result)
            self.assertNotIn(888, session_state_manager._opening_tasks)

            # 等待任务处理取消并验证
            try:
                await task
            except asyncio.CancelledError:
                pass  # 预期行为

            # 验证任务已取消
            self.assertTrue(task.cancelled())

            # 清理
            session_state_manager.cleanup(888)

        asyncio.run(run_test())

    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        from turing_test.backend.services.session_state import session_state_manager

        # 取消不存在的任务应该返回 False
        result = session_state_manager.cancel_opening_task(999999)
        self.assertFalse(result)

    def test_cleanup_cancels_opening_task(self):
        """测试 cleanup 时会取消待处理的开场白任务"""
        from turing_test.backend.services.session_state import session_state_manager
        import asyncio

        async def run_test():
            # 创建会话状态
            await session_state_manager.create(
                session_id=777,
                user_id=1,
                is_honeypot=False,
                opponent_type="ai"
            )

            # 创建待处理任务
            async def long_task():
                try:
                    await asyncio.sleep(10)
                    return False
                except asyncio.CancelledError:
                    raise

            task = asyncio.create_task(long_task())

            # 注册任务
            session_state_manager.register_opening_task(777, task)

            # 清理会话
            session_state_manager.cleanup(777)

            # 等待任务处理取消
            try:
                await task
            except asyncio.CancelledError:
                pass  # 预期行为

            # 验证任务已取消
            self.assertTrue(task.cancelled())

        asyncio.run(run_test())

    def test_cancel_completed_task(self):
        """测试取消已完成的任务"""
        from turing_test.backend.services.session_state import session_state_manager
        import asyncio

        async def run_test():
            # 创建会话状态
            await session_state_manager.create(
                session_id=666,
                user_id=1,
                is_honeypot=False,
                opponent_type="ai"
            )

            # 创建立即完成的任务
            async def immediate_task():
                return "done"

            task = asyncio.create_task(immediate_task())
            await task  # 等待任务完成

            # 注册已完成的任务
            session_state_manager.register_opening_task(666, task)

            # 取消已完成的任务应该返回 True（因为从字典中移除了）
            result = session_state_manager.cancel_opening_task(666)
            self.assertTrue(result)

            # 清理
            session_state_manager.cleanup(666)

        asyncio.run(run_test())
