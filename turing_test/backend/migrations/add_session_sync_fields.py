"""
数据库迁移脚本：为 sessions 表添加会话同步相关字段

新增字段：
- first_left_at: 真人对战时，先离开一方的离开时间
- first_leaver_notified: 是否已通知先离开一方
- mid_game_turn: 场中判断时的轮次
- mid_game_meta_count: 场中判断时的元对话次数
- pending_opponent_bonus: 是否等待对方结算
- base_score_settled: 已结算的基础积分
- opponent_bonus_paid: 对方猜错奖励是否已发放

用法:
    uv run python turing_test/backend/migrations/add_session_sync_fields.py migrate
    uv run python turing_test/backend/migrations/add_session_sync_fields.py rollback
    uv run python turing_test/backend/migrations/add_session_sync_fields.py verify
"""

import asyncio
import sys
import aiosqlite
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import settings


async def migrate():
    """执行迁移"""
    db_path = settings.turing.database.url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]

        # first_left_at - 先离开一方的离开时间
        if "first_left_at" not in columns:
            print("添加 first_left_at 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN first_left_at DATETIME"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_first_left ON sessions(first_left_at)"
            )
            print("✅ first_left_at 添加成功")
        else:
            print("⚠️  first_left_at 已存在")

        # first_leaver_notified - 是否已通知先离开一方
        if "first_leaver_notified" not in columns:
            print("添加 first_leaver_notified 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN first_leaver_notified BOOLEAN DEFAULT 0"
            )
            print("✅ first_leaver_notified 添加成功")
        else:
            print("⚠️  first_leaver_notified 已存在")

        # mid_game_turn - 场中判断时的轮次
        if "mid_game_turn" not in columns:
            print("添加 mid_game_turn 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN mid_game_turn INTEGER"
            )
            print("✅ mid_game_turn 添加成功")
        else:
            print("⚠️  mid_game_turn 已存在")

        # mid_game_meta_count - 场中判断时的元对话次数
        if "mid_game_meta_count" not in columns:
            print("添加 mid_game_meta_count 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN mid_game_meta_count INTEGER"
            )
            print("✅ mid_game_meta_count 添加成功")
        else:
            print("⚠️  mid_game_meta_count 已存在")

        # pending_opponent_bonus - 是否等待对方结算
        if "pending_opponent_bonus" not in columns:
            print("添加 pending_opponent_bonus 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN pending_opponent_bonus BOOLEAN DEFAULT 0"
            )
            print("✅ pending_opponent_bonus 添加成功")
        else:
            print("⚠️  pending_opponent_bonus 已存在")

        # base_score_settled - 已结算的基础积分
        if "base_score_settled" not in columns:
            print("添加 base_score_settled 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN base_score_settled INTEGER"
            )
            print("✅ base_score_settled 添加成功")
        else:
            print("⚠️  base_score_settled 已存在")

        # opponent_bonus_paid - 对方猜错奖励是否已发放
        if "opponent_bonus_paid" not in columns:
            print("添加 opponent_bonus_paid 字段...")
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN opponent_bonus_paid BOOLEAN DEFAULT 0"
            )
            print("✅ opponent_bonus_paid 添加成功")
        else:
            print("⚠️  opponent_bonus_paid 已存在")

        await db.commit()
        print("\n✅ 迁移完成")


async def rollback():
    """回滚迁移（SQLite 不支持直接 DROP COLUMN，仅提供提示）"""
    print("⚠️  SQLite 不支持直接删除字段，如需回滚请手动操作数据库")
    print("\n参考 SQL:")
    print("""
    BEGIN TRANSACTION;
    CREATE TABLE sessions_new AS SELECT * FROM sessions;
    DROP TABLE sessions;
    CREATE TABLE sessions (
        -- 重新创建表结构，不包含新增字段
    );
    INSERT INTO sessions SELECT * FROM sessions_new;
    DROP TABLE sessions_new;
    COMMIT;
    """)


async def verify():
    """验证迁移状态"""
    db_path = settings.turing.database.url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]

        expected_columns = [
            "first_left_at",
            "first_leaver_notified",
            "mid_game_turn",
            "mid_game_meta_count",
            "pending_opponent_bonus",
            "base_score_settled",
            "opponent_bonus_paid",
        ]

        print("验证字段是否存在：")
        all_exist = True
        for col in expected_columns:
            exists = col in columns
            status = "✅" if exists else "❌"
            print(f"  {status} {col}")
            if not exists:
                all_exist = False

        if all_exist:
            print("\n✅ 验证通过：所有字段已存在")
        else:
            print("\n❌ 验证失败：部分字段缺失")


async def main():
    if len(sys.argv) < 2:
        print("用法：python add_session_sync_fields.py [migrate|rollback|verify]")
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
        print("用法：python add_session_sync_fields.py [migrate|rollback|verify]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
