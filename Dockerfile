# Eliza-Py Dockerfile
# 支持 Alice 聊天机器人和 Turing 测试后端
# 使用多阶段构建优化镜像大小
# 包含前端构建，单容器部署

# =============================================================================
# 阶段 1: 前端构建 - 构建 Vue 前端
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/turing_test/frontend

# 复制 package.json 和 package-lock.json（利用层缓存）
COPY turing_test/frontend/package*.json ./

# 安装依赖
RUN npm ci --silent

# 复制前端源代码
COPY turing_test/frontend/ ./

# 创建生产环境配置
RUN echo "VITE_API_BASE_URL=/api" > .env.production && \
    echo "VITE_WS_BASE_URL=ws://localhost/ws" >> .env.production

# 构建前端（输出到后端 static 目录）
RUN npm run build

# =============================================================================
# 阶段 2: Python 依赖构建
# =============================================================================
FROM python:3.12.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装构建依赖和 uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 仅复制依赖文件（利用层缓存：依赖文件变化频率低）
COPY pyproject.toml uv.lock ./

# 创建虚拟环境并同步依赖
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
RUN uv sync --frozen --no-dev

# =============================================================================
# 阶段 3: 运行阶段
# =============================================================================
FROM python:3.12.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装最小运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    bash \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# 从前端构建阶段复制已构建的静态文件
COPY --from=frontend-builder /app/turing_test/backend/static /app/turing_test/backend/static

# 复制应用代码（代码变化不会使依赖层缓存失效）
COPY . .

# 复制启动备份脚本并设置执行权限
COPY scripts/startup-backup.sh /usr/local/bin/startup-backup
RUN chmod +x /usr/local/bin/startup-backup

# 创建必要的目录并设置权限
RUN mkdir -p /app/data /app/data/backups /app/logs /app/scripts/lua && \
    chown -R appuser:appuser /app

# 创建非 root 用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口（支持 PORT 环境变量覆盖）
# 默认 8000，可通过环境变量 PORT 修改
EXPOSE 8000

# 健康检查 - 检查端口是否可连接（支持 PORT 环境变量）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import os, socket; port=int(os.getenv('PORT', 8000)); s=socket.socket(); s.settimeout(5); result=s.connect_ex(('127.0.0.1', port)); s.close(); exit(0 if result==0 else 1)" || exit 1

# =============================================================================
# 环境变量说明
# =============================================================================
# 可通过 docker run -e 或 docker-compose environment 设置：
#
# 数据导出保护（可选）:
#   TURING_ADMIN_API_KEY=your-secret-key-here
#   设置后，/admin/export-data 端点需要携带此 API Key 才能下载
#
# 启动备份（可选）:
#   ENABLE_STARTUP_BACKUP=true  (默认：true)
#   启动应用前自动备份现有数据库
#
# 示例:
#   docker run -e TURING_ADMIN_API_KEY=my-secret-key eliza-py
#   curl -H "X-API-Key: my-secret-key" https://your-server.com/admin/export-data -o turing.db
# =============================================================================

# 默认启动命令（使用启动备份脚本）
# 可通过 docker run 覆盖：
#   docker run eliza-py python main.py alice  # Alice 模式
#   docker run eliza-py python main.py turing # Turing 模式（默认）
#   docker run eliza-py bash                  # 仅启动 shell
CMD ["/usr/local/bin/startup-backup", "python", "main.py", "turing"]
