#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本

功能:
- 创建数据库表结构
- 生成初始邀请码
- 初始化系统数据

使用方法:
    # 初始化数据库并生成 100 个邀请码
    python -m turing_test.backend.scripts.init_db

    # 初始化数据库并生成 500 个邀请码，过期时间 30 天
    python -m turing_test.backend.scripts.init_db --count 500 --expire-days 30

    # 仅创建表结构，不生成邀请码
    python -m turing_test.backend.scripts.init_db --no-invite-codes

    # 重置数据库（删除所有数据后重新初始化）
    python -m turing_test.backend.scripts.init_db --reset
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text, select, func

from turing_test.backend.database import engine, async_session_maker, Base, init_db
from turing_test.backend.models import InviteCode, User, UserStats
from turing_test.backend.services.invite_code_service import InviteCodeService, InviteCodeGenerator
from config import settings


# =============================================================================
# 日志配置
# =============================================================================

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)


# =============================================================================
# 数据库初始化
# =============================================================================

async def create_tables():
    """创建数据库表结构"""
    logger.info("开始创建数据库表结构...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ 数据库表结构创建成功")


async def reset_database():
    """重置数据库（删除所有表后重新创建）"""
    logger.warning("⚠️  即将重置数据库，所有数据将被删除！")

    async with engine.begin() as conn:
        # SQLite 需要特殊处理
        if settings.turing.database.url.startswith("sqlite"):
            # 删除所有表
            await conn.execute(text("DROP TABLE IF EXISTS session_share_access_logs"))
            await conn.execute(text("DROP TABLE IF EXISTS session_shares"))
            await conn.execute(text("DROP TABLE IF EXISTS invite_codes"))
            await conn.execute(text("DROP TABLE IF EXISTS surveys"))
            await conn.execute(text("DROP TABLE IF EXISTS user_stats"))
            await conn.execute(text("DROP TABLE IF EXISTS score_history"))
            await conn.execute(text("DROP TABLE IF EXISTS messages"))
            await conn.execute(text("DROP TABLE IF EXISTS sessions"))
            await conn.execute(text("DROP TABLE IF EXISTS users"))
            logger.info("已删除所有 SQLite 表")
        else:
            # 其他数据库使用 metadata.drop_all
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("已删除所有表")

        # 重新创建所有表
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ 数据库重置成功")


async def check_existing_data() -> bool:
    """检查数据库是否已有数据"""
    from sqlalchemy.exc import OperationalError
    
    async with async_session_maker() as db:
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
        except OperationalError:
            # 表不存在，说明数据库是空的
            logger.info("数据库表结构不存在，将是空数据库初始化")
            return False

        try:
            result = await db.execute(text("SELECT COUNT(*) FROM invite_codes"))
            invite_code_count = result.scalar()
        except OperationalError:
            invite_code_count = 0

        if user_count > 0 or invite_code_count > 0:
            logger.warning(f"数据库中已有数据：{user_count} 个用户，{invite_code_count} 个邀请码")
            return True

        return False


# =============================================================================
# 邀请码生成
# =============================================================================

async def generate_initial_invite_codes(
    count: int = 100,
    length: int = None,
    prefix: str = "",
    suffix: str = "",
    max_uses: int = 1,
    expire_days: int = None,
    batch_note: str = "初始邀请码"
) -> tuple[str, list[str]]:
    """
    生成初始邀请码

    Args:
        count: 生成数量
        length: 邀请码长度（不传则使用配置值）
        prefix: 前缀
        suffix: 后缀
        max_uses: 最大使用次数
        expire_days: 过期天数
        batch_note: 备注

    Returns:
        (批次 ID, 邀请码列表)
    """
    if length is None:
        length = settings.turing.auth.invite_code_length

    logger.info(f"开始生成 {count} 个初始邀请码...")
    logger.info(f"  - 长度：{length}")
    logger.info(f"  - 前缀：{prefix or '(无)'}")
    logger.info(f"  - 后缀：{suffix or '(无)'}")
    logger.info(f"  - 最大使用次数：{max_uses if max_uses != -1 else '无限'}")
    logger.info(f"  - 过期时间：{f'{expire_days} 天' if expire_days else '永不过期'}")

    async with async_session_maker() as db:
        service = InviteCodeService(db)

        # 批量创建
        invite_codes = await service.create_batch(
            count=count,
            length=length,
            prefix=prefix,
            suffix=suffix,
            max_uses=max_uses,
            expire_days=expire_days,
            note=batch_note,
        )

        # 获取批次 ID
        batch_id = invite_codes[0].batch_id if invite_codes else None
        codes = [code.code for code in invite_codes]

        # 提交事务
        await db.commit()

        logger.info(f"✅ 成功生成 {len(codes)} 个邀请码，批次 ID: {batch_id}")

        return batch_id, codes


async def export_invite_codes(codes: list[str], output_file: str = None):
    """导出邀请码到文件"""
    if not output_file:
        output_file = f"invite_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    output_path = Path(output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 邀请码列表\n")
        f.write(f"# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 总数：{len(codes)}\n")
        f.write("#\n")
        for code in codes:
            f.write(f"{code}\n")

    logger.info(f"✅ 邀请码已导出到：{output_path.absolute()}")


# =============================================================================
# 统计信息
# =============================================================================

