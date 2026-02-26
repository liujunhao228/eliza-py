"""
数据库迁移脚本：为 sessions 表添加 user_guess 字段

用于存储场中判断时用户的猜测结果（'human' | 'ai'）

用法:
    uv run python turing_test/backend/migrations/add_session_user_guess.py migrate
    uv run python turing_test/backend/migrations/add_session_user_guess.py rollback
    uv run python turing_test/backend/migrations/add_session_user_guess.py verify
"""

import asyncio
import sys
import aiosqlite
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import settings


async def migrate():
    """执行迁移：添加 user_guess 字段"""
    db_path = settings.turing.database.url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as db:
        # 检查字段是否已存在
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]

        if "user_guess" in columns:
            print("✓ 字段 user_guess 已存在，无需迁移")
            return

        # 添加字段
        await db.execute("ALTER TABLE sessions ADD COLUMN user_guess VARCHAR(10)")
        await db.commit()

        print("✓ 迁移成功：已添加 user_guess 字段到 sessions 表")


async def rollback():
    """回滚迁移：删除 user_guess 字段"""
    db_path = settings.turing.database.url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as db:
        # SQLite 不支持直接 DROP COLUMN，需要重建表
        # 这里仅做提示，不实际执行回滚
        print("⚠️ SQLite 不支持直接删除字段，如需回滚请手动操作数据库")
        print("  或使用以下 SQL:")
        print("  BEGIN TRANSACTION;")
        print("  CREATE TABLE sessions_new AS SELECT * FROM sessions;")
        print("  DROP TABLE sessions;")
        print("  CREATE TABLE sessions (...不含 user_guess...);")
        print("  INSERT INTO sessions SELECT * FROM sessions_new;")
        print("  DROP TABLE sessions_new;")
        print("  COMMIT;")


async def verify():
    """验证迁移状态"""
    db_path = settings.turing.database.url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]

        if "user_guess" in columns:
            print("✓ 验证通过：user_guess 字段已存在")

            # 检查字段类型
            cursor = await db.execute(
                "SELECT name, type FROM PRAGMA_table_info('sessions') WHERE name='user_guess'"
            )
            col_info = await cursor.fetchone()
            if col_info:
                print(f"  字段信息：{col_info[0]} | 类型：{col_info[1]}")
        else:
            print("✗ 验证失败：user_guess 字段不存在")


async def main():
    if len(sys.argv) < 2:
        print("用法：python add_session_user_guess.py [migrate|rollback|verify]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "migrate":
        await migrate()
    elif command == "rollback":
        await rollback()
    elif command == "verify":
        await verify()
    else:
        print(f"未知命令：{command}")
        print("用法：python add_session_user_guess.py [migrate|rollback|verify]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
