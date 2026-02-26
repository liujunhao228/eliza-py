"""
邀请码服务单元测试

测试邀请码生成、验证、使用等核心功能。
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from turing_test.backend.services.invite_code_service import (
    InviteCodeService,
    InviteCodeGenerator,
)
from turing_test.backend.models import InviteCode, User


# =============================================================================
# 测试夹具
# =============================================================================

@pytest.fixture
def async_session():
    """创建内存数据库会话"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return session_maker


@pytest.fixture
async def db_session(async_session):
    """创建数据库会话并初始化表"""
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with async_session() as session:
        # 创建表
        from turing_test.backend.database import Base
        async with session.begin():
            # 使用 sync engine 创建表
            from sqlalchemy import create_engine
            sync_engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(sync_engine)
        
        yield session
        await session.rollback()


@pytest.fixture
def invite_code_service(db_session):
    """创建邀请码服务实例"""
    return InviteCodeService(db_session)


# =============================================================================
# InviteCodeGenerator 测试
# =============================================================================

class TestInviteCodeGenerator:
    """测试邀请码生成器"""

    def test_generate_default_length(self):
        """测试默认长度生成"""
        code = InviteCodeGenerator.generate()
        assert len(code) == 8  # 默认长度

    def test_generate_custom_length(self):
        """测试自定义长度生成"""
        code = InviteCodeGenerator.generate(length=12)
        assert len(code) == 12

    def test_generate_with_prefix(self):
        """测试带前缀生成"""
        code = InviteCodeGenerator.generate(prefix="TEST")
        assert code.startswith("TEST")
        assert len(code) == 8

    def test_generate_with_suffix(self):
        """测试带后缀生成"""
        code = InviteCodeGenerator.generate(suffix="END")
        assert code.endswith("END")
        assert len(code) == 8

    def test_generate_with_prefix_and_suffix(self):
        """测试带前缀和后缀生成"""
        code = InviteCodeGenerator.generate(prefix="A", suffix="Z")
        assert code.startswith("A")
        assert code.endswith("Z")
        assert len(code) == 8

    def test_generate_custom_charset(self):
        """测试自定义字符集"""
        charset = "ABCDEF"
        code = InviteCodeGenerator.generate(charset=charset)
        assert all(c in charset for c in code)

    def test_generate_invalid_length(self):
        """测试无效长度"""
        with pytest.raises(ValueError):
            InviteCodeGenerator.generate(length=2, prefix="LONG")

    def test_generate_batch(self):
        """测试批量生成"""
        codes = InviteCodeGenerator.generate_batch(count=5)
        assert len(codes) == 5
        assert all(len(code) == 8 for code in codes)

    def test_generate_batch_unique(self):
        """测试批量生成唯一性"""
        codes = InviteCodeGenerator.generate_batch(count=100, ensure_unique=True)
        assert len(codes) == 100
        assert len(set(codes)) == 100  # 所有代码都是唯一的

    def test_generate_batch_with_existing(self):
        """测试批量生成排除已存在代码"""
        existing = ["AAAAAAAA", "BBBBBBBB"]
        codes = InviteCodeGenerator.generate_batch(
            count=5,
            ensure_unique=True,
            existing_codes=existing
        )
        assert all(code not in existing for code in codes)


# =============================================================================
# InviteCodeService 测试
# =============================================================================

