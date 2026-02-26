#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邀请码功能测试脚本

测试邀请码生成、验证、使用等功能。
"""

import asyncio
import sys
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
project_root = "F:/eliza-py"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from turing_test.backend.database import init_db, close_db, async_session_maker
from turing_test.backend.models import InviteCode, User
from turing_test.backend.services.invite_code_service import InviteCodeService, InviteCodeGenerator
from sqlalchemy import select


async def test_generator():
    """测试邀请码生成器"""
    print("\n" + "=" * 60)
    print("测试邀请码生成器")
    print("=" * 60)

    # 测试单个生成
    print("\n1. 测试单个邀请码生成:")
    code1 = InviteCodeGenerator.generate(length=6)
    code2 = InviteCodeGenerator.generate(length=8)
    code3 = InviteCodeGenerator.generate(prefix="VIP", length=10)
    code4 = InviteCodeGenerator.generate(suffix="2024", length=10)

    print(f"   6 位邀请码：{code1}")
    print(f"   8 位邀请码：{code2}")
    print(f"   带前缀 VIP：{code3}")
    print(f"   带后缀 2024: {code4}")

    # 测试批量生成
    print("\n2. 测试批量生成 (10 个):")
    codes = InviteCodeGenerator.generate_batch(count=10, length=6)
    for i, code in enumerate(codes, 1):
        print(f"   {i}. {code}")

    # 测试唯一性
    print("\n3. 测试唯一性 (生成 100 个不重复):")
    unique_codes = InviteCodeGenerator.generate_batch(
        count=100,
        length=8,
        ensure_unique=True
    )
    print(f"   生成数量：{len(unique_codes)}")
    print(f"   唯一数量：{len(set(unique_codes))}")
    print(f"   唯一性验证：{'通过' if len(unique_codes) == len(set(unique_codes)) else '失败'}")

    return True


async def test_service():
    """测试邀请码服务"""
    print("\n" + "=" * 60)
    print("测试邀请码服务")
    print("=" * 60)

    async with async_session_maker() as db:
        service = InviteCodeService(db)

        # 初始化数据库
        await init_db()

        # 测试创建单个邀请码
        print("\n1. 测试创建单个邀请码:")
        invite_code = await service.create(
            length=8,
            max_uses=1,
            expire_days=30,
            note="测试邀请码"
        )
        print(f"   创建邀请码：{invite_code.code}")
        print(f"   ID: {invite_code.id}")
        print(f"   最大使用次数：{invite_code.max_uses}")
        print(f"   过期时间：{invite_code.expire_at}")

        # 测试批量创建
        print("\n2. 测试批量创建 (20 个):")
        batch_codes = await service.create_batch(
            count=20,
            length=6,
            max_uses=1,
            expire_days=7,
            note="批量测试"
        )
        print(f"   创建数量：{len(batch_codes)}")
        print(f"   批次 ID: {batch_codes[0].batch_id}")
        print(f"   前 5 个邀请码:")
        for ic in batch_codes[:5]:
            print(f"      - {ic.code}")

        # 测试验证
        print("\n3. 测试验证邀请码:")
        result = await service.verify(invite_code.code)
        print(f"   验证有效邀请码：{result['valid']} - {result['message']}")

        # 创建一个已禁用的邀请码
        disabled_code = await service.create(
            length=8,
            note="已禁用测试"
        )
        await service.disable(disabled_code.id)
        result = await service.verify(disabled_code.code)
        print(f"   验证禁用邀请码：{result['valid']} - {result['message']}")

        # 测试使用邀请码
        print("\n4. 测试使用邀请码:")
        # 先创建一个测试用户
        test_user = User(
            username=f"测试用户_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            invite_code="TEST_CODE",
            score=100
        )
        db.add(test_user)
        await db.flush()

        use_result = await service.use(invite_code.code, test_user.id)
        print(f"   使用邀请码：{use_result['success']} - {use_result['message']}")
        print(f"   当前使用次数：{invite_code.current_uses + 1}")

        # 测试查询列表
        print("\n5. 测试查询邀请码列表:")
        codes_list = await service.list(limit=5)
        print(f"   查询前 5 个邀请码:")
        for ic in codes_list:
            status = "已使用" if ic.is_used else "未使用"
            active = "激活" if ic.is_active else "禁用"
            print(f"      - {ic.code} [{status}] [{active}]")

        # 测试统计
        print("\n6. 测试统计信息:")
        stats = await service.get_stats()
        print(f"   总数：{stats['total']}")
        print(f"   激活：{stats['active']}")
        print(f"   已使用：{stats['used']}")
        print(f"   可用：{stats['available']}")
        print(f"   批次：{stats['batches']}")

        await db.commit()

    return True


async def test_api():
    """测试 API 端点（需要服务器运行）"""
    print("\n" + "=" * 60)
    print("测试 API 端点")
    print("=" * 60)
    print("\n请确保后端服务器正在运行 (python turing_test/backend/main.py)")
    print("\n可用 API 端点:")
    print("  POST   /api/invite-codes/create       - 创建单个邀请码")
    print("  POST   /api/invite-codes/batch        - 批量创建邀请码")
    print("  GET    /api/invite-codes/list         - 查询邀请码列表")
    print("  GET    /api/invite-codes/stats        - 获取统计信息")
    print("  GET    /api/invite-codes/{id}         - 查询邀请码详情")
    print("  POST   /api/invite-codes/{id}/disable - 禁用邀请码")
    print("  POST   /api/invite-codes/{id}/enable  - 启用邀请码")
    print("  DELETE /api/invite-codes/{id}         - 删除邀请码")
    print("\n访问 http://localhost:8000/docs 查看完整 API 文档")

    return True


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("邀请码功能测试")
    print("=" * 60)
    print(f"开始时间：{datetime.now()}")

    try:
        # 测试生成器
        await test_generator()

        # 测试服务
        await test_service()

        # 测试 API
        await test_api()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await close_db()
        print(f"结束时间：{datetime.now()}")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
