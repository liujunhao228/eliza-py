"""
邀请码服务模块

提供邀请码生成、验证、使用等功能。
"""

from .generator import InviteCodeGenerator
from .service import InviteCodeService

__all__ = [
    "InviteCodeGenerator",
    "InviteCodeService",
    "get_invite_code_service",
]


# =============================================================================
# 依赖注入
# =============================================================================

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from turing_test.backend.database import get_db


async def get_invite_code_service(db: AsyncSession = Depends(get_db)) -> InviteCodeService:
    """
    获取邀请码服务实例（用于 FastAPI 依赖注入）

    用法:
        @router.get("/test")
        async def test(service: InviteCodeService = Depends(get_invite_code_service)):
            ...
    """
    return InviteCodeService(db)
