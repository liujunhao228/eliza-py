#!/bin/bash
# =============================================================================
# Eliza-Py Docker 一键部署脚本 (Linux/Mac)
# =============================================================================
# 使用方法:
#   bash scripts/deploy.sh
#
# 或者先添加执行权限:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印横幅
print_banner() {
    echo ""
    echo "========================================"
    echo "   Eliza-Py Docker 一键部署脚本"
    echo "========================================"
    echo ""
}

# 检查 Docker 是否安装
check_docker() {
    log_info "检查 Docker 安装..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com | sh"
        echo "  CentOS: yum install -y docker-ce"
        echo "  Mac: 下载 Docker Desktop https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        echo "  Ubuntu/Debian: apt-get install docker-compose-plugin"
        echo "  CentOS: yum install docker-compose-plugin"
        echo "  Mac: Docker Desktop 已包含"
        exit 1
    fi
    
    log_success "Docker 和 Docker Compose 已安装"
    docker --version
    docker compose version
}

# 检查是否在正确的目录
check_project_root() {
    log_info "检查项目结构..."
    
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        log_error "未找到 docker-compose.yml，请确保在项目根目录运行"
        exit 1
    fi
    
    if [ ! -f "$PROJECT_ROOT/Dockerfile" ]; then
        log_error "未找到 Dockerfile"
        exit 1
    fi
    
    log_success "项目结构检查通过"
}

# 创建 .env 文件
create_env_file() {
    local env_file="$PROJECT_ROOT/.env.docker"
    local local_env_file="$PROJECT_ROOT/.env"
    
    log_info "检查环境配置文件..."
    
    if [ ! -f "$env_file" ]; then
        log_warning "未找到 .env.docker 文件，将创建示例配置"
        create_example_env
    fi
    
    if [ ! -f "$local_env_file" ]; then
        log_info "复制 .env.docker 到 .env"
        cp "$env_file" "$local_env_file"
        log_success "已创建 .env 文件，请根据需要修改配置"
    else
        log_info ".env 文件已存在"
    fi
}

# 创建示例 .env 文件
create_example_env() {
    cat > "$env_file" << 'EOF'
# =============================================================================
# Eliza-Py Docker 环境配置
# =============================================================================

# 服务端口（宿主机:容器）
HOST_PORT=8000

# 运行模式：turing (默认) 或 alice
RUN_MODE=turing

# 日志配置
LOG_LEVEL=INFO
DEBUG=false
ENVIRONMENT=production

# =============================================================================
# ⚠️ 生产环境必须修改以下密钥
# =============================================================================

# JWT 认证密钥 - 生产环境必须修改！
# 生成方法：python -c "import secrets; print(secrets.token_urlsafe(32))"
CONFIG_TURING_AUTH_SECRET_KEY=CHANGE_ME_IN_PRODUCTION

# 数据导出 API 密钥 - 推荐设置
TURING_ADMIN_API_KEY=

# =============================================================================
# 可选配置
# =============================================================================

# CORS 配置（生产环境必填）
# CONFIG_TURING_CORS_ORIGINS=https://your-domain.com

# 启动备份
ENABLE_STARTUP_BACKUP=true

# Sentry 错误追踪（可选）
# SENTRY_DSN=
# SENTRY_ENABLED=false
EOF
    log_success "已创建 .env.docker 示例文件"
}

# 生成安全密钥
generate_secret_key() {
    log_info "生成安全密钥..."
    
    if command -v python3 &> /dev/null; then
        python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    elif command -v python &> /dev/null; then
        python -c "import secrets; print(secrets.token_urlsafe(32))"
    elif command -v openssl &> /dev/null; then
        openssl rand -base64 32
    else
        log_warning "无法生成密钥，请手动设置 CONFIG_TURING_AUTH_SECRET_KEY"
        echo "  可用方法:"
        echo "    python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        echo "    openssl rand -base64 32"
    fi
}

# 构建 Docker 镜像
build_image() {
    log_info "构建 Docker 镜像..."
    
    cd "$PROJECT_ROOT"
    
    if [ "$1" == "--rebuild" ]; then
        log_info "强制重建镜像（无缓存）..."
        docker compose build --no-cache
    else
        docker compose build
    fi
    
    log_success "Docker 镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd "$PROJECT_ROOT"
    
    docker compose up -d
    
    log_success "服务已启动"
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    
    cd "$PROJECT_ROOT"
    
    docker compose ps
}

# 显示访问信息
show_access_info() {
    echo ""
    echo "========================================"
    echo "   部署完成!"
    echo "========================================"
    echo ""
    log_success "Eliza-Py 已成功部署"
    echo ""
    echo "访问地址:"
    echo "  http://localhost:8000"
    echo ""
    echo "管理端点:"
    echo "  健康检查：http://localhost:8000/health"
    echo "  导出数据：http://localhost:8000/admin/export-data"
    echo ""
    echo "常用命令:"
    echo "  查看日志：docker compose logs -f"
    echo "  停止服务：docker compose down"
    echo "  重启服务：docker compose restart"
    echo "  重建镜像：docker compose up -d --build"
    echo ""
    echo "========================================"
}

# 主函数
main() {
    print_banner
    
    # 解析参数
    case "${1:-}" in
        --rebuild)
            REBUILD=true
            ;;
        --status)
            check_docker
            check_project_root
            check_status
            exit 0
            ;;
        --stop)
            check_docker
            cd "$PROJECT_ROOT"
            docker compose down
            log_success "服务已停止"
            exit 0
            ;;
        --restart)
            check_docker
            cd "$PROJECT_ROOT"
            docker compose restart
            log_success "服务已重启"
            exit 0
            ;;
        --help|-h)
            echo "用法：bash scripts/deploy.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --rebuild    强制重建镜像（不使用缓存）"
            echo "  --status     查看服务状态"
            echo "  --stop       停止服务"
            echo "  --restart    重启服务"
            echo "  --help, -h   显示帮助"
            echo ""
            exit 0
            ;;
    esac
    
    # 执行部署
    check_docker
    check_project_root
    create_env_file
    
    echo ""
    log_info "准备构建并启动服务..."
    echo ""
    
    build_image "${REBUILD:+--rebuild}"
    start_services
    
    # 等待服务启动
    echo ""
    log_info "等待服务启动..."
    sleep 5
    
    check_status
    show_access_info
}

# 运行主函数
main "$@"
