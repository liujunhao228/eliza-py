#!/bin/bash
# Docker 入口脚本
# 启动 nginx 和后端服务

set -e

echo "🚀 启动服务..."

# 启动 nginx（后台运行）
nginx
echo "✅ nginx 已启动"

# 数据库路径
DB_PATH="/app/data/turing.db"
DATA_DIR="/app/data"

# 确保数据目录存在
mkdir -p "$DATA_DIR"

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
        uv run python -m turing_test.backend.scripts.init_db \
            --count "$INVITE_COUNT" \
            --expire-days "$INVITE_EXPIRE" \
            --skip-check \
            --output "$DATA_DIR/invite_codes.txt"
    else
        uv run python -m turing_test.backend.scripts.init_db \
            --count "$INVITE_COUNT" \
            --skip-check \
            --output "$DATA_DIR/invite_codes.txt"
    fi
    
    echo "✅ 数据库初始化完成"
    echo "📄 邀请码已导出到：$DATA_DIR/invite_codes.txt"
else
    echo "📁 检测到现有数据库：$DB_PATH"
fi

echo "🔄 启动后端服务..."

# 执行传入的命令（默认 uv run python main.py turing）
exec "$@"
