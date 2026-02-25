#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加会话分享功能

功能：
1. 创建 SessionShare 表：会话分享记录
2. 为 Sessions 表添加 shares 关系（无需修改表结构）
3. 为 Users 表添加 shared_sessions 关系（无需修改表结构）

使用方法：
    python migrations/add_session_shares.py

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


def create_session_shares(engine):
    """创建 SessionShare 表"""
    logger.info("正在创建 SessionShare 表...")

    if table_exists(engine, "session_shares"):
        logger.info("  表已存在，跳过")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE session_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                share_token VARCHAR(64) UNIQUE NOT NULL,
                is_public BOOLEAN DEFAULT TRUE,
                expires_at DATETIME,
                password_hash VARCHAR(255),
                view_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))

        # 创建索引
        conn.execute(text("CREATE INDEX idx_session_shares_token ON session_shares(share_token)"))
        conn.execute(text("CREATE INDEX idx_session_shares_session ON session_shares(session_id)"))
        conn.execute(text("CREATE INDEX idx_session_shares_user ON session_shares(user_id)"))

    logger.info("✅ SessionShare 表创建完成")


def run_migration():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("数据库迁移：添加会话分享功能")
    logger.info("=" * 60)

    # 创建引擎
    engine = create_engine(settings.turing.database.url)

    try:
        # 执行迁移
        create_session_shares(engine)

        logger.info("=" * 60)
        logger.info("✅ 所有迁移完成！")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 迁移失败：{e}", exc_info=True)
        return False


def rollback_migration():
    """回滚迁移（删除 SessionShare 表）"""
    logger.info("=" * 60)
    logger.info("回滚数据库迁移")
    logger.info("=" * 60)

    engine = create_engine(settings.turing.database.url)

    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS session_shares"))
        
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

    # 检查 SessionShare 表
    logger.info("\nSessionShare 表:")
    if table_exists(engine, "session_shares"):
        logger.info("  ✅ session_shares 表已创建")
        columns = [col['name'] for col in inspector.get_columns("session_shares")]
        required_columns = [
            "id", "session_id", "user_id", "share_token",
            "is_public", "expires_at", "password_hash",
            "view_count", "created_at", "updated_at"
        ]
        for col in required_columns:
            status = "✅" if col in columns else "❌"
            logger.info(f"  {status} {col}")
    else:
        logger.info("  ❌ session_shares 表不存在")

    logger.info("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具：会话分享功能")
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
