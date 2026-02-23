#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加积分系统

功能：
1. 扩展 Users 表：添加积分相关字段
2. 扩展 Sessions 表：添加博弈相关字段
3. 扩展 Messages 表：添加元对话标记
4. 创建 ScoreHistory 表：积分历史记录
5. 创建 UserStats 表：用户统计数据

使用方法：
    python migrations/add_score_system.py

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
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Session, DeclarativeBase

from config import settings
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)


class Base(DeclarativeBase):
    pass


# =============================================================================
# 备份表（用于回滚）
# =============================================================================

BACKUP_TABLES = [
    "users_backup",
    "sessions_backup",
    "messages_backup",
]


def create_backup_url(db_url: str) -> str:
    """创建备份数据库 URL"""
    if "sqlite" in db_url:
        return db_url.replace(".db", "_backup.db")
    return db_url + "_backup"


def backup_database(source_url: str, target_url: str):
    """备份整个数据库"""
    logger.info(f"正在备份数据库：{source_url} -> {target_url}")

    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)

    with source_engine.connect() as source_conn:
        # 获取所有表名
        inspector = inspect(source_engine)
        tables = inspector.get_table_names()

        # 创建目标表并复制数据
        with target_engine.begin() as target_conn:
            for table_name in tables:
                # 获取表结构
                columns = inspector.get_columns(table_name)
                col_defs = []
                for col in columns:
                    col_type = str(col['type'])
                    col_defs.append(f'"{col["name"]}" {col_type}')

                # 创建表
                create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'
                target_conn.execute(text(create_sql))

                # 复制数据
                target_conn.execute(text(f'INSERT INTO "{table_name}" SELECT * FROM "{table_name}"'))

    logger.info("✅ 数据库备份完成")


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


def migrate_users(engine):
    """迁移 Users 表"""
    logger.info("正在迁移 Users 表...")

    with engine.begin() as conn:
        # 添加积分字段
        columns_to_add = [
            ("score", "INTEGER DEFAULT 100"),
            ("total_score_earned", "INTEGER DEFAULT 0"),
            ("total_score_lost", "INTEGER DEFAULT 0"),
            ("highest_score", "INTEGER DEFAULT 100"),
            ("lowest_score", "INTEGER DEFAULT 100"),
            ("risk_preference", "VARCHAR(20) DEFAULT 'moderate'"),
            ("last_login_at", "DATETIME"),
        ]

        for col_name, col_def in columns_to_add:
            if not column_exists(engine, "users", col_name):
                logger.info(f"  添加列：{col_name}")
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
            else:
                logger.info(f"  列已存在：{col_name}")

    logger.info("✅ Users 表迁移完成")


