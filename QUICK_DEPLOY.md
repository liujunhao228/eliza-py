# Eliza-Py 快速部署参考

## Docker 部署（免费云服务器）

### 构建镜像
```bash
docker build -t eliza-py .
```

### 本地测试
```bash
docker run -p 8000:8000 eliza-py
# 访问 http://localhost:8000
```

### 环境变量（可选）
```bash
docker run -p 8000:8000 \
  -e TURING_ADMIN_API_KEY=your-secret-key \
  -e CONFIG_TURING_AUTH_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  eliza-py
```

### 数据持久化
```bash
docker run -p 8000:8000 \
  -v ./data:/app/data \
  eliza-py
```

### 自定义端口（如 ClawCloudRun 需要 3001）
```bash
docker run -p 3001:3001 \
  -e PORT=3001 \
  -v ./data:/app/data \
  eliza-py
```

---

## 云服务器端口配置

### ClawCloudRun
| 配置项 | 值 |
|--------|-----|
| 容器端口 | `3001` |
| 环境变量 | `PORT=3001` |
| 公网访问 | 自动分配域名 |

### Render.com / Railway
自动检测 `PORT` 环境变量，无需额外配置。

### Hugging Face Spaces
固定使用 8000 端口，无需配置。

---

## 下载数据库
```bash
curl -H "X-API-Key: your-secret-key" \
     https://your-server.com/admin/export-data \
     -o turing.db
```

---

## 关键配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| 端口 | HTTP 服务端口 | `8000` |
| 数据目录 | 数据库持久化路径 | `/app/data` |
| 静态文件 | 前端构建输出 | `/app/turing_test/backend/static` |

---

## 环境变量列表

### 认证安全
- `TURING_ADMIN_API_KEY` - 数据导出 API 密钥（推荐设置）
- `CONFIG_TURING_AUTH_SECRET_KEY` - JWT 密钥（生产环境必填）

### 日志调试
- `DEBUG` - 调试模式 (`true`/`false`)，生产环境设为 `false`
- `LOG_LEVEL` - 日志级别 (`DEBUG`/`INFO`/`WARNING`/`ERROR`)

### 数据库
- `CONFIG_TURING_DATABASE_URL` - 数据库 URL
  - SQLite: `sqlite:///data/turing.db`
  - PostgreSQL: `postgresql+asyncpg://user:pass@host:5432/db`

---

## 云服务商特定配置

### ClawCloudRun
1. 镜像：填写你的镜像地址
2. 端口：`8000`
3. 存储卷：`/app/data`
4. 环境变量：在控制台添加

### Hugging Face Spaces
```yaml
# 在 spaces 中添加 Docker 配置
docker:
  ports:
    - 8000
  env:
    - TURING_ADMIN_API_KEY=your-key
```

### Render.com
1. Build Command: `docker build -t eliza-py .`
2. Start Command: `python main.py turing`
3. Disk: 添加持久化磁盘，挂载到 `/app/data`

---

## 故障排查

### 容器启动失败
```bash
docker logs <container-id>
```

### 数据库丢失
检查是否正确挂载数据卷：
```bash
docker inspect <container-id> | grep Mounts -A 10
```

### 前端页面 404
确认构建时前端已正确输出：
```bash
docker run --rm eliza-py ls -la /app/turing_test/backend/static
```

### WebSocket 连接失败
- 检查反向代理是否支持 WebSocket
- 确认防火墙允许 WebSocket 连接
