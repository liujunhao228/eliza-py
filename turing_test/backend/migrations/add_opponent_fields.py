#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加缺失的会话字段

迁移内容:
1. 在 sessions 表中添加 opponent_user_id 字段
2. 在 sessions 表中添加 opponent_session_id 字段

使用方法:
    uv run turing_test/backend/migrations/add_opponent_fields.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def migrate():
    """执行迁移"""
    # 从配置获取数据库 URL
    from config import settings
    
    database_url = settings.turing.database.url
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    # 创建数据库引擎
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # 检查字段是否已存在
        def get_columns(conn):
            from sqlalchemy import inspect
            inspector = inspect(conn)
            return [col['name'] for col in inspector.get_columns('sessions')]
        
        columns = await conn.run_sync(get_columns)
        
        # 添加 opponent_user_id 字段
        if 'opponent_user_id' not in columns:
            print("添加 opponent_user_id 字段...")
            await conn.execute(text(
                "ALTER TABLE sessions ADD COLUMN opponent_user_id INTEGER"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_sessions_opponent_user ON sessions(opponent_user_id)"
            ))
            print("✅ opponent_user_id 字段添加成功")
        else:
            print("⚠️  opponent_user_id 字段已存在，跳过")
        
        # 添加 opponent_session_id 字段
        if 'opponent_session_id' not in columns:
            print("添加 opponent_session_id 字段...")
            await conn.execute(text(
                "ALTER TABLE sessions ADD COLUMN opponent_session_id INTEGER"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_sessions_opponent_session ON sessions(opponent_session_id)"
            ))
            print("✅ opponent_session_id 字段添加成功")
        else:
            print("⚠️  opponent_session_id 字段已存在，跳过")
        
        print("\n迁移完成！")
    
    await engine.dispose()


async def main():
    """主函数"""
    await migrate()


if __name__ == "__main__":
    asyncio.run(main())
