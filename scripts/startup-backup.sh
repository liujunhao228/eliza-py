#!/bin/bash
# 启动前备份脚本
# 如果检测到已有数据库文件，先创建备份

set -e

DB_PATH="/app/data/turing.db"
BACKUP_DIR="/app/data/backups"
MAX_BACKUPS=3

echo "🔄 启动前检查数据库备份..."

# 检查数据库文件是否存在
if [ -f "$DB_PATH" ]; then
    echo "📁 检测到现有数据库，创建备份..."
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 生成带时间戳的备份文件名
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/turing_backup_$TIMESTAMP.db"
    
    # 复制数据库文件
    cp "$DB_PATH" "$BACKUP_FILE"
    echo "✅ 备份已创建：$BACKUP_FILE"
    
    # 清理旧备份（只保留最近的 N 个）
    cd "$BACKUP_DIR"
    BACKUP_COUNT=$(ls -1 turing_backup_*.db 2>/dev/null | wc -l)
    
    if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
        # 删除最旧的备份
        DELETE_COUNT=$((BACKUP_COUNT - MAX_BACKUPS))
        ls -1t turing_backup_*.db | tail -n "$DELETE_COUNT" | xargs rm -f
        echo "🧹 已清理 $DELETE_COUNT 个旧备份"
    fi
else
    echo "ℹ️  数据库文件不存在，跳过备份"
fi

echo "✅ 备份检查完成，启动应用..."

# 执行原始启动命令
exec "$@"
