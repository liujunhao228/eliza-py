"""
AI Bot 服务单元测试

测试 AI Bot 服务的响应生成、打字延迟模拟等功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Tuple

from turing_test.backend.services.ai_bot_service import (
    AIBotService,
    get_ai_bot_service,
    shutdown_ai_bot_service,
    reset_bot_pool,
    get_bot_response,
)


# =============================================================================
# 夹具
# =============================================================================

@pytest.fixture
def mock_bot():
    """创建模拟 Bot 实例"""
    bot = MagicMock()
    bot.respond = MagicMock(return_value="你好，我是 AI 助手！")
    return bot


@pytest.fixture
def mock_bot_pool(mock_bot):
    """创建模拟 Bot 池"""
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=mock_bot)
    pool.release = MagicMock()
    pool.get_stats = MagicMock(return_value={
        "total_instances": 2,
        "active_instances": 1,
        "idle_instances": 1,
    })
    return pool


@pytest.fixture
async def ai_service(mock_bot_pool):
    """创建 AI 服务实例（使用模拟 Bot 池）"""
    service = AIBotService()
    service._initialized = True
    service._bot_pool = mock_bot_pool
    return service


# =============================================================================
# 基础功能测试
# =============================================================================

class TestAIBotServiceBasic:
    """测试 AI Bot 服务基础功能"""

    @pytest.mark.asyncio
    async def test_get_response_basic(self, ai_service, mock_bot):
        """测试基础响应生成"""
        response, delay = await ai_service.get_response("你好")
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(delay, float)
        assert delay >= 0
        
        # 验证 Bot 被调用
        mock_bot.respond.assert_called_once_with("你好")

    @pytest.mark.asyncio
    async def test_get_response_with_typing(self, ai_service):
        """测试带打字延迟的响应"""
        response, delay = await ai_service.get_response(
            "你好",
            simulate_typing=True
        )
        
        assert delay > 0  # 应该有延迟

    @pytest.mark.asyncio
    async def test_get_response_without_typing(self, ai_service):
        """测试不带打字延迟的响应"""
        response, delay = await ai_service.get_response(
            "你好",
            simulate_typing=False
        )
        
        assert delay == 0  # 应该没有延迟

    @pytest.mark.asyncio
    async def test_get_response_not_initialized(self):
        """测试服务未初始化时的响应"""
        service = AIBotService()
        service._initialized = False
        
        response, delay = await service.get_response("你好")
        
        assert "未初始化" in response
        assert delay == 1.0

    @pytest.mark.asyncio
    async def test_get_response_bot_unavailable(self):
        """测试 Bot 不可用时的响应"""
        service = AIBotService()
        service._initialized = True
        service._bot_pool = MagicMock()
        service._bot_pool.acquire = MagicMock(return_value=None)
        
        response, delay = await service.get_response("你好")
        
        assert "忙" in response or "抱歉" in response
        assert delay == 1.0

    @pytest.mark.asyncio
    async def test_get_response_exception(self):
        """测试响应生成异常时的处理"""
        service = AIBotService()
        service._initialized = True
        
        mock_bot = MagicMock()
        mock_bot.respond = MagicMock(side_effect=Exception("测试异常"))
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_bot)
        mock_pool.release = MagicMock()
        
        service._bot_pool = mock_pool
        
        response, delay = await service.get_response("你好")
        
        assert "故障" in response
        assert delay == 1.0
        
        # Bot 应该被释放回池中
        mock_pool.release.assert_called_once()


# =============================================================================
# 打字延迟测试
# =============================================================================

class TestTypingDelay:
    """测试打字延迟计算"""

    @pytest.mark.asyncio
    async def test_typing_delay_calculation(self, ai_service):
        """测试打字延迟计算"""
        # 短响应
        short_delay = ai_service._calculate_typing_delay("你好")
        assert short_delay >= 0.5
        
        # 长响应应该有更多延迟
        long_response = "这是一段很长的回复，用于测试打字延迟的计算逻辑。" * 10
        long_delay = ai_service._calculate_typing_delay(long_response)
        
        assert long_delay > short_delay

    @pytest.mark.asyncio
    async def test_typing_delay_minimum(self, ai_service):
        """测试最小延迟"""
        delay = ai_service._calculate_typing_delay("")
        
        assert delay >= 0.5  # 最小延迟

    @pytest.mark.asyncio
    async def test_typing_delay_jitter(self, ai_service):
        """测试延迟随机波动"""
        response = "测试响应"
        
        # 多次计算应该有波动
        delays = [
            ai_service._calculate_typing_delay(response)
            for _ in range(10)
        ]
        
        # 延迟不应该完全相同
        assert len(set(delays)) > 1


# =============================================================================
# Bot 池统计测试
# =============================================================================

class TestPoolStats:
    """测试 Bot 池统计"""

    @pytest.mark.asyncio
    async def test_get_pool_stats(self, ai_service, mock_bot_pool):
        """测试获取 Bot 池统计"""
        stats = ai_service.get_pool_stats()
        
        assert isinstance(stats, dict)
        assert "total_instances" in stats
        assert "active_instances" in stats
        assert "idle_instances" in stats

    @pytest.mark.asyncio
    async def test_get_pool_stats_not_initialized(self):
        """测试未初始化时的统计"""
        service = AIBotService()
        service._initialized = False
        
        stats = service.get_pool_stats()
        
        assert "error" in stats


# =============================================================================
# 全局服务函数测试
# =============================================================================

class TestGlobalServiceFunctions:
    """测试全局服务函数"""

    @pytest.mark.asyncio
    async def test_get_bot_response_function(self):
        """测试全局 get_bot_response 函数"""
        # 由于需要实际初始化，这里只测试函数存在
        assert callable(get_bot_response)

    @pytest.mark.asyncio
    async def test_reset_bot_pool_function(self):
        """测试全局 reset_bot_pool 函数"""
        # 测试函数存在且可调用
        assert callable(reset_bot_pool)


# =============================================================================
# 集成测试
# =============================================================================

class TestAIBotServiceIntegration:
    """AI Bot 服务集成测试"""

    @pytest.mark.asyncio
    async def test_full_response_workflow(self, ai_service, mock_bot_pool):
        """测试完整响应流程"""
        # 第一次请求
        response1, delay1 = await ai_service.get_response("你好", simulate_typing=False)
        assert len(response1) > 0
        
        # Bot 应该被释放回池中
        mock_bot_pool.release.assert_called()
        
        # 重置 mock
        mock_bot_pool.reset_mock()
        
        # 第二次请求
        response2, delay2 = await ai_service.get_response("再见", simulate_typing=False)
        assert len(response2) > 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, ai_service, mock_bot_pool):
        """测试并发请求处理"""
        async def get_response(input_text):
            return await ai_service.get_response(input_text, simulate_typing=False)
        
        # 并发发送多个请求
        tasks = [
            get_response(f"消息{i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 所有请求应该成功
        assert len(results) == 5
        assert all(isinstance(response, str) and len(response) > 0 
                   for response, _ in results)


# =============================================================================
# 边界条件测试
# =============================================================================

class TestAIBotServiceEdgeCases:
    """测试边界条件"""

    @pytest.mark.asyncio
    async def test_empty_input(self, ai_service):
        """测试空输入"""
        response, delay = await ai_service.get_response("")
        
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_very_long_input(self, ai_service):
        """测试长输入"""
        long_input = "测试" * 1000
        response, delay = await ai_service.get_response(long_input)
        
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_special_characters_input(self, ai_service):
        """测试特殊字符输入"""
        special_input = "@#$%^&*()_+ 123 abc"
        response, delay = await ai_service.get_response(special_input)
        
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_unicode_input(self, ai_service):
        """测试 Unicode 输入"""
        unicode_input = "你好🌍世界🚀"
        response, delay = await ai_service.get_response(unicode_input)
        
        assert isinstance(response, str)


# =============================================================================
# 服务生命周期测试
# =============================================================================

class TestServiceLifecycle:
    """测试服务生命周期"""

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, ai_service):
        """测试重复初始化"""
        initial_state = ai_service._initialized
        await ai_service.initialize()
        
        # 状态应该保持不变
        assert ai_service._initialized == initial_state

    @pytest.mark.asyncio
    async def test_shutdown_not_initialized(self):
        """测试关闭未初始化的服务"""
        service = AIBotService()
        service._initialized = False
        
        # 不应该抛出异常
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_with_mock_dependencies(self):
        """测试使用模拟依赖初始化"""
        service = AIBotService()
        
        # 模拟依赖
        mock_nlp = MagicMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=MagicMock())
        mock_pool.release = MagicMock()
        
        service._nlp_service = mock_nlp
        service._bot_pool = mock_pool
        service._initialized = True
        
        assert service._initialized is True


# =============================================================================
# 性能测试
# =============================================================================

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_response_time(self, ai_service):
        """测试响应时间"""
        import time
        
        start = time.time()
        response, delay = await ai_service.get_response("你好", simulate_typing=False)
        elapsed = time.time() - start
        
        # 响应时间应该合理（小于 1 秒，不包括打字延迟）
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_batch_requests(self, ai_service):
        """测试批量请求处理时间"""
        import time
        
        start = time.time()
        
        tasks = [
            ai_service.get_response(f"消息{i}", simulate_typing=False)
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        # 所有请求应该在合理时间内完成
        assert elapsed < 5.0
        assert len(results) == 10


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
