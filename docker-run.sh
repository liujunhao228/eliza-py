#!/bin/bash
# Eliza-Py Docker 启动脚本
# 自动生成安全密钥并启动容器

set -e

# 配置变量
IMAGE_NAME="eliza-py:latest"
CONTAINER_NAME="eliza-py"
PORT="${DOCKER_PORT:-8000}"
DATA_VOLUME="eliza-data:/app/data"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Eliza-Py Docker 启动脚本"
echo "============================"

# 检查 Docker 是否运行
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker 未运行${NC}"
    exit 1
fi

# 检查镜像是否存在
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    echo -e "${YELLOW}⚠️  镜像不存在，开始构建...${NC}"
    docker build -t "$IMAGE_NAME" .
fi

# 生成安全密钥
if [ -z "$CONFIG_TURING_AUTH_SECRET_KEY" ]; then
    echo "🔑 生成安全密钥..."
    CONFIG_TURING_AUTH_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
fi

# 停止并删除现有容器
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "🗑️  停止现有容器..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# 构建 docker run 命令
DOCKER_RUN_CMD=(
    docker run -d
    --name "$CONTAINER_NAME"
    -p "$PORT:8000"
    -v "$DATA_VOLUME"
    -e "CONFIG_TURING_AUTH_SECRET_KEY=$CONFIG_TURING_AUTH_SECRET_KEY"
    -e "DEBUG=${DEBUG:-false}"
    -e "LOG_LEVEL=${LOG_LEVEL:-INFO}"
)

# 添加可选环境变量
if [ -n "$CONFIG_TURING_CORS_ORIGINS" ]; then
    DOCKER_RUN_CMD+=(-e "CONFIG_TURING_CORS_ORIGINS=$CONFIG_TURING_CORS_ORIGINS")
fi

if [ -n "$SENTRY_DSN" ]; then
    DOCKER_RUN_CMD+=(-e "SENTRY_DSN=$SENTRY_DSN")
    DOCKER_RUN_CMD+=(-e "SENTRY_ENABLED=${SENTRY_ENABLED:-true}")
fi

if [ -n "$ENVIRONMENT" ]; then
    DOCKER_RUN_CMD+=(-e "ENVIRONMENT=$ENVIRONMENT")
else
    DOCKER_RUN_CMD+=(-e "ENVIRONMENT=production")
fi

# 添加镜像名称
DOCKER_RUN_CMD+=("$IMAGE_NAME")

# 启动容器
echo "🚀 启动容器..."
echo "   端口：$PORT"
echo "   数据卷：$DATA_VOLUME"
echo ""

if "${DOCKER_RUN_CMD[@]}"; then
    echo -e "${GREEN}✅ 容器启动成功！${NC}"
    echo ""
    echo "📊 容器状态:"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "🔗 访问地址:"
    echo "   API:      http://localhost:$PORT"
    echo "   文档：http://localhost:$PORT/docs"
    echo "   健康检查：http://localhost:$PORT/health"
    echo ""
    echo "📝 常用命令:"
    echo "   docker logs -f $CONTAINER_NAME          # 查看日志"
    echo "   docker exec -it $CONTAINER_NAME bash    # 进入容器"
    echo "   docker stop $CONTAINER_NAME             # 停止容器"
    echo "   docker rm $CONTAINER_NAME               # 删除容器"
    echo ""
    echo "🔐 安全密钥已生成（请妥善保存）:"
    echo "   $CONFIG_TURING_AUTH_SECRET_KEY"
    echo ""
    echo "💡 提示：可将密钥添加到 .env 文件避免每次重新生成"
else
    echo -e "${RED}❌ 容器启动失败${NC}"
    exit 1
fi
