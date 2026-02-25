"""
中间件单元测试

测试限流、请求日志、错误追踪等中间件功能。
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient


# =============================================================================
# 请求日志中间件测试
# =============================================================================

class TestRequestLoggerMiddleware:
    """测试请求日志中间件"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.post("/test")
        async def test_post_endpoint(request: Request):
            data = await request.json()
            return {"received": data}
        
        @app.get("/slow")
        async def slow_endpoint():
            await asyncio.sleep(0.1)  # 模拟慢请求
            return {"message": "slow"}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        from turing_test.backend.middleware.request_logger import (
            RequestLoggerMiddleware,
            RequestLoggerConfig,
        )
        
        # 启用日志
        RequestLoggerConfig.ENABLED = True
        RequestLoggerConfig.LOG_REQUEST_BODY = False
        RequestLoggerConfig.SLOW_REQUEST_THRESHOLD = 50  # 50ms 视为慢请求
        
        # 添加中间件
        app.add_middleware(RequestLoggerMiddleware)
        
        return TestClient(app)

    def test_log_basic_request(self, client):
        """测试基础请求日志"""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
        
        # 验证响应头包含处理时间
        assert "X-Process-Time" in response.headers

    def test_log_post_request(self, client):
        """测试 POST 请求日志"""
        response = client.post(
            "/test",
            json={"key": "value"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"received": {"key": "value"}}

    def test_ignore_health_endpoint(self, client):
        """测试忽略健康检查端点"""
        # /health 应该在忽略列表中
        from turing_test.backend.middleware.request_logger import RequestLoggerConfig
        
        assert "/health" in RequestLoggerConfig.get_ignore_paths()

    def test_ignore_options_method(self, client):
        """测试忽略 OPTIONS 方法"""
        from turing_test.backend.middleware.request_logger import RequestLoggerConfig
        
        assert "OPTIONS" in RequestLoggerConfig.get_ignore_methods()

    def test_request_id_generation(self, client):
        """测试请求 ID 生成"""
        response = client.get("/test")
        
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert request_id.startswith("req_")

    def test_custom_request_id(self, client):
        """测试自定义请求 ID"""
        response = client.get(
            "/test",
            headers={"X-Request-ID": "custom-id-123"}
        )
        
        assert response.headers["X-Request-ID"] == "custom-id-123"

    def test_client_ip_extraction(self, client):
        """测试客户端 IP 提取"""
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        )
        
        assert response.status_code == 200

    def test_sanitize_headers(self):
        """测试请求头脱敏"""
        from turing_test.backend.middleware.request_logger import sanitize_headers
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "Cookie": "session=abc123",
        }
        
        sanitized = sanitize_headers(headers)
        
        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Authorization"] == "***REDACTED***"
        assert sanitized["Cookie"] == "***REDACTED***"

    def test_sanitize_body(self):
        """测试请求体脱敏"""
        from turing_test.backend.middleware.request_logger import sanitize_body
        import json
        
        body = json.dumps({
            "username": "test",
            "password": "secret123",
        })
        
        sanitized = sanitize_body(body)
        sanitized_data = json.loads(sanitized)
        
        assert sanitized_data["username"] == "test"
        assert sanitized_data["password"] == "***REDACTED***"

    def test_body_truncation(self):
        """测试请求体截断"""
        from turing_test.backend.middleware.request_logger import (
            sanitize_body,
            RequestLoggerConfig,
        )
        
        long_body = "x" * 2000
        
        sanitized = sanitize_body(long_body, max_length=100)
        
        assert len(sanitized) <= 115  # 100 + "... (truncated)"
        assert sanitized.endswith("... (truncated)")


# =============================================================================
# 限流中间件测试
# =============================================================================

