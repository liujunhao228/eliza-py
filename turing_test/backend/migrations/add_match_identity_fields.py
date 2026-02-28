#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加匹配真实身份字段

迁移内容:
1. 在 sessions 表中添加 true_identity 字段
2. 在 sessions 表中添加 bot_level 字段

使用方法:
    uv run turing_test/backend/migrations/add_match_identity_fields.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text, inspect
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
        # 检查字段是否已存在 (在 run_sync 内部使用 inspect)
        def get_columns(conn):
            inspector = inspect(conn)
            return [col['name'] for col in inspector.get_columns('sessions')]
        
        columns = await conn.run_sync(get_columns)
        
        # 添加 true_identity 字段
        if 'true_identity' not in columns:
            print("添加 true_identity 字段...")
            await conn.execute(text(
                "ALTER TABLE sessions ADD COLUMN true_identity VARCHAR(50)"
            ))
            print("✅ true_identity 字段添加成功")
        else:
            print("⚠️  true_identity 字段已存在，跳过")
        
        # 添加 bot_level 字段
        if 'bot_level' not in columns:
            print("添加 bot_level 字段...")
            await conn.execute(text(
                "ALTER TABLE sessions ADD COLUMN bot_level VARCHAR(20)"
            ))
            print("✅ bot_level 字段添加成功")
        else:
            print("⚠️  bot_level 字段已存在，跳过")
        
        print("\n迁移完成！")
        print("\n新字段说明:")
        print("  - true_identity: 真实身份 ('Human', 'Bot_Lv1', 'Bot_Lv2', 'Bot_Lv3', 'Honeypot_Aggressive', 'Honeypot_Sus')")
        print("  - bot_level: Bot 等级 ('lv1_newbie', 'lv2_typical', 'lv3_logic')")
        print("\n⚠️  注意：这些字段仅后台记录，绝不返回前端！")
    
    await engine.dispose()


async def rollback():
    """回滚迁移"""
    from config import settings
    
    database_url = settings.turing.database.url
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    engine = create_async_engine(database_url)
    
    async with engine.begin() as conn:
        print("回滚迁移...")
        
        # SQLite 不支持直接删除列，需要重建表
        # 这里仅做提示
        print("⚠️  SQLite 不支持直接删除列，如需回滚请手动处理:")
        print("   1. 备份数据")
        print("   2. 创建新表 (不含 true_identity, bot_level)")
        print("   3. 复制数据")
        print("   4. 删除旧表")
        print("   5. 重命名新表")
    
    await engine.dispose()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移：添加匹配真实身份字段")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚迁移"
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        await rollback()
    else:
        await migrate()


if __name__ == "__main__":
    asyncio.run(main())
