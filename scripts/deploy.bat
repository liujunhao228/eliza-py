@echo off
REM =============================================================================
REM Eliza-Py Docker 一键部署脚本 (Windows)
REM =============================================================================
REM 使用方法:
REM   scripts\deploy.bat
REM
REM 或者双击运行:
REM   scripts\deploy.bat
REM =============================================================================

setlocal EnableDelayedExpansion

REM 颜色定义（Windows 10+ 支持 ANSI）
set "BLUE=[INFO]"
set "GREEN=[SUCCESS]"
set "YELLOW=[WARNING]"
set "RED=[ERROR]"

REM 获取脚本目录和项目根目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM 打印横幅
echo.
echo ========================================
echo    Eliza-Py Docker 一键部署脚本
echo ========================================
echo.

REM 检查 Docker 是否安装
:check_docker
echo %BLUE% 检查 Docker 安装...

docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED% Docker 未安装，请先安装 Docker Desktop
    echo   下载地址：https://www.docker.com/products/docker-desktop
    goto :error
)

docker compose version >nul 2>&1
if errorlevel 1 (
    echo %RED% Docker Compose 未安装
    echo   Docker Desktop 已包含 Docker Compose
    goto :error
)

echo %GREEN% Docker 和 Docker Compose 已安装
docker --version
docker compose version
echo.

REM 检查项目结构
:check_project
echo %BLUE% 检查项目结构...

if not exist "%PROJECT_ROOT%\docker-compose.yml" (
    echo %RED% 未找到 docker-compose.yml
    echo   请确保在项目根目录运行
    goto :error
)

if not exist "%PROJECT_ROOT%\Dockerfile" (
    echo %RED% 未找到 Dockerfile
    goto :error
)

echo %GREEN% 项目结构检查通过
echo.

REM 创建 .env 文件
:create_env
echo %BLUE% 检查环境配置文件...

if not exist "%PROJECT_ROOT%\.env.docker" (
    echo %YELLOW% 未找到 .env.docker 文件，将创建示例配置
    call :create_example_env
)

if not exist "%PROJECT_ROOT%\.env" (
    echo %BLUE% 复制 .env.docker 到 .env
    copy "%PROJECT_ROOT%\.env.docker" "%PROJECT_ROOT%\.env" >nul
    echo %GREEN% 已创建 .env 文件，请根据需要修改配置
) else (
    echo %BLUE% .env 文件已存在
)
echo.

REM 构建 Docker 镜像
:build_image
echo %BLUE% 构建 Docker 镜像...

cd /d "%PROJECT_ROOT%"

if "%1"=="--rebuild" (
    echo %BLUE% 强制重建镜像（无缓存）...
    docker compose build --no-cache
) else (
    docker compose build
)

if errorlevel 1 (
    echo %RED% Docker 镜像构建失败
    goto :error
)

echo %GREEN% Docker 镜像构建完成
echo.

REM 启动服务
:start_services
echo %BLUE% 启动服务...

docker compose up -d

if errorlevel 1 (
    echo %RED% 服务启动失败
    goto :error
)

echo %GREEN% 服务已启动
echo.

REM 等待服务启动
echo %BLUE% 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
:check_status
echo %BLUE% 检查服务状态...

docker compose ps

echo.
echo ========================================
echo    部署完成!
echo ========================================
echo.
echo %GREEN% Eliza-Py 已成功部署
echo.
echo 访问地址:
echo   http://localhost:8000
echo.
echo 管理端点:
echo   健康检查：http://localhost:8000/health
echo   导出数据：http://localhost:8000/admin/export-data
echo.
echo 常用命令:
echo   查看日志：docker compose logs -f
echo   停止服务：docker compose down
echo   重启服务：docker compose restart
echo   重建镜像：docker compose up -d --build
echo.
echo ========================================

goto :end

REM 创建示例 .env 文件
:create_example_env
echo %BLUE% 创建 .env.docker 示例文件...
(
echo # =============================================================================
echo # Eliza-Py Docker 环境配置
echo # =============================================================================
echo.
echo # 服务端口（宿主机：容器）
echo HOST_PORT=8000
echo.
echo # 运行模式：turing ^(默认^) 或 alice
echo RUN_MODE=turing
echo.
echo # 日志配置
echo LOG_LEVEL=INFO
echo DEBUG=false
echo ENVIRONMENT=production
echo.
echo # =============================================================================
echo # ^⚠️ 生产环境必须修改以下密钥
echo # =============================================================================
echo.
echo # JWT 认证密钥 - 生产环境必须修改！
echo # 生成方法：python -c "import secrets; print^(secrets.token_urlsafe^(32^)^)"
echo CONFIG_TURING_AUTH_SECRET_KEY=CHANGE_ME_IN_PRODUCTION
echo.
echo # 数据导出 API 密钥 - 推荐设置
echo TURING_ADMIN_API_KEY=
echo.
echo # =============================================================================
echo # 可选配置
echo # =============================================================================
echo.
echo # CORS 配置（生产环境必填）
echo # CONFIG_TURING_CORS_ORIGINS=https://your-domain.com
echo.
echo # 启动备份
echo ENABLE_STARTUP_BACKUP=true
echo.
echo # Sentry 错误追踪（可选）
echo # SENTRY_DSN=
echo # SENTRY_ENABLED=false
) > "%PROJECT_ROOT%\.env.docker"
echo %GREEN% 已创建 .env.docker 示例文件
goto :eof

REM 错误处理
:error
echo.
echo ========================================
echo    部署失败
echo ========================================
echo   请检查上述错误信息
echo ========================================
exit /b 1

REM 结束
:end
endlocal
exit /b 0
