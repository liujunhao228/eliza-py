# 图灵测试后端 API

基于 FastAPI 的图灵测试后端服务。

## 📦 安装

```bash
# 进入后端目录
cd turing_test/backend

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，根据需要修改配置
nano .env
```

## 🚀 运行

### 开发模式

```bash
# 使用启动脚本（从项目根目录）
python start_backend.py

# 或使用 uvicorn 直接运行
cd turing_test/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 生产模式

```bash
# 使用 gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

## 📚 API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🏗️ 项目结构

```
turing_test/backend/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理
├── database.py          # 数据库连接
├── requirements.txt      # 依赖包
├── .env.example         # 环境变量示例
├── api/                # API 路由
│   ├── __init__.py
│   ├── auth.py         # 认证相关
│   ├── user.py         # 用户相关
│   └── match.py        # 匹配相关
├── models/             # SQLAlchemy 模型
│   └── __init__.py     # 数据库表定义
├── schemas/            # Pydantic 模型
│   └── __init__.py     # API 请求/响应模型
├── websocket/          # WebSocket 端点
│   ├── __init__.py
│   ├── manager.py      # 连接管理器
│   ├── match.py        # 匹配 WebSocket
│   └── chat.py        # 聊天 WebSocket
└── migrations/        # 数据库迁移
```

## 🔌 API 端点

### 认证

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `GET /api/auth/verify/{invite_code}` - 验证邀请码

### 用户

- `GET /api/user/{user_id}` - 获取用户信息
- `GET /api/user/{user_id}/stats` - 获取用户统计
- `GET /api/user/{user_id}/score-history` - 获取积分历史
- `GET /api/user/{user_id}/sessions` - 获取用户会话

### 匹配

- `GET /api/match/status` - 获取匹配状态
- `POST /api/match/join` - 加入匹配队列
- `POST /api/match/leave` - 离开匹配队列

### WebSocket

- `WS /ws/match` - 匹配 WebSocket
- `WS /ws/chat` - 聊天 WebSocket

## 📊 数据库

### 表结构

- `users` - 用户表
- `sessions` - 会话表
- `messages` - 消息表
- `score_history` - 积分历史表
- `user_stats` - 用户统计表

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 🔧 配置

主要配置项（在 `.env` 文件中）：

- `DATABASE_URL` - 数据库连接 URL
- `SECRET_KEY` - JWT 密钥
- `MATCH_TIMEOUT` - 匹配超时时间
- `ENABLE_LTP` - 是否启用 LTP
- `BOT_POOL_MAX_INSTANCES` - 机器人池最大实例数

## 🧪 测试

```bash
# 运行测试（需要先创建测试文件）
pytest
```

## 📝 开发

### 添加新的 API 端点

1. 在 `api/` 目录下创建新的路由文件
2. 定义路由和处理器
3. 在 `main.py` 中注册路由

### 添加新的 WebSocket 端点

1. 在 `websocket/` 目录下创建新的路由文件
2. 定义 WebSocket 端点和处理逻辑
3. 在 `main.py` 中注册路由

## 🚨 待完成功能

- [ ] AliceBot 集成
- [ ] 真实的匹配逻辑
- [ ] 积分计算服务
- [ ] 数据埋点 API
- [ ] 钓鱼机器人实现
- [ ] Redis 缓存集成
- [ ] 单元测试
- [ ] 集成测试

## 📄 许可证

MIT License
