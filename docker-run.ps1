# Eliza-Py Docker 启动脚本 (PowerShell)
# 自动生成安全密钥并启动容器

$ErrorActionPreference = "Stop"

# 配置变量
$IMAGE_NAME = "eliza-py:latest"
$CONTAINER_NAME = "eliza-py"
$PORT = if ($env:DOCKER_PORT) { $env:DOCKER_PORT } else { "8000" }
$DATA_VOLUME = "eliza-data:/app/data"

Write-Host "🚀 Eliza-Py Docker 启动脚本" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

# 检查 Docker 是否运行
try {
    $dockerInfo = docker info 2>&1
} catch {
    Write-Host "❌ Docker 未运行或未安装" -ForegroundColor Red
    exit 1
}

# 检查镜像是否存在
$imageExists = docker image inspect "$IMAGE_NAME" 2>$null
if (-not $imageExists) {
    Write-Host "⚠️  镜像不存在，开始构建..." -ForegroundColor Yellow
    docker build -t "$IMAGE_NAME" .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 镜像构建失败" -ForegroundColor Red
        exit 1
    }
}

# 生成安全密钥
if (-not $env:CONFIG_TURING_AUTH_SECRET_KEY) {
    Write-Host "🔑 生成安全密钥..." -ForegroundColor Yellow
    $SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
} else {
    $SECRET_KEY = $env:CONFIG_TURING_AUTH_SECRET_KEY
}

# 停止并删除现有容器
$existingContainer = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $CONTAINER_NAME }
if ($existingContainer) {
    Write-Host "🗑️  停止现有容器..." -ForegroundColor Yellow
    docker stop "$CONTAINER_NAME" 2>$null | Out-Null
    docker rm "$CONTAINER_NAME" 2>$null | Out-Null
}

# 构建环境变量数组
$ENV_VARS = @(
    "-e", "CONFIG_TURING_AUTH_SECRET_KEY=$SECRET_KEY",
    "-e", "DEBUG=$(if ($env:DEBUG) { $env:DEBUG } else { 'false' })",
    "-e", "LOG_LEVEL=$(if ($env:LOG_LEVEL) { $env:LOG_LEVEL } else { 'INFO' })",
    "-e", "ENVIRONMENT=$(if ($env:ENVIRONMENT) { $env:ENVIRONMENT } else { 'production' })"
)

if ($env:CONFIG_TURING_CORS_ORIGINS) {
    $ENV_VARS += "-e", "CONFIG_TURING_CORS_ORIGINS=$($env:CONFIG_TURING_CORS_ORIGINS)"
}

if ($env:SENTRY_DSN) {
    $ENV_VARS += "-e", "SENTRY_DSN=$($env:SENTRY_DSN)"
    $ENV_VARS += "-e", "SENTRY_ENABLED=$(if ($env:SENTRY_ENABLED) { $env:SENTRY_ENABLED } else { 'true' })"
}

# 启动容器
Write-Host "🚀 启动容器..." -ForegroundColor Green
Write-Host "   端口：$PORT"
Write-Host "   数据卷：$DATA_VOLUME"
Write-Host ""

docker run -d `
    --name "$CONTAINER_NAME" `
    -p "$PORT`:8000" `
    -v "$DATA_VOLUME" `
    $ENV_VARS `
    "$IMAGE_NAME"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 容器启动成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 容器状态:" -ForegroundColor Cyan
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
    Write-Host ""
    Write-Host "🔗 访问地址:" -ForegroundColor Cyan
    Write-Host "   API:      http://localhost:$PORT"
    Write-Host "   文档：http://localhost:$PORT/docs"
    Write-Host "   健康检查：http://localhost:$PORT/health"
    Write-Host ""
    Write-Host "📝 常用命令:" -ForegroundColor Cyan
    Write-Host "   docker logs -f $CONTAINER_NAME          # 查看日志"
    Write-Host "   docker exec -it $CONTAINER_NAME bash    # 进入容器"
    Write-Host "   docker stop $CONTAINER_NAME             # 停止容器"
    Write-Host "   docker rm $CONTAINER_NAME               # 删除容器"
    Write-Host ""
    Write-Host "🔐 安全密钥 (请妥善保存):" -ForegroundColor Yellow
    Write-Host "   $SECRET_KEY"
    Write-Host ""
    Write-Host "💡 提示：可将密钥添加到 .env 文件避免每次重新生成" -ForegroundColor Gray
} else {
    Write-Host "❌ 容器启动失败" -ForegroundColor Red
    exit 1
}