async def print_stats():
    """打印数据库统计信息"""
    async with async_session_maker() as db:
        logger.info("\n📊 数据库统计信息:")

        # 用户统计
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar()
        logger.info(f"  - 用户总数：{user_count}")

        # 邀请码统计
        result = await db.execute(select(func.count(InviteCode.id)))
        total_codes = result.scalar()

        # 可用邀请码：is_active=True AND is_used=False
        result = await db.execute(
            select(func.count(InviteCode.id)).where(
                InviteCode.is_active == True,
                InviteCode.is_used == False
            )
        )
        available_codes = result.scalar()

        result = await db.execute(
            select(func.count(InviteCode.id)).where(InviteCode.is_used == True)
        )
        used_codes = result.scalar()

        logger.info(f"  - 邀请码总数：{total_codes}")
        logger.info(f"  - 可用邀请码：{available_codes}")
        logger.info(f"  - 已使用：{used_codes}")


# =============================================================================
# 主函数
# =============================================================================

async def main():
    # 调试信息：打印数据库路径
    import os
    logger.info("\n🔍 [DEBUG] 数据库初始化调试信息:")
    logger.info(f"🔍 [DEBUG] 配置文件中的数据库 URL: {settings.turing.database.url}")
    logger.info(f"🔍 [DEBUG] 当前工作目录：{Path.cwd()}")
    logger.info(f"🔍 [DEBUG] PROJECT_ROOT 环境变量：{os.getenv('PROJECT_ROOT', '未设置')}")
    
    # 计算预期的数据库路径
    db_url = settings.turing.database.url
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if not db_path.startswith("/"):
            project_root = os.getenv('PROJECT_ROOT')
            if project_root:
                expected_db_path = str(Path(project_root) / db_path)
            else:
                expected_db_path = str(Path(__file__).parent.parent.parent.parent / db_path)
        else:
            expected_db_path = db_path
        logger.info(f"🔍 [DEBUG] 预期的数据库文件路径：{expected_db_path}")
        logger.info(f"🔍 [DEBUG] 数据库文件是否存在：{Path(expected_db_path).exists()}")
        
        # 检查 /app/data 目录
        data_dir = Path("/app/data")
        if data_dir.exists():
            files = [f.name for f in data_dir.iterdir()]
            logger.info(f"🔍 [DEBUG] /app/data 目录内容：{files}")
        else:
            logger.warning(f"🔍 [DEBUG] /app/data 目录不存在")
    logger.info("")

    parser = argparse.ArgumentParser(
        description="数据库初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 初始化数据库并生成 100 个邀请码
  python -m turing_test.backend.scripts.init_db

  # 生成 500 个邀请码，过期时间 30 天
  python -m turing_test.backend.scripts.init_db --count 500 --expire-days 30

  # 仅创建表结构
  python -m turing_test.backend.scripts.init_db --no-invite-codes

  # 重置数据库
  python -m turing_test.backend.scripts.init_db --reset

  # 自定义邀请码配置
  python -m turing_test.backend.scripts.init_db --count 200 --length 8 --prefix VIP --max-uses 5
        """
    )

    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="生成邀请码数量（默认：100）"
    )
    parser.add_argument(
        "--length",
        type=int,
        default=None,
        help="邀请码长度（默认：使用配置文件中的值）"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="邀请码前缀（默认：无）"
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="邀请码后缀（默认：无）"
    )
    parser.add_argument(
        "--max-uses",
        type=int,
        default=1,
        help="最大使用次数，-1 表示无限（默认：1）"
    )
    parser.add_argument(
        "--expire-days",
        type=int,
        default=None,
        help="过期天数（默认：永不过期）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="邀请码导出文件路径（默认：自动生成）"
    )
    parser.add_argument(
        "--no-invite-codes",
        action="store_true",
        help="不生成邀请码，仅创建表结构"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置数据库（删除所有数据后重新初始化）⚠️  危险操作"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="跳过已有数据检查"
    )

    args = parser.parse_args()

    # 警告提示
    if args.reset:
        logger.warning("⚠️  ⚠️  ⚠️  即将执行重置操作！")
        logger.warning("此操作将删除数据库中所有数据，且不可恢复！")

        confirm = input("\n确认要继续吗？输入 'yes' 确认：")
        if confirm.lower() != 'yes':
            logger.info("操作已取消")
            sys.exit(0)

        await reset_database()
    else:
        # 检查是否已有数据
        if not args.skip_check:
            has_data = await check_existing_data()
            if has_data:
                confirm = input("\n是否继续创建表结构？(y/n): ")
                if confirm.lower() != 'y':
                    logger.info("操作已取消")
                    sys.exit(0)

        # 创建表结构
        await create_tables()

    # 生成邀请码
    if not args.no_invite_codes:
        batch_id, codes = await generate_initial_invite_codes(
            count=args.count,
            length=args.length,
            prefix=args.prefix,
            suffix=args.suffix,
            max_uses=args.max_uses,
            expire_days=args.expire_days,
        )

        # 导出邀请码
        await export_invite_codes(codes, args.output)

        # 打印前 10 个邀请码示例
        logger.info(f"\n📋 邀请码示例（前 10 个）:")
        for code in codes[:10]:
            logger.info(f"  {code}")
        if len(codes) > 10:
            logger.info(f"  ... 还有 {len(codes) - 10} 个邀请码")

    # 打印统计信息
    await print_stats()

    logger.info("\n✅ 数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
