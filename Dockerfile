# ========================================
# Stage: Builder
# 构建依赖和编译环境
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip 和构建工具
RUN pip install --upgrade pip setuptools wheel uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装所有依赖（包含 NLP 可选依赖）
RUN uv pip install --system -e ".[nlp]" --no-cache

# ========================================
# Stage: Runtime
# 最小化运行时镜像
# ========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 创建非 root 用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 从 builder 阶段复制已安装的包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 设置权限
RUN chown -R appuser:appgroup /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 5000 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1

# 默认启动命令（Web 模式）
CMD ["python", "main.py", "--web", "--host", "0.0.0.0", "--port", "8000"]

# ========================================
# Stage: Development
# 开发环境（支持热重载）
# ========================================
FROM runtime AS dev

USER root

# 安装开发工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 安装开发依赖
RUN uv pip install --system -e ".[dev,test]" --no-cache

USER appuser

# 开发模式启动（热重载）
CMD ["python", "main.py", "--web", "--host", "0.0.0.0", "--port", "8000", "--debug"]