class TestInviteCodeService:
    """测试邀请码服务"""

    @pytest.mark.asyncio
    async def test_create_single_code(self, invite_code_service, db_session):
        """测试创建单个邀请码"""
        code = await invite_code_service.create()
        
        assert code.code is not None
        assert code.max_uses == 1
        assert code.current_uses == 0
        assert code.is_active is True
        assert code.is_used is False

    @pytest.mark.asyncio
    async def test_create_custom_code(self, invite_code_service, db_session):
        """测试创建自定义邀请码"""
        code = await invite_code_service.create(code="MYCODE123")
        
        assert code.code == "MYCODE123"

    @pytest.mark.asyncio
    async def test_create_with_expire(self, invite_code_service, db_session):
        """测试创建带过期时间的邀请码"""
        code = await invite_code_service.create(expire_days=30)
        
        assert code.expire_at is not None
        assert code.expire_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_create_batch(self, invite_code_service, db_session):
        """测试批量创建邀请码"""
        codes = await invite_code_service.create_batch(count=5)
        
        assert len(codes) == 5
        # 所有代码属于同一批次
        batch_id = codes[0].batch_id
        assert all(code.batch_id == batch_id for code in codes)

    @pytest.mark.asyncio
    async def test_verify_valid_code(self, invite_code_service, db_session):
        """测试验证有效邀请码"""
        code = await invite_code_service.create()
        result = await invite_code_service.verify(code.code)
        
        assert result["valid"] is True
        assert result["message"] == "邀请码有效"
        assert result["invite_code"] is not None

    @pytest.mark.asyncio
    async def test_verify_nonexistent_code(self, invite_code_service, db_session):
        """测试验证不存在的邀请码"""
        result = await invite_code_service.verify("NOTEXIST")
        
        assert result["valid"] is False
        assert result["message"] == "邀请码不存在"

    @pytest.mark.asyncio
    async def test_verify_disabled_code(self, invite_code_service, db_session):
        """测试验证被禁用的邀请码"""
        code = await invite_code_service.create()
        await invite_code_service.disable(code.id)
        
        result = await invite_code_service.verify(code.code)
        
        assert result["valid"] is False
        assert result["message"] == "邀请码已被禁用"

    @pytest.mark.asyncio
    async def test_verify_expired_code(self, invite_code_service, db_session):
        """测试验证过期的邀请码"""
        # 创建已过期的邀请码
        code = await invite_code_service.create(expire_days=-1)
        
        result = await invite_code_service.verify(code.code)
        
        assert result["valid"] is False
        assert result["message"] == "邀请码已过期"

    @pytest.mark.asyncio
    async def test_verify_max_uses_reached(self, invite_code_service, db_session):
        """测试验证达到最大使用次数的邀请码"""
        code = await invite_code_service.create(max_uses=2)
        # 模拟使用 2 次
        code.current_uses = 2
        await db_session.flush()
        
        result = await invite_code_service.verify(code.code)
        
        assert result["valid"] is False
        assert result["message"] == "邀请码已达到最大使用次数"

    @pytest.mark.asyncio
    async def test_use_code_success(self, invite_code_service, db_session):
        """测试使用邀请码成功"""
        code = await invite_code_service.create()
        user_id = 123
        
        result = await invite_code_service.use(code.code, user_id)
        
        assert result["success"] is True
        assert result["message"] == "邀请码使用成功"
        assert code.current_uses == 1
        assert code.used_by_user_id == user_id

    @pytest.mark.asyncio
    async def test_use_code_invalid(self, invite_code_service, db_session):
        """测试使用无效邀请码"""
        result = await invite_code_service.use("NOTEXIST", 123)
        
        assert result["success"] is False
        assert result["message"] == "邀请码不存在"

    @pytest.mark.asyncio
    async def test_get_by_code(self, invite_code_service, db_session):
        """测试根据代码查询邀请码"""
        code = await invite_code_service.create(code="TESTCODE")
        
        result = await invite_code_service.get_by_code("TESTCODE")
        
        assert result is not None
        assert result.code == "TESTCODE"

    @pytest.mark.asyncio
    async def test_get_by_id(self, invite_code_service, db_session):
        """测试根据 ID 查询邀请码"""
        code = await invite_code_service.create()
        
        result = await invite_code_service.get_by_id(code.id)
        
        assert result is not None
        assert result.id == code.id

    @pytest.mark.asyncio
    async def test_list_codes(self, invite_code_service, db_session):
        """测试查询邀请码列表"""
        # 创建多个邀请码
        await invite_code_service.create_batch(count=5)
        
        codes = await invite_code_service.list(limit=10)
        
        assert len(codes) == 5

    @pytest.mark.asyncio
    async def test_list_filter_active(self, invite_code_service, db_session):
        """测试按激活状态筛选"""
        code1 = await invite_code_service.create()
        code2 = await invite_code_service.create()
        await invite_code_service.disable(code2.id)
        
        active_codes = await invite_code_service.list(is_active=True)
        disabled_codes = await invite_code_service.list(is_active=False)
        
        assert len(active_codes) == 1
        assert len(disabled_codes) == 1

    @pytest.mark.asyncio
    async def test_disable_code(self, invite_code_service, db_session):
        """测试禁用邀请码"""
        code = await invite_code_service.create()
        
        result = await invite_code_service.disable(code.id)
        
        assert result is not None
        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_enable_code(self, invite_code_service, db_session):
        """测试启用邀请码"""
        code = await invite_code_service.create()
        await invite_code_service.disable(code.id)
        
        result = await invite_code_service.enable(code.id)
        
        assert result is not None
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_delete_code(self, invite_code_service, db_session):
        """测试删除邀请码"""
        code = await invite_code_service.create()
        
        result = await invite_code_service.delete(code.id)
        
        assert result is True
        # 验证已删除
        deleted = await invite_code_service.get_by_id(code.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_get_stats(self, invite_code_service, db_session):
        """测试获取统计信息"""
        # 创建多个邀请码
        await invite_code_service.create_batch(count=5)
        code = await invite_code_service.create()
        await invite_code_service.use(code.code, 123)
        await invite_code_service.disable(code.id)
        
        stats = await invite_code_service.get_stats()
        
        assert stats["total"] == 6
        assert stats["active"] == 5
        assert stats["used"] == 1
        assert stats["disabled"] == 1


# =============================================================================
# 集成测试
# =============================================================================

class TestInviteCodeIntegration:
    """邀请码集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, invite_code_service, db_session):
        """测试完整工作流程：创建 -> 验证 -> 使用"""
        # 创建邀请码
        code = await invite_code_service.create(
            max_uses=3,
            expire_days=30
        )
        
        # 验证
        verify_result = await invite_code_service.verify(code.code)
        assert verify_result["valid"] is True
        
        # 使用 3 次
        for i in range(3):
            use_result = await invite_code_service.use(code.code, i + 1)
            assert use_result["success"] is True
        
        # 再次验证应该失败
        verify_result = await invite_code_service.verify(code.code)
        assert verify_result["valid"] is False
        assert verify_result["message"] == "邀请码已达到最大使用次数"


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
