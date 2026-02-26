#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加分享访问日志功能

功能：
1. 创建 SessionShareAccess 表：分享访问日志记录
2. 记录每次分享链接的访问信息（IP、User-Agent、访问时间）

使用方法：
    python migrations/add_share_access_logs.py

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


def create_share_access_logs(engine):
    """创建 SessionShareAccess 表"""
    logger.info("正在创建 SessionShareAccess 表...")

    if table_exists(engine, "session_share_access_logs"):
        logger.info("  表已存在，跳过")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE session_share_access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                share_id INTEGER NOT NULL,
                ip_address VARCHAR(45) NOT NULL,
                user_agent VARCHAR(500),
                accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (share_id) REFERENCES session_shares(id) ON DELETE CASCADE
            )
        """))

        # 创建索引
        conn.execute(text("CREATE INDEX idx_share_access_logs_share ON session_share_access_logs(share_id)"))
        conn.execute(text("CREATE INDEX idx_share_access_logs_accessed ON session_share_access_logs(accessed_at)"))

    logger.info("✅ SessionShareAccess 表创建完成")


def run_migration():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("数据库迁移：添加分享访问日志功能")
    logger.info("=" * 60)

    # 创建引擎
    engine = create_engine(settings.turing.database.url)

    try:
        # 执行迁移
        create_share_access_logs(engine)

        logger.info("=" * 60)
        logger.info("✅ 所有迁移完成！")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 迁移失败：{e}", exc_info=True)
        return False


def rollback_migration():
    """回滚迁移（删除 SessionShareAccess 表）"""
    logger.info("=" * 60)
    logger.info("回滚数据库迁移")
    logger.info("=" * 60)

    engine = create_engine(settings.turing.database.url)

    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS session_share_access_logs"))

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

    # 检查 SessionShareAccess 表
    logger.info("\nSessionShareAccess 表:")
    if table_exists(engine, "session_share_access_logs"):
        logger.info("  ✅ session_share_access_logs 表已创建")
        columns = [col['name'] for col in inspector.get_columns("session_share_access_logs")]
        required_columns = [
            "id", "share_id", "ip_address", "user_agent", "accessed_at"
        ]
        for col in required_columns:
            status = "✅" if col in columns else "❌"
            logger.info(f"  {status} {col}")
    else:
        logger.info("  ❌ session_share_access_logs 表不存在")

    logger.info("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具：分享访问日志功能")
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