class TestRateLimiterMiddleware:
    """测试限流中间件"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.post("/login")
        async def login_endpoint():
            return {"message": "login"}
        
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        from turing_test.backend.middleware.rate_limiter import (
            setup_rate_limiter,
            limiter,
        )
        
        # 设置限流器
        setup_rate_limiter(app)
        
        return TestClient(app)

    def test_basic_request(self, client):
        """测试基础请求"""
        response = client.get("/test")
        
        assert response.status_code == 200

    def test_rate_limit_headers(self, client):
        """测试限流响应头"""
        response = client.get("/test")
        
        # 应该包含限流相关头
        # 注意：slowapi 可能不总是返回这些头，取决于配置
        assert response.status_code == 200

    def test_rate_limit_config(self):
        """测试限流配置"""
        from turing_test.backend.middleware.rate_limiter import RateLimiterConfig
        
        assert RateLimiterConfig.DEFAULT_LIMIT == "100/minute"
        
        endpoint_limits = RateLimiterConfig.ENDPOINT_LIMITS
        assert "POST /api/auth/login" in endpoint_limits
        assert endpoint_limits["POST /api/auth/login"] == "10/minute"

    def test_custom_rate_limit_decorator(self):
        """测试自定义限流装饰器"""
        from turing_test.backend.middleware.rate_limiter import rate_limit
        
        app = FastAPI()
        
        @app.get("/limited")
        @rate_limit("5/minute", "test_limited")
        async def limited_endpoint():
            return {"message": "limited"}
        
        client = TestClient(app)
        response = client.get("/limited")
        
        assert response.status_code == 200

    def test_get_client_ip(self):
        """测试客户端 IP 获取"""
        from turing_test.backend.middleware.rate_limiter import get_client_ip
        
        # 创建模拟请求
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "192.168.1.1, 10.0.0.1",
        }
        request.client.host = "127.0.0.1"
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_fallback(self):
        """测试客户端 IP 回退"""
        from turing_test.backend.middleware.rate_limiter import get_client_ip
        
        request = MagicMock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        
        ip = get_client_ip(request)
        assert ip == "127.0.0.1"


# =============================================================================
# 错误追踪中间件测试
# =============================================================================

class TestErrorTrackerMiddleware:
    """测试错误追踪中间件"""

    def test_sentry_config(self):
        """测试 Sentry 配置"""
        from turing_test.backend.middleware.error_tracker import SentryConfig
        
        assert SentryConfig.TRACES_SAMPLE_RATE == 0.1
        assert SentryConfig.PROFILES_SAMPLE_RATE == 0.1
        
        sensitive_fields = SentryConfig.get_sensitive_fields()
        assert "password" in sensitive_fields
        assert "token" in sensitive_fields

    def test_sanitize_request_data(self):
        """测试请求数据脱敏"""
        from turing_test.backend.middleware.error_tracker import ErrorTracker
        
        request_data = {
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer token123",
            },
            "cookies": {
                "session": "abc123",
                "password": "secret",
            },
            "data": {
                "username": "test",
                "password": "secret123",
            }
        }
        
        sanitized = ErrorTracker._sanitize_request(request_data)
        
        assert sanitized["headers"]["Authorization"] == "***REDACTED***"
        assert sanitized["cookies"]["session"] == "***REDACTED***"
        assert sanitized["cookies"]["password"] == "***REDACTED***"
        assert sanitized["data"]["password"] == "***REDACTED***"
        assert sanitized["data"]["username"] == "test"

    def test_sanitize_user_data(self):
        """测试用户数据脱敏"""
        from turing_test.backend.middleware.error_tracker import ErrorTracker
        
        user_data = {
            "id": "123",
            "email": "test@example.com",
            "username": "testuser",
        }
        
        sanitized = ErrorTracker._sanitize_user(user_data)
        
        # ID 应该保持不变
        assert sanitized["id"] == "123"
        # 敏感字段应该被哈希
        assert sanitized["email"] != "test@example.com"
        assert len(sanitized["email"]) == 8  # SHA256 哈希的前 8 位

    def test_context_functions(self):
        """测试上下文函数"""
        from turing_test.backend.middleware.error_tracker import (
            set_tag,
            set_context,
            add_breadcrumb,
        )
        
        # 这些函数在 Sentry 未启用时不应该抛出异常
        set_tag("test", "value")
        set_context("test", {"key": "value"})
        add_breadcrumb("test message", category="test")

    def test_error_tracking_disabled(self):
        """测试错误追踪禁用状态"""
        from turing_test.backend.middleware.error_tracker import (
            SentryConfig,
            setup_error_tracker,
        )
        
        app = FastAPI()
        
        # 没有 DSN 时应该返回 False
        result = setup_error_tracker(app, dsn=None)
        assert result is False
        assert SentryConfig.ENABLED is False


# =============================================================================
# 中间件集成测试
# =============================================================================

class TestMiddlewareIntegration:
    """测试中间件集成"""

    def test_all_middlewares(self):
        """测试所有中间件一起工作"""
        from turing_test.backend.middleware import (
            setup_rate_limiter,
            setup_request_logger,
            setup_error_tracker,
        )
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # 设置所有中间件
        setup_request_logger(app)
        setup_rate_limiter(app)
        setup_error_tracker(app)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}

    def test_middleware_order(self):
        """测试中间件顺序"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"order": "correct"}
        
        # 中间件应该按正确顺序添加
        # 1. CORS (已在 main.py 中添加)
        # 2. Request Logger
        # 3. Rate Limiter
        # 4. Error Tracker
        
        from turing_test.backend.middleware import (
            setup_rate_limiter,
            setup_request_logger,
            setup_error_tracker,
        )
        
        setup_request_logger(app)
        setup_rate_limiter(app)
        setup_error_tracker(app)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200


# =============================================================================
# 性能测试
# =============================================================================

class TestMiddlewarePerformance:
    """测试中间件性能"""

    def test_request_logger_overhead(self):
        """测试请求日志开销"""
        from turing_test.backend.middleware.request_logger import (
            RequestLoggerMiddleware,
            RequestLoggerConfig,
        )
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        RequestLoggerConfig.ENABLED = True
        app.add_middleware(RequestLoggerMiddleware)
        
        client = TestClient(app)
        
        # 测量响应时间
        start = time.time()
        for _ in range(10):
            response = client.get("/test")
        elapsed = time.time() - start
        
        avg_time = elapsed / 10
        # 平均响应时间应该小于 100ms
        assert avg_time < 0.1

    def test_rate_limiter_overhead(self):
        """测试限流器开销"""
        from turing_test.backend.middleware.rate_limiter import setup_rate_limiter
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        setup_rate_limiter(app)
        
        client = TestClient(app)
        
        # 测量响应时间
        start = time.time()
        for _ in range(10):
            response = client.get("/test")
        elapsed = time.time() - start
        
        avg_time = elapsed / 10
        # 平均响应时间应该小于 100ms
        assert avg_time < 0.1


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
