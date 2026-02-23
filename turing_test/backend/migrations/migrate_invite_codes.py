#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邀请码迁移脚本

将 invite_codes.txt 中的邀请码导入到数据库。
"""

import asyncio
import sys
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
project_root = "F:/eliza-py"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from turing_test.backend.database import init_db, close_db, async_session_maker
from turing_test.backend.models import InviteCode
from turing_test.backend.services.invite_code_service import InviteCodeService
from sqlalchemy import select


async def migrate_invite_codes():
    """迁移邀请码"""
    print("\n" + "=" * 60)
    print("邀请码迁移脚本")
    print("=" * 60)

    # 读取 invite_codes.txt
    invite_codes_file = "F:/eliza-py/invite_codes.txt"
    
    try:
        with open(invite_codes_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ 文件不存在：{invite_codes_file}")
        return False

    # 解析邀请码（跳过注释行）
    codes_to_migrate = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            codes_to_migrate.append(line)

    print(f"\n📋 从文件中读取到 {len(codes_to_migrate)} 个邀请码")

    async with async_session_maker() as db:
        service = InviteCodeService(db)
        await init_db()

        # 检查数据库中已存在的邀请码
        result = await db.execute(select(InviteCode.code))
        existing_codes = set(row[0] for row in result.all())
        
        print(f"💾 数据库中已有 {len(existing_codes)} 个邀请码")

        # 过滤掉已存在的邀请码
        new_codes = [code for code in codes_to_migrate if code not in existing_codes]
        
        print(f"🆕 需要导入 {len(new_codes)} 个新邀请码")

        if not new_codes:
            print("✅ 没有需要导入的邀请码")
            await db.commit()
            return True

        # 生成批次 ID
        batch_id = f"migrate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"📦 批次 ID: {batch_id}")
        print(f"\n开始导入...")

        # 批量创建
        count = 0
        for code in new_codes:
            try:
                invite_code = InviteCode(
                    code=code,
                    max_uses=1,
                    current_uses=0,
                    is_active=True,
                    is_used=False,
                    batch_id=batch_id,
                    expire_at=datetime.utcnow() + timedelta(days=365),  # 1 年有效期
                    note="从 invite_codes.txt 迁移",
                )
                db.add(invite_code)
                count += 1
                
                # 每 50 个提交一次
                if count % 50 == 0:
                    await db.flush()
                    print(f"  已导入 {count}/{len(new_codes)} 个")
                    
            except Exception as e:
                print(f"⚠️ 导入失败 {code}: {e}")

        # 提交剩余数据
        await db.flush()
        await db.commit()

        print(f"\n✅ 成功导入 {count} 个邀请码")
        print(f"📊 导入后数据库共有 {len(existing_codes) + count} 个邀请码")

    return True


async def main():
    """主函数"""
    print(f"\n开始时间：{datetime.now()}")
    
    try:
        success = await migrate_invite_codes()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 迁移完成!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 迁移失败!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ 迁移过程出错：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await close_db()
        print(f"\n结束时间：{datetime.now()}")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
