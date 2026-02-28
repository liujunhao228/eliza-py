# Eliza-Py Docker 快速开始

## 一键部署

### Linux / Mac

```bash
# 方式 1: 直接运行
bash scripts/deploy.sh

# 方式 2: 添加执行权限后运行
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Windows

```cmd
scripts\deploy.bat
```

或者双击 `scripts\deploy.bat` 运行。

---

## 手动部署

### 1. 配置环境变量

```bash
# 复制示例配置
cp .env.docker .env

# 编辑 .env 文件，修改密钥等配置
```

### 2. 启动服务

```bash
# 构建并启动
docker compose up -d

# 或者强制重建镜像
docker compose up -d --build
```

### 3. 访问服务

- **主页**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **导出数据**: http://localhost:8000/admin/export-data

---

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 停止并删除数据卷（⚠️ 会删除数据库）
docker compose down -v

# 重建镜像
docker compose build

# 进入容器
docker compose exec eliza-py bash
```

---

## 部署脚本选项

### Linux/Mac 脚本

```bash
# 显示帮助
bash scripts/deploy.sh --help

# 查看服务状态
bash scripts/deploy.sh --status

# 停止服务
bash scripts/deploy.sh --stop

# 重启服务
bash scripts/deploy.sh --restart

# 强制重建镜像（不使用缓存）
bash scripts/deploy.sh --rebuild
```

### Windows 脚本

Windows 脚本自动执行完整部署流程，包括：
- 检查 Docker 安装
- 创建环境配置文件
- 构建镜像
- 启动服务

---

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HOST_PORT` | 宿主机端口 | `8000` |
| `RUN_MODE` | 运行模式 (turing/alice) | `turing` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DEBUG` | 调试模式 | `false` |
| `CONFIG_TURING_AUTH_SECRET_KEY` | JWT 密钥 ⚠️ | `CHANGE_ME_IN_PRODUCTION` |
| `TURING_ADMIN_API_KEY` | 数据导出密钥 | (空) |

### ⚠️ 生产环境安全提示

1. **必须修改 JWT 密钥**:
   ```bash
   # 生成安全密钥
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **设置数据导出密钥**:
   ```bash
   TURING_ADMIN_API_KEY=your-secret-key-here
   ```

3. **配置 CORS**:
   ```bash
   CONFIG_TURING_CORS_ORIGINS=https://your-domain.com
   ```

---

## 数据持久化

数据库文件存储在 Docker 卷中：

- **卷名称**: `eliza-py-data`
- **容器路径**: `/app/data/turing.db`
- **备份目录**: `/app/data/backups/`

### 备份数据库

```bash
# 下载数据库（如果设置了 TURING_ADMIN_API_KEY）
curl -H "X-API-Key: your-key" \
     http://localhost:8000/admin/export-data \
     -o turing.db
```

---

## 故障排查

### 端口被占用

```bash
# 修改 .env 中的 HOST_PORT
HOST_PORT=9000

# 重启服务
docker compose restart
```

### 查看日志

```bash
# 查看完整日志
docker compose logs

# 实时查看日志
docker compose logs -f

# 查看特定容器日志
docker compose logs eliza-py
```

### 进入容器调试

```bash
docker compose exec eliza-py bash

# 在容器内
python main.py check-config  # 检查配置
ls -la /app/data/            # 查看数据文件
```

### 重置服务

```bash
# ⚠️ 警告：这会删除所有数据
docker compose down -v
docker compose up -d
```

---

## 升级

```bash
# 拉取最新代码
git pull

# 重建镜像并重启
docker compose up -d --build
```

---

## 卸载

```bash
# 停止并删除服务（保留数据卷）
docker compose down

# 删除数据卷（⚠️ 会删除所有数据）
docker volume rm eliza-py-data

# 删除镜像
docker rmi eliza-py-eliza-py
```

---

## 更多信息

- [详细部署文档](DEPLOYMENT.md)
- [单服务器部署](DEPLOY_SINGLE_SERVER.md)
- [ClawCloudRun 部署](DEPLOY_CLAWCLOUDRUN.md)
