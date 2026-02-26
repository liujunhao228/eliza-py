# Eliza-Py Dockerfile
# 支持 Alice 聊天机器人和 Turing 测试后端
# 使用多阶段构建优化镜像大小

# =============================================================================
# 阶段 1: 构建阶段 - 安装依赖
# =============================================================================
FROM python:3.12.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 工具
RUN pip install --no-cache-dir uv

# 仅复制依赖文件（利用层缓存：依赖文件变化频率低）
COPY pyproject.toml uv.lock* ./

# 安装依赖到指定目录
RUN uv pip install --prefix=/install .

# =============================================================================
# 阶段 2: 运行阶段
# =============================================================================
FROM python:3.12.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages"

WORKDIR /app

# 安装最小运行时依赖（仅需 libgomp1 用于某些科学计算包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制已安装的依赖
COPY --from=builder /install /install

# 复制应用代码（代码变化不会使依赖层缓存失效）
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p /app/data /app/logs /app/scripts/lua

# 创建非 root 用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查 - 检查端口是否可连接
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); result=s.connect_ex(('127.0.0.1', 8000)); s.close(); exit(0 if result==0 else 1)" || exit 1

# 默认启动命令
# 可通过 docker run 覆盖：
#   docker run eliza-py python main.py alice  # Alice 模式
#   docker run eliza-py python main.py turing # Turing 模式（默认）
CMD ["python", "main.py", "turing"]
