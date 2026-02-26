#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件集成测试脚本

验证中间件是否正确集成到主流程中。

使用方法:
    python test_middleware_integration.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_imports():
    """测试导入"""
    print("=" * 60)
    print("测试 1: 导入模块")
    print("=" * 60)
    
    try:
        from turing_test.backend.middleware import (
            setup_rate_limiter,
            setup_request_logger,
            setup_error_tracker,
        )
        print("[OK] 中间件模块导入成功")
    except ImportError as e:
        print(f"[FAIL] 中间件模块导入失败：{e}")
        return False
    
    try:
        from config import settings
        print("[OK] 配置模块导入成功")
    except ImportError as e:
        print(f"[FAIL] 配置模块导入失败：{e}")
        return False
    
    return True


def test_config():
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("测试 2: 配置加载")
    print("=" * 60)
    
    try:
        from config import settings
        
        print(f"   Debug 模式：{settings.debug}")
        print(f"   日志级别：{settings.log_level}")
        print(f"   Sentry DSN: {getattr(settings, 'sentry_dsn', '未配置')}")
        print(f"   Sentry 启用：{getattr(settings, 'sentry_enabled', False)}")
        print(f"   环境：{getattr(settings, 'environment', 'production')}")
        print("[OK] 配置加载成功")
        return True
    except Exception as e:
        print(f"[FAIL] 配置加载失败：{e}")
        return False


def test_middleware_setup():
    """测试中间件设置"""
    print("\n" + "=" * 60)
    print("测试 3: 中间件设置")
    print("=" * 60)
    
    try:
        from fastapi import FastAPI
        from turing_test.backend.middleware import (
            setup_rate_limiter,
            setup_request_logger,
            setup_error_tracker,
        )
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        # 设置中间件
        setup_request_logger(app)
        setup_rate_limiter(app)
        setup_error_tracker(app)
        
        print("[OK] 中间件设置成功")
        
        # 验证中间件已注册
        middleware_types = []
        for m in app.user_middleware:
            middleware_name = type(m).__name__
            middleware_types.append(middleware_name)
        print(f"   已注册的中间件：{middleware_types}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 中间件设置失败：{e}")
        return False


def test_request_logger():
    """测试请求日志"""
    print("\n" + "=" * 60)
    print("测试 4: 请求日志功能")
    print("=" * 60)
    
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from turing_test.backend.middleware.request_logger import (
            RequestLoggerMiddleware,
            RequestLoggerConfig,
        )
        
        # 启用日志
        RequestLoggerConfig.ENABLED = True
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        app.add_middleware(RequestLoggerMiddleware)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        assert "X-Request-ID" in response.headers
        
        print(f"   响应时间：{response.headers.get('X-Process-Time')}ms")
        print(f"   请求 ID: {response.headers.get('X-Request-ID')}")
        print("[OK] 请求日志功能正常")
        return True
    except Exception as e:
        print(f"[FAIL] 请求日志功能测试失败：{e}")
        return False


def test_rate_limiter():
    """测试限流功能"""
    print("\n" + "=" * 60)
    print("测试 5: 限流功能")
    print("=" * 60)
    
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from turing_test.backend.middleware.rate_limiter import (
            setup_rate_limiter,
            RateLimiterConfig,
        )
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        setup_rate_limiter(app)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        
        print(f"   默认限流：{RateLimiterConfig.DEFAULT_LIMIT}")
        print(f"   端点限流配置数：{len(RateLimiterConfig.ENDPOINT_LIMITS)}")
        print("[OK] 限流功能正常")
        return True
    except Exception as e:
        print(f"[FAIL] 限流功能测试失败：{e}")
        return False


def test_error_tracker():
    """测试错误追踪"""
    print("\n" + "=" * 60)
    print("测试 6: 错误追踪功能")
    print("=" * 60)
    
    try:
        from fastapi import FastAPI
        from turing_test.backend.middleware.error_tracker import (
            setup_error_tracker,
            SentryConfig,
        )
        
        app = FastAPI()
        
        # 不配置 DSN 时应该返回 False
        result = setup_error_tracker(app, dsn=None)
        
        assert result is False
        assert SentryConfig.ENABLED is False
        
        print("   Sentry DSN: 未配置")
        print("   Sentry 状态：已禁用（预期行为）")
        print("[OK] 错误追踪配置正常")
        return True
    except Exception as e:
        print(f"[FAIL] 错误追踪功能测试失败：{e}")
        return False


def test_main_app():
    """测试主应用集成"""
    print("\n" + "=" * 60)
    print("测试 7: 主应用集成")
    print("=" * 60)
    
    try:
        # 直接导入 main 模块验证集成
        from turing_test.backend import main
        
        app = main.app
        
        # 验证中间件已注册
        middleware_names = []
        for m in app.user_middleware:
            middleware_name = type(m).__name__
            if hasattr(type(m), 'name'):
                middleware_name = type(m).name
            middleware_names.append(middleware_name)
        
        print(f"   已注册中间件：{middleware_names}")
        
        # 验证路由已注册
        routes = [r.path for r in app.routes]
        print(f"   已注册路由数：{len(routes)}")
        
        print("[OK] 主应用集成正常")
        return True
    except Exception as e:
        print(f"[FAIL] 主应用集成测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("中间件集成测试")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("导入测试", test_imports()))
    results.append(("配置加载", test_config()))
    results.append(("中间件设置", test_middleware_setup()))
    results.append(("请求日志", test_request_logger()))
    results.append(("限流功能", test_rate_limiter()))
    results.append(("错误追踪", test_error_tracker()))
    results.append(("主应用集成", test_main_app()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"   {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！中间件已成功集成到主流程。")
        return 0
    else:
        print("\n[WARNING] 部分测试失败，请检查配置和代码。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