def migrate_sessions(engine):
    """迁移 Sessions 表"""
    logger.info("正在迁移 Sessions 表...")

    with engine.begin() as conn:
        # 添加博弈字段
        columns_to_add = [
            ("is_honeypot", "BOOLEAN DEFAULT FALSE"),
            ("triggered_mid_game", "BOOLEAN DEFAULT FALSE"),
            ("meta_conversation_count", "INTEGER DEFAULT 0"),
            ("confidence_level", "VARCHAR(20)"),
            ("is_correct", "BOOLEAN"),
            ("final_score", "INTEGER"),
            ("score_breakdown", "JSON"),
        ]

        for col_name, col_def in columns_to_add:
            if not column_exists(engine, "sessions", col_name):
                logger.info(f"  添加列：{col_name}")
                conn.execute(text(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_def}"))
            else:
                logger.info(f"  列已存在：{col_name}")

    logger.info("✅ Sessions 表迁移完成")


def migrate_messages(engine):
    """迁移 Messages 表"""
    logger.info("正在迁移 Messages 表...")

    with engine.begin() as conn:
        # 添加元对话标记
        if not column_exists(engine, "messages", "is_meta_conversation"):
            logger.info("  添加列：is_meta_conversation")
            conn.execute(text(
                "ALTER TABLE messages ADD COLUMN is_meta_conversation BOOLEAN DEFAULT FALSE"
            ))
        else:
            logger.info("  列已存在：is_meta_conversation")

        if not column_exists(engine, "messages", "meta_keyword"):
            logger.info("  添加列：meta_keyword")
            conn.execute(text(
                "ALTER TABLE messages ADD COLUMN meta_keyword VARCHAR(50)"
            ))
        else:
            logger.info("  列已存在：meta_keyword")

    logger.info("✅ Messages 表迁移完成")


def create_score_history(engine):
    """创建 ScoreHistory 表"""
    logger.info("正在创建 ScoreHistory 表...")

    if table_exists(engine, "score_history"):
        logger.info("  表已存在，跳过")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id INTEGER,
                score_change INTEGER NOT NULL,
                score_before INTEGER NOT NULL,
                score_after INTEGER NOT NULL,
                reason VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """))

        # 创建索引
        conn.execute(text("CREATE INDEX idx_score_history_user ON score_history(user_id)"))
        conn.execute(text("CREATE INDEX idx_score_history_session ON score_history(session_id)"))
        conn.execute(text("CREATE INDEX idx_score_history_created ON score_history(created_at)"))

    logger.info("✅ ScoreHistory 表创建完成")


def create_user_stats(engine):
    """创建 UserStats 表"""
    logger.info("正在创建 UserStats 表...")

    if table_exists(engine, "user_stats"):
        logger.info("  表已存在，跳过")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE user_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                total_sessions INTEGER DEFAULT 0,
                ai_sessions INTEGER DEFAULT 0,
                human_sessions INTEGER DEFAULT 0,
                honeypot_sessions INTEGER DEFAULT 0,
                total_guesses INTEGER DEFAULT 0,
                correct_guesses INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0,
                low_confidence_count INTEGER DEFAULT 0,
                mid_confidence_count INTEGER DEFAULT 0,
                high_confidence_count INTEGER DEFAULT 0,
                total_meta_conversations INTEGER DEFAULT 0,
                avg_meta_per_session REAL DEFAULT 0,
                max_meta_in_one_session INTEGER DEFAULT 0,
                accuracy_with_meta REAL,
                accuracy_without_meta REAL,
                mid_game_judgments INTEGER DEFAULT 0,
                mid_game_accuracy REAL DEFAULT 0,
                avg_turns REAL DEFAULT 0,
                min_turns INTEGER,
                max_turns INTEGER,
                total_chat_time INTEGER DEFAULT 0,
                avg_session_duration REAL DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))

        # 创建索引
        conn.execute(text("CREATE INDEX idx_user_stats_user ON user_stats(user_id)"))

    logger.info("✅ UserStats 表创建完成")


def create_base_tables(engine):
    """如果数据库为空，先创建基础表"""
    logger.info("检查是否需要创建基础表...")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not tables or "users" not in tables:
        logger.info("数据库为空，正在创建基础表...")
        from models import User, Session, Message, ScoreHistory, UserStats, Base
        Base.metadata.create_all(engine)
        logger.info("✅ 基础表创建完成")
        return True
    return False


def run_migration():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("数据库迁移：添加积分系统")
    logger.info("=" * 60)

    # 创建备份
    backup_url = create_backup_url(settings.DATABASE_URL)
    logger.info(f"备份数据库：{backup_url}")

    try:
        backup_database(settings.DATABASE_URL, backup_url)
    except Exception as e:
        logger.warning(f"备份失败：{e}，继续执行迁移...")

    # 创建引擎
    engine = create_engine(settings.DATABASE_URL)

    try:
        # 先创建基础表（如果是空数据库）
        create_base_tables(engine)

        # 执行迁移
        migrate_users(engine)
        migrate_sessions(engine)
        migrate_messages(engine)
        create_score_history(engine)
        create_user_stats(engine)

        logger.info("=" * 60)
        logger.info("✅ 所有迁移完成！")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 迁移失败：{e}", exc_info=True)
        return False


def rollback_migration():
    """回滚迁移（从备份恢复）"""
    logger.info("=" * 60)
    logger.info("回滚数据库迁移")
    logger.info("=" * 60)

    backup_url = create_backup_url(settings.DATABASE_URL)

    if not os.path.exists(backup_url.replace("sqlite:///", "")):
        logger.error("❌ 备份文件不存在，无法回滚")
        return False

    try:
        # 删除当前数据库
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"已删除数据库：{db_path}")

        # 恢复备份
        backup_path = backup_url.replace("sqlite:///", "")
        import shutil
        shutil.copy(backup_path, db_path)
        logger.info(f"已从备份恢复：{backup_path}")

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

    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    # 检查 Users 表
    logger.info("\nUsers 表字段:")
    if table_exists(engine, "users"):
        columns = [col['name'] for col in inspector.get_columns("users")]
        for col in ["score", "total_score_earned", "highest_score", "risk_preference"]:
            status = "✅" if col in columns else "❌"
            logger.info(f"  {status} {col}")

    # 检查 Sessions 表
    logger.info("\nSessions 表字段:")
    if table_exists(engine, "sessions"):
        columns = [col['name'] for col in inspector.get_columns("sessions")]
        for col in ["is_honeypot", "meta_conversation_count", "final_score", "score_breakdown"]:
            status = "✅" if col in columns else "❌"
            logger.info(f"  {status} {col}")

    # 检查 Messages 表
    logger.info("\nMessages 表字段:")
    if table_exists(engine, "messages"):
        columns = [col['name'] for col in inspector.get_columns("messages")]
        for col in ["is_meta_conversation", "meta_keyword"]:
            status = "✅" if col in columns else "❌"
            logger.info(f"  {status} {col}")

    # 检查新表
    logger.info("\n新创建的表:")
    for table in ["score_history", "user_stats"]:
        status = "✅" if table_exists(engine, table) else "❌"
        logger.info(f"  {status} {table}")

    logger.info("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具")
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
