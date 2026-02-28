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
# 使用相对路径，由 nginx 反向代理处理
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
    && rm -rf /var/lib/apt/lists/*

# 使用 pip 安装 uv 到全局路径
RUN pip install --no-cache-dir uv

# 仅复制依赖文件（利用层缓存：依赖文件变化频率低）
COPY pyproject.toml uv.lock ./

# 创建虚拟环境并同步依赖
RUN uv venv /opt/venv && \
    uv sync --frozen --no-dev

# 复制 uv 到标准路径以便运行阶段使用
RUN cp /usr/local/bin/uv /opt/uv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# =============================================================================
# 阶段 3: 运行阶段
# =============================================================================
FROM python:3.12.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装 nginx 和最小运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    libgomp1 \
    bash \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境和 uv
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/uv /usr/local/bin/uv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# 从前端构建阶段复制已构建的静态文件到 nginx 目录
# 前端构建输出到 turing_test/backend/static，复制到 nginx 默认目录
COPY --from=frontend-builder /app/turing_test/backend/static /usr/share/nginx/html

# 复制 nginx 配置文件
COPY docker/nginx.conf /etc/nginx/nginx.conf

# 复制应用代码（代码变化不会使依赖层缓存失效）
COPY . .

# 复制入口脚本并设置执行权限
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

# 创建非 root 用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash appuser

# 创建必要的目录并设置权限
RUN mkdir -p /app/data /app/logs /app/scripts/lua && \
    chown -R appuser:appuser /app /opt/venv /usr/share/nginx/html && \
    mkdir -p /var/log/nginx /var/cache/nginx /run /tmp/nginx_client_body /tmp/nginx_proxy /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi && \
    chown -R appuser:appuser /var/log/nginx /var/cache/nginx /run /tmp/nginx_client_body /tmp/nginx_proxy /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi

USER appuser

# 暴露端口：3001 (前端), 8080 (后端 API)
EXPOSE 3001 8080

# 健康检查 - 检查 nginx 端口是否可连接
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); result=s.connect_ex(('127.0.0.1', 3001)); s.close(); exit(0 if result==0 else 1)" || exit 1

# =============================================================================
# 环境变量说明
# =============================================================================
# 可通过 docker run -e 或 docker-compose environment 设置：
#
# 数据导出保护（可选）:
#   TURING_ADMIN_API_KEY=your-secret-key-here
#   设置后，/admin/export-data 端点需要携带此 API Key 才能下载
#
# 数据库初始化配置（首次启动时自动初始化数据库）:
#   INVITE_CODE_COUNT=100        (默认：100)
#   首次启动时生成的邀请码数量
#
#   INVITE_CODE_EXPIRE_DAYS=30   (默认：永不过期)
#   邀请码过期天数，不设置则永不过期
#
# 示例:
#   # 默认启动（首次自动初始化数据库，生成 100 个邀请码）
#   docker run eliza-py
#
#   # 自定义邀请码数量
#   docker run -e INVITE_CODE_COUNT=500 eliza-py
#
#   # 设置邀请码过期时间
#   docker run -e INVITE_CODE_COUNT=200 -e INVITE_CODE_EXPIRE_DAYS=30 eliza-py
#
#   # 数据导出保护
#   docker run -e TURING_ADMIN_API_KEY=my-secret-key eliza-py
#   curl -H "X-API-Key: my-secret-key" https://your-server.com/admin/export-data -o turing.db
# =============================================================================

# 默认启动命令（使用入口脚本）
# 可通过 docker run 覆盖：
#   docker run eliza-py python main.py alice  # Alice 模式
#   docker run eliza-py python main.py turing # Turing 模式（默认）
#   docker run eliza-py bash                  # 仅启动 shell
#
# 注意：默认命令会同时启动 nginx 和后端服务
# 使用 JSON 数组形式正确传递参数
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["uv", "run", "python", "main.py", "turing"]
