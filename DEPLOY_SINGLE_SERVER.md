# 单服务器部署指南

适用于免费服务器/资源受限环境，前后端合并部署，只暴露一个端口。

## 架构说明

```
用户访问 https://your-domain.com
         │
         ▼
    ┌─────────────┐
    │   FastAPI   │  对外唯一入口 (8000 端口)
    │   :8000     │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐  ┌──────────┐
│前端静态  │  │ 后端 API  │
│  文件   │  │  路由     │
│         │  │  /api/*   │
└─────────┘  │  /ws/*    │
             └──────────┘
```

## 部署步骤

### 1. 构建前端

```bash
cd turing_test/frontend

# 创建生产环境配置
cat > .env.production << EOF
VITE_API_BASE_URL=/api
VITE_WS_BASE_URL=ws://your-domain.com/ws
EOF

# 构建前端（输出到后端 static 目录）
npm run build
```

### 2. 配置后端

创建或编辑根目录 `.env` 文件：

```bash
# 生产环境配置
DEBUG=false
ENVIRONMENT=production

# 服务器配置
CONFIG_TURING_SERVER_PORT=8000
CONFIG_TURING_SERVER_HOST=0.0.0.0

# 数据库配置
CONFIG_TURING_DATABASE_URL=sqlite:///data/turing.db

# 认证配置（必须修改！）
CONFIG_TURING_AUTH_SECRET_KEY=你的随机密钥

# CORS 配置（单服务器部署不需要）
# CONFIG_TURING_CORS_ORIGINS=

# 日志配置
LOG_LEVEL=WARNING
```

### 3. 初始化数据库

```bash
uv run python main.py init-db --count 100
```

### 4. 启动服务

```bash
# 使用 uvicorn 直接启动
uvicorn turing_test.backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1

# 或使用项目脚本
uv run python start_turing_test.py
```

### 5. 配置反向代理（可选）

如果使用 Nginx 反向代理（推荐）：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

## 目录结构

```
eliza-py/
├── .env                          # 后端配置
├── turing_test/
│   ├── backend/
│   │   ├── main.py               # 后端入口（含静态文件服务）
│   │   └── static/               # 前端构建输出（构建后生成）
│   │       ├── index.html
│   │       └── assets/
│   └── frontend/
│       ├── .env.production       # 前端生产配置
│       └── vite.config.ts        # Vite 配置（已配置输出目录）
```

## 环境变量说明

### 后端环境变量（`.env`）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEBUG` | 调试模式 | `false` |
| `CONFIG_TURING_SERVER_PORT` | 服务端口 | `8000` |
| `CONFIG_TURING_SERVER_HOST` | 监听地址 | `0.0.0.0` |
| `CONFIG_TURING_AUTH_SECRET_KEY` | JWT 密钥 | 必须设置 |
| `CONFIG_TURING_DATABASE_URL` | 数据库 URL | `sqlite:///data/turing.db` |
| `LOG_LEVEL` | 日志级别 | `WARNING` |

### 前端环境变量（`.env.production`）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VITE_API_BASE_URL` | API 基础路径 | `/api` |
| `VITE_WS_BASE_URL` | WebSocket 地址 | `ws://your-domain.com/ws` |

## 常见问题

### Q: 为什么访问 `/` 返回 404？
A: 确保前端已构建，`turing_test/backend/static/` 目录存在 `index.html`

### Q: WebSocket 连接失败？
A: 检查反向代理是否正确配置 `Upgrade` 和 `Connection` 头

### Q: 如何查看日志？
A: 日志文件在 `logs/turing.log`，或使用 `journalctl -u your-service` 查看系统日志

## Systemd 服务配置（Linux）

创建 `/etc/systemd/system/eliza-py.service`：

```ini
[Unit]
Description=Eliza-Py Turing Test Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/eliza-py
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn turing_test.backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable eliza-py
sudo systemctl start eliza-py
```

## Docker 部署

使用项目根目录的 `Dockerfile`：

```bash
docker build -t eliza-py .
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e CONFIG_TURING_AUTH_SECRET_KEY=your-secret-key \
  eliza-py
```
