# 中间件配置指南

本文档介绍图灵测试后端新增的中间件功能及其配置方法。

## 目录

- [概述](#概述)
- [API 限流中间件](#api-限流中间件)
- [请求日志中间件](#请求日志中间件)
- [Sentry 错误追踪](#sentry-错误追踪)
- [配置说明](#配置说明)
- [使用示例](#使用示例)

---

## 概述

本项目已集成以下中间件功能：

| 中间件 | 功能 | 默认状态 |
|--------|------|----------|
| 限流中间件 | 防止 API 滥用，基于 IP 的速率限制 | ✅ 启用 |
| 请求日志 | 记录所有请求的详细信息 | ✅ 启用 |
| Sentry 错误追踪 | 生产环境错误监控和性能追踪 | ⚠️ 需配置 DSN |

---

## API 限流中间件

使用 [slowapi](https://github.com/laurentS/slowapi) 实现基于 IP 的速率限制。

### 默认配置

```python
# 默认限流策略
DEFAULT_LIMIT = "100/minute"  # 每分钟 100 次请求

# 特定端点限流策略
ENDPOINT_LIMITS = {
    # 认证端点 - 更严格的限制（防止暴力破解）
    "POST /api/auth/login": "10/minute",
    "POST /api/auth/register": "5/minute",
    
    # 邀请码端点 - 中等限制
    "POST /api/invite-codes/*": "20/minute",
    "GET /api/invite-codes/*": "30/minute",
    
    # 匹配端点 - 中等限制
    "POST /api/match/*": "30/minute",
    
    # 聊天端点 - 较宽松的限制
    "POST /api/chat/*": "60/minute",
    
    # 健康检查 - 宽松限制
    "GET /health": "30/minute",
}
```

### 自定义限流配置

编辑 `turing_test/backend/middleware/rate_limiter.py`:

```python
class RateLimiterConfig:
    # 修改默认限流
    DEFAULT_LIMIT: str = "200/minute"
    
    # 添加新的端点限流
    ENDPOINT_LIMITS: Dict[str, str] = {
        ...
    }
```

### 在路由中使用限流装饰器

```python
from turing_test.backend.middleware.rate_limiter import rate_limit

@app.post("/sensitive")
@rate_limit("5/minute", "sensitive_operation")
async def sensitive_endpoint():
    ...
```

### 限流响应

当触发限流时，返回以下响应：

```json
{
    "success": false,
    "error_code": "RATE_LIMIT_EXCEEDED",
    "message": "请求过于频繁，请稍后再试",
    "retry_after": 60
}
```

---

## 请求日志中间件

记录所有 HTTP 请求的详细信息。

### 日志内容

每个请求记录以下信息：

- 请求方法、路径、IP
- 请求 ID（用于追踪）
- 响应状态码
- 处理时间
- 响应大小

### 日志示例

```
📥 请求开始 | GET /api/user/profile | IP: 192.168.1.1 | Request ID: req_1234567890
📤 请求完成 | GET /api/user/profile | Status: 200 | Time: 45.23ms | Size: 256B
```

### 慢请求检测

处理时间超过阈值的请求会被标记为慢请求：

```
🐢 慢请求警告 | POST /api/match/find | 耗时：1523.45ms
```

### 配置选项

编辑 `turing_test/backend/middleware/request_logger.py`:

```python
class RequestLoggerConfig:
    # 是否启用日志
    ENABLED: bool = True
    
    # 是否记录请求体
    LOG_REQUEST_BODY: bool = False
    
    # 是否记录响应体
    LOG_RESPONSE_BODY: bool = False
    
    # 请求体最大记录长度
    MAX_BODY_LENGTH: int = 1000
    
    # 需要忽略的路径
    IGNORE_PATHS = ["/health", "/docs", "/redoc"]
    
    # 慢请求阈值（毫秒）
    SLOW_REQUEST_THRESHOLD: int = 1000
```

### 敏感信息脱敏

以下字段会自动脱敏：

- `password`
- `token`
- `secret`
- `api_key`
- `authorization`
- `cookie`

---

## Sentry 错误追踪

集成 [Sentry](https://sentry.io/) 进行生产环境错误监控。

### 配置 DSN

1. 在 Sentry 创建项目并获取 DSN
2. 在环境变量中设置：

```bash
# .env 文件
SENTRY_DSN=https://your-dsn@sentry.io/your-project-id
```

或在 `config.yaml` 中配置：

```yaml
sentry:
  dsn: "https://your-dsn@sentry.io/your-project-id"
  enabled: true
```

### 配置选项

编辑 `turing_test/backend/middleware/error_tracker.py`:

```python
class SentryConfig:
    # 环境名称
    ENVIRONMENT: str = "production"
    
    # 性能追踪采样率
    TRACES_SAMPLE_RATE: float = 0.1  # 10%
    
    # 性能分析采样率
    PROFILES_SAMPLE_RATE: float = 0.1  # 10%
    
    # 需要忽略的异常类型
    IGNORE_EXCEPTIONS = (HTTPException,)
```

### 手动捕获异常

```python
from turing_test.backend.middleware.error_tracker import (
    capture_exception,
    capture_message,
    set_user_context,
    add_breadcrumb,
)

# 捕获异常
try:
    ...
except Exception as e:
    capture_exception(e, extra_info={"user_id": 123})

# 发送消息
capture_message("重要事件", level="warning")

# 设置用户上下文
set_user_context(user_id="123", username="testuser")

# 添加面包屑日志
add_breadcrumb("用户执行操作", category="action", level="info")
```

### 性能追踪

```python
from turing_test.backend.middleware.error_tracker import (
    start_transaction,
)

# 手动追踪事务
with start_transaction(name="process_data", op="task"):
    # 执行任务
    ...
```

---

## 配置说明

### 环境变量

```bash
# Sentry DSN（可选，生产环境建议配置）
SENTRY_DSN=https://your-dsn@sentry.io/your-project-id

# 环境
ENVIRONMENT=production  # 或 development
```

### 中间件配置汇总

所有中间件配置位于 `turing_test/backend/middleware/` 目录：

```
middleware/
├── __init__.py           # 模块导出
├── rate_limiter.py       # 限流中间件配置
├── request_logger.py     # 请求日志配置
└── error_tracker.py      # Sentry 错误追踪配置
```

---

## 使用示例

### 1. 开发环境调试

在开发环境中，建议：

```python
# request_logger.py
RequestLoggerConfig.LOG_REQUEST_BODY = True  # 记录请求体便于调试
RequestLoggerConfig.SLOW_REQUEST_THRESHOLD = 500  # 降低慢请求阈值
```

### 2. 生产环境配置

在生产环境中，建议：

```python
# rate_limiter.py
RateLimiterConfig.DEFAULT_LIMIT = "100/minute"  # 严格限流

# request_logger.py
RequestLoggerConfig.LOG_REQUEST_BODY = False  # 不记录请求体，保护隐私
RequestLoggerConfig.LOG_RESPONSE_BODY = False

# error_tracker.py
SentryConfig.TRACES_SAMPLE_RATE = 0.1  # 10% 采样率
SentryConfig.ENABLED = True  # 启用 Sentry
```

### 3. 高并发场景

在高并发场景下，建议：

```python
# rate_limiter.py
RateLimiterConfig.DEFAULT_LIMIT = "50/minute"  # 更严格的限流

# 使用 Redis 存储限流数据（而非内存）
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri="redis://localhost:6379",
)
```

---

## 测试

### 运行中间件测试

```bash
cd turing_test/backend

# 运行所有中间件测试
pytest test_middleware.py -v

# 运行特定测试
pytest test_middleware.py::TestRequestLoggerMiddleware -v
pytest test_middleware.py::TestRateLimiterMiddleware -v
pytest test_middleware.py::TestErrorTrackerMiddleware -v
```

### 测试限流

```bash
# 快速发送多个请求测试限流
for i in {1..20}; do
    curl http://localhost:8000/api/auth/login \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"invite_code": "TEST"}'
done
```

### 测试错误追踪

```bash
# 触发测试错误（如果启用了 /sentry-debug 端点）
curl http://localhost:8000/sentry-debug
```

---

## 故障排除

### 限流不生效

1. 检查 slowapi 是否正确安装
2. 确认中间件已添加到 FastAPI 应用
3. 检查限流配置是否正确

### 日志不输出

1. 检查 `RequestLoggerConfig.ENABLED` 是否为 `True`
2. 确认路径不在忽略列表中
3. 检查 loguru 配置

### Sentry 不发送错误

1. 检查 DSN 是否正确配置
2. 确认网络连接正常
3. 检查 `SentryConfig.ENABLED` 是否为 `True`
4. 查看本地日志是否有 Sentry 相关错误

---

## 相关文件

- `turing_test/backend/main.py` - 中间件集成入口
- `turing_test/backend/middleware/` - 中间件实现
- `turing_test/backend/test_middleware.py` - 中间件测试

---

## 参考资料

- [SlowAPI 文档](https://slowapi.readthedocs.io/)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [FastAPI 中间件](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Loguru 文档](https://loguru.readthedocs.io/)
