#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加用户密码和昵称字段

功能：
1. 将 username 字段重命名为 nickname
2. 添加 password_hash 字段用于存储密码哈希
3. 设置 nickname 和 password_hash 为必填字段

使用说明：
    python migrations/add_user_password_and_nickname.py

注意：
- 执行前请备份现有数据
- 支持回滚操作
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import (
    create_engine,
    text,
    inspect,
)
from loguru import logger

from config import settings

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)


def table_exists(engine, table_name: str) -> bool:
    """检查表是否存在"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(engine)
    if not table_exists(engine, table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_migration():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("数据库迁移：添加用户密码和昵称字段")
    logger.info("=" * 60)

    engine = create_engine(settings.turing.database.url)

    try:
        with engine.begin() as conn:
            # 检查 users 表是否存在
            if not table_exists(engine, "users"):
                logger.error("❌ users 表不存在，无法执行迁移")
                return False

            # 步骤 1: 添加 password_hash 列（允许 NULL）
            if not column_exists(engine, "users", "password_hash"):
                logger.info("正在添加 password_hash 列...")
                conn.execute(text("""
                    ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)
                """))
                logger.info("  ✅ password_hash 列添加完成")
            else:
                logger.info("  password_hash 列已存在，跳过")

            # 步骤 2: 重命名 username 为 nickname
            if column_exists(engine, "users", "username"):
                logger.info("正在重命名 username 列为 nickname...")
                # SQLite 重命名列
                conn.execute(text("""
                    ALTER TABLE users RENAME COLUMN username TO nickname
                """))
                logger.info("  ✅ username 列已重命名为 nickname")
            else:
                logger.info("  username 列不存在，可能已重命名")

            # 步骤 3: 将现有用户的 nickname 设置为原 username 值（如果有 NULL）
            logger.info("正在更新现有用户的 nickname...")
            conn.execute(text("""
                UPDATE users SET nickname = '用户' || SUBSTR(invite_code, 1, 4) 
                WHERE nickname IS NULL OR nickname = ''
            """))
            logger.info("  ✅ nickname 更新完成")

            # 步骤 4: 设置 nickname 为 NOT NULL
            # SQLite 不支持直接修改列约束，需要重建表
            logger.info("正在设置 nickname 为必填字段...")
            
            # 获取所有列定义
            inspector = inspect(engine)
            columns = inspector.get_columns("users")
            
            # 构建新表结构（排除自增和默认值）
            column_defs = []
            for col in columns:
                col_name = col['name']
                col_type = str(col['type'])
                
                if col_name == "id":
                    column_defs.append(f"{col_name} INTEGER PRIMARY KEY AUTOINCREMENT")
                elif col_name == "nickname":
                    # 设置为 NOT NULL
                    column_defs.append(f"{col_name} VARCHAR(50) NOT NULL")
                elif col_name == "password_hash":
                    # 设置为 NOT NULL
                    column_defs.append(f"{col_name} VARCHAR(255) NOT NULL")
                else:
                    nullable = "NOT NULL" if not col.get('nullable', True) else ""
                    default = ""
                    if col.get('default') is not None:
                        default_val = col['default']
                        default = f" DEFAULT {default_val}"
                    column_defs.append(f"{col_name} {col_type} {nullable}{default}".strip())

            # 创建临时表
            logger.info("正在创建临时表...")
            conn.execute(text(f"""
                CREATE TABLE users_new (
                    {', '.join(column_defs)}
                )
            """))

            # 复制数据
            logger.info("正在复制数据到新表...")
            old_columns = [col['name'] for col in columns]
            conn.execute(text(f"""
                INSERT INTO users_new ({', '.join(old_columns)})
                SELECT {', '.join(old_columns)} FROM users
            """))

            # 删除旧表
            logger.info("正在删除旧表...")
            conn.execute(text("DROP TABLE users"))

            # 重命名新表
            logger.info("正在重命名新表...")
            conn.execute(text("ALTER TABLE users_new RENAME TO users"))

            # 重建索引
            logger.info("正在重建索引...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS ix_users_id ON users(id)",
                "CREATE INDEX IF NOT EXISTS ix_users_nickname ON users(nickname)",
                "CREATE INDEX IF NOT EXISTS ix_users_invite_code ON users(invite_code)",
                "CREATE INDEX IF NOT EXISTS ix_users_score ON users(score)",
            ]
            for idx_sql in indexes:
                conn.execute(text(idx_sql))

            logger.info("  ✅ 表结构更新完成")

        logger.info("=" * 60)
        logger.info("✅ 迁移完成！")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"❌ 迁移失败：{e}", exc_info=True)
        return False


def rollback_migration():
    """回滚迁移"""
    logger.info("=" * 60)
    logger.info("回滚数据库迁移")
    logger.info("=" * 60)

    engine = create_engine(settings.turing.database.url)

    try:
        with engine.begin() as conn:
            # 删除 password_hash 列，恢复 username 列
            if table_exists(engine, "users"):
                # 重建表结构（恢复 username，删除 password_hash）
                logger.info("正在恢复原始表结构...")
                
                conn.execute(text("""
                    CREATE TABLE users_old (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        invite_code VARCHAR(20) UNIQUE NOT NULL,
                        score INTEGER DEFAULT 100,
                        total_score_earned INTEGER DEFAULT 0,
                        total_score_lost INTEGER DEFAULT 0,
                        highest_score INTEGER DEFAULT 100,
                        lowest_score INTEGER DEFAULT 100,
                        risk_preference VARCHAR(20) DEFAULT 'moderate',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_login_at DATETIME
                    )
                """))

                # 复制数据（只复制原有字段）
                conn.execute(text("""
                    INSERT INTO users_old (
                        id, username, invite_code, score, total_score_earned,
                        total_score_lost, highest_score, lowest_score,
                        risk_preference, created_at, last_login_at
                    )
                    SELECT 
                        id, nickname, invite_code, score, total_score_earned,
                        total_score_lost, highest_score, lowest_score,
                        risk_preference, created_at, last_login_at
                    FROM users
                """))

                conn.execute(text("DROP TABLE users"))
                conn.execute(text("ALTER TABLE users_old RENAME TO users"))

                # 重建索引
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_id ON users(id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_invite_code ON users(invite_code)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_score ON users(score)"))

                logger.info("  ✅ 表结构已恢复")

        logger.info("✅ 回滚完成")
        return True

    except Exception as e:
        logger.error(f"❌ 回滚失败：{e}", exc_info=True)
        return False


def verify_migration():
    """验证迁移结果"""
    logger.info("=" * 60)
    logger.info("验证迁移结果")
    logger.info("=" * 60)

    engine = create_engine(settings.turing.database.url)
    inspector = inspect(engine)

    if not table_exists(engine, "users"):
        logger.error("❌ users 表不存在")
        return False

    columns = [col['name'] for col in inspector.get_columns("users")]
    
    logger.info("\nusers 表结构:")
    required_columns = ["id", "nickname", "password_hash", "invite_code", "score"]
    for col in required_columns:
        status = "✅" if col in columns else "❌"
        logger.info(f"  {status} {col}")

    # 检查是否还有旧的 username 列
    if "username" in columns:
        logger.warning("  ⚠️  username 列仍然存在，可能需要手动删除")

    logger.info("\n" + "=" * 60)
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具：用户密码和昵称字段")
    parser.add_argument(
        "action",
        choices=["migrate", "rollback", "verify"],
        help="迁移操作"
    )

    args = parser.parse_args()

    if args.action == "migrate":
        success = run_migration()
        verify_migration()
        sys.exit(0 if success else 1)
    elif args.action == "rollback":
        success = rollback_migration()
        sys.exit(0 if success else 1)
    elif args.action == "verify":
        verify_migration()
        sys.exit(0)
