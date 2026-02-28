#!/bin/bash
# Docker 入口脚本
# 启动 nginx 和后端服务

set -e

echo "🚀 启动服务..."

# 设置项目根目录环境变量，确保数据库路径解析正确
export PROJECT_ROOT=/app

# 调试信息：打印所有 CONFIG_ 开头的环境变量
echo "🔍 [DEBUG] 环境变量检查:"
env | grep -E "^CONFIG_|^DEBUG|^LOG_LEVEL|^ENVIRONMENT|^INVITE_CODE_|^SENTRY_|^TURING_" || echo "🔍 [DEBUG] 未找到相关环境变量"

# 修正数据目录权限（处理挂载卷的情况，需要 root 权限）
if [ "$(id -u)" = "0" ]; then
    DATA_DIR="/app/data"
    LOGS_DIR="/app/logs"
    
    # 创建目录（如果不存在）
    mkdir -p "$DATA_DIR" "$LOGS_DIR"
    
    # 修正权限：确保 appuser 可以写入
    # 使用 755 权限，所有者可读写执行
    chmod 755 "$DATA_DIR" "$LOGS_DIR"
    chown -R appuser:appgroup "$DATA_DIR" "$LOGS_DIR"
    
    # 如果数据库文件已存在，确保其权限正确
    if [ -f "$DATA_DIR/turing.db" ]; then
        chown appuser:appgroup "$DATA_DIR/turing.db"
        chmod 644 "$DATA_DIR/turing.db"
        echo "✅ 已修正数据库文件权限"
    fi
    
    echo "✅ 已修正 $DATA_DIR 和 $LOGS_DIR 权限"
fi

# 启动 nginx（后台运行）
nginx
echo "✅ nginx 已启动"

# 数据库路径
DB_PATH="/app/data/turing.db"
DATA_DIR="/app/data"

# 调试信息
echo "🔍 [DEBUG] 检查数据库文件..."
echo "🔍 [DEBUG] DB_PATH: $DB_PATH"
echo "🔍 [DEBUG] DATA_DIR: $DATA_DIR"
echo "🔍 [DEBUG] PROJECT_ROOT: $PROJECT_ROOT"
echo "🔍 [DEBUG] 当前工作目录：$(pwd)"
echo "🔍 [DEBUG] /app/data 目录内容:"
ls -la /app/data 2>/dev/null || echo "🔍 [DEBUG] /app/data 目录不存在或为空"

# 检查数据库是否存在，不存在则初始化
if [ ! -f "$DB_PATH" ]; then
    echo "📁 数据库不存在，开始初始化..."

    # 初始化数据库并生成邀请码
    # 默认生成 100 个邀请码，可通过环境变量配置
    # INVITE_CODE_COUNT: 邀请码数量（默认：100）
    # INVITE_CODE_EXPIRE_DAYS: 邀请码过期天数（默认：永不过期）
    INVITE_COUNT="${INVITE_CODE_COUNT:-100}"
    INVITE_EXPIRE="${INVITE_CODE_EXPIRE_DAYS:-}"

    echo "📋 计划生成 $INVITE_COUNT 个邀请码"

    if [ -n "$INVITE_EXPIRE" ]; then
        echo "⏰ 邀请码过期天数：$INVITE_EXPIRE 天"
        python -m turing_test.backend.scripts.init_db \
            --count "$INVITE_COUNT" \
            --expire-days "$INVITE_EXPIRE" \
            --skip-check \
            --output "$DATA_DIR/invite_codes.txt"
    else
        python -m turing_test.backend.scripts.init_db \
            --count "$INVITE_COUNT" \
            --skip-check \
            --output "$DATA_DIR/invite_codes.txt"
    fi

    # 重要：初始化后修正数据库文件权限（因为是以 root 身份创建的）
    if [ -f "$DB_PATH" ]; then
        chown appuser:appgroup "$DB_PATH"
        chmod 644 "$DB_PATH"
        echo "✅ 已修正新创建数据库文件权限"
    fi

    echo "✅ 数据库初始化完成"
    echo "📄 邀请码已导出到：$DATA_DIR/invite_codes.txt"
else
    echo "📁 检测到现有数据库：$DB_PATH"
fi

echo "🔄 启动后端服务..."

# 最后一次检查并修正所有必要文件的权限（确保 appuser 可以访问）
if [ "$(id -u)" = "0" ]; then
    # 修正数据目录和日志目录权限
    chown -R appuser:appgroup /app/data /app/logs 2>/dev/null || true
    chmod 755 /app/data /app/logs 2>/dev/null || true
    
    # 修正数据库文件权限（如果存在）
    if [ -f "$DB_PATH" ]; then
        chown appuser:appgroup "$DB_PATH"
        chmod 644 "$DB_PATH"
    fi
    
    # 修正日志文件权限（如果存在）
    find /app/logs -type f -name "*.log" -exec chown appuser:appgroup {} \; 2>/dev/null || true
fi

# 以 appuser 用户执行后端命令（安全最佳实践）
if [ "$(id -u)" = "0" ]; then
    # 当前是 root，切换到 appuser 执行
    # 注意：不要使用 'su -'，否则会清除环境变量（如 PATH 和 AUTH_SECRET_KEY）
    # su -c 会自动继承大部分环境变量，使用 exec 替换当前进程
    exec su appuser -c "cd /app && exec $*"
else
    # 当前已是非 root 用户，直接执行
    exec "$@"
fi
