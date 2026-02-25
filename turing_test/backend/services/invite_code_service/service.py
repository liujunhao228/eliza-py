"""
邀请码服务模块

负责邀请码的 CRUD 服务、验证和使用。
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from turing_test.backend.models import InviteCode, User
from .generator import InviteCodeGenerator


class InviteCodeService:
    """邀请码服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        code: Optional[str] = None,
        length: Optional[int] = None,
        prefix: str = "",
        suffix: str = "",
        max_uses: int = 1,
        expire_days: Optional[int] = None,
        batch_id: Optional[str] = None,
        note: Optional[str] = None
    ) -> InviteCode:
        """
        创建邀请码

        Args:
            code: 自定义邀请码，不传则自动生成
            length: 自动生成时的长度
            prefix: 前缀
            suffix: 后缀
            max_uses: 最大使用次数，-1 表示无限
            expire_days: 过期天数，None 表示永不过期
            batch_id: 批次 ID
            note: 备注

        Returns:
            创建的邀请码对象
        """
        # 生成或验证邀请码
        if code is None:
            code = InviteCodeGenerator.generate(
                length=length,
                prefix=prefix,
                suffix=suffix
            )

        # 计算过期时间
        expire_at = None
        if expire_days is not None:
            expire_at = datetime.now(timezone.utc) + timedelta(days=expire_days)

        # 创建邀请码记录
        invite_code = InviteCode(
            code=code,
            max_uses=max_uses,
            current_uses=0,
            is_active=True,
            is_used=False if max_uses <= 1 else False,
            batch_id=batch_id,
            expire_at=expire_at,
            note=note,
        )

        self.db.add(invite_code)
        await self.db.flush()
        await self.db.refresh(invite_code)

        logger.info(f"创建邀请码：{code}")
        return invite_code

    async def create_batch(
        self,
        count: int,
        length: Optional[int] = None,
        prefix: str = "",
        suffix: str = "",
        max_uses: int = 1,
        expire_days: Optional[int] = None,
        batch_id: Optional[str] = None,
        note: Optional[str] = None
    ) -> List[InviteCode]:
        """
        批量创建邀请码

        Args:
            count: 创建数量
            length: 邀请码长度
            prefix: 前缀
            suffix: 后缀
            max_uses: 最大使用次数
            expire_days: 过期天数
            batch_id: 批次 ID
            note: 备注

        Returns:
            邀请码列表
        """
        # 获取已存在的邀请码
        result = await self.db.execute(select(InviteCode.code))
        existing_codes = [row[0] for row in result.all()]

        # 生成唯一邀请码
        codes = InviteCodeGenerator.generate_batch(
            count=count,
            length=length,
            prefix=prefix,
            suffix=suffix,
            ensure_unique=True,
            existing_codes=existing_codes
        )

        # 计算过期时间
        expire_at = None
        if expire_days is not None:
            expire_at = datetime.now(timezone.utc) + timedelta(days=expire_days)

        # 如果没有提供 batch_id，生成一个
        if batch_id is None:
            batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 批量创建
        invite_codes = []
        for code in codes:
            invite_code = InviteCode(
                code=code,
                max_uses=max_uses,
                current_uses=0,
                is_active=True,
                is_used=False if max_uses <= 1 else False,
                batch_id=batch_id,
                expire_at=expire_at,
                note=note,
            )
            self.db.add(invite_code)
            invite_codes.append(invite_code)

        await self.db.flush()

        logger.info(f"批量创建 {len(invite_codes)} 个邀请码，批次：{batch_id}")
        return invite_codes

    async def verify(self, code: str) -> Dict[str, Any]:
        """
        验证邀请码

        Args:
            code: 邀请码

        Returns:
            验证结果：{
                "valid": bool,
                "message": str,
                "invite_code": Optional[InviteCode]
            }
        """
        # 查询邀请码
        result = await self.db.execute(
            select(InviteCode).where(InviteCode.code == code)
        )
        invite_code = result.scalar_one_or_none()

        # 检查是否存在
        if invite_code is None:
            return {
                "valid": False,
                "message": "邀请码不存在",
                "invite_code": None
            }

        # 检查是否激活
        if not invite_code.is_active:
            return {
                "valid": False,
                "message": "邀请码已被禁用",
                "invite_code": invite_code
            }

        # 检查是否过期
        if invite_code.expire_at and invite_code.expire_at < datetime.now(timezone.utc):
            return {
                "valid": False,
                "message": "邀请码已过期",
                "invite_code": invite_code
            }

        # 检查使用次数
        if invite_code.max_uses != -1 and invite_code.current_uses >= invite_code.max_uses:
            return {
                "valid": False,
                "message": "邀请码已达到最大使用次数",
                "invite_code": invite_code
            }

        return {
            "valid": True,
            "message": "邀请码有效",
            "invite_code": invite_code
        }

    async def use(
        self,
        code: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        使用邀请码

        Args:
            code: 邀请码
            user_id: 用户 ID

        Returns:
            使用结果：{
                "success": bool,
                "message": str,
                "invite_code": Optional[InviteCode]
            }
        """
        # 验证邀请码
        verification = await self.verify(code)
        if not verification["valid"]:
            return {
                "success": False,
                "message": verification["message"],
                "invite_code": None
            }

        invite_code = verification["invite_code"]

        # 更新使用信息
        invite_code.current_uses += 1
        invite_code.used_by_user_id = user_id
        invite_code.used_at = datetime.now(timezone.utc)

        # 如果达到最大使用次数，标记为已使用
        if invite_code.max_uses != -1 and invite_code.current_uses >= invite_code.max_uses:
            invite_code.is_used = True

        await self.db.flush()
        await self.db.refresh(invite_code)

        logger.info(f"邀请码 {code} 被用户 {user_id} 使用")
        return {
            "success": True,
            "message": "邀请码使用成功",
            "invite_code": invite_code
        }

    async def get_by_code(self, code: str) -> Optional[InviteCode]:
        """根据邀请码查询"""
        result = await self.db.execute(
            select(InviteCode).where(InviteCode.code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, code_id: int) -> Optional[InviteCode]:
        """根据 ID 查询"""
        result = await self.db.execute(
            select(InviteCode).where(InviteCode.id == code_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        is_active: Optional[bool] = None,
        is_used: Optional[bool] = None,
        batch_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[InviteCode]:
        """
        查询邀请码列表

        Args:
            is_active: 筛选激活状态
            is_used: 筛选使用状态
            batch_id: 筛选批次
            limit: 限制数量
            offset: 偏移量

        Returns:
            邀请码列表
        """
        query = select(InviteCode)

        if is_active is not None:
            query = query.where(InviteCode.is_active == is_active)
        if is_used is not None:
            query = query.where(InviteCode.is_used == is_used)
        if batch_id is not None:
            query = query.where(InviteCode.batch_id == batch_id)

        query = query.order_by(InviteCode.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def disable(self, code_id: int) -> Optional[InviteCode]:
        """禁用邀请码"""
        invite_code = await self.get_by_id(code_id)
        if invite_code:
            invite_code.is_active = False
            await self.db.flush()
            await self.db.refresh(invite_code)
            logger.info(f"禁用邀请码：{invite_code.code}")
        return invite_code

    async def enable(self, code_id: int) -> Optional[InviteCode]:
        """启用邀请码"""
        invite_code = await self.get_by_id(code_id)
        if invite_code:
            invite_code.is_active = True
            await self.db.flush()
            await self.db.refresh(invite_code)
            logger.info(f"启用邀请码：{invite_code.code}")
        return invite_code

    async def delete(self, code_id: int) -> bool:
        """删除邀请码"""
        invite_code = await self.get_by_id(code_id)
        if invite_code:
            await self.db.delete(invite_code)
            await self.db.flush()
            logger.info(f"删除邀请码：{invite_code.code}")
            return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取邀请码统计信息

        Returns:
            统计信息
        """
        # 总数
        result = await self.db.execute(select(InviteCode))
        all_codes = list(result.scalars().all())

        total = len(all_codes)
        active = sum(1 for c in all_codes if c.is_active)
        used = sum(1 for c in all_codes if c.is_used)
        expired = sum(
            1 for c in all_codes
            if c.expire_at and c.expire_at < datetime.now(timezone.utc)
        )

        # 批次统计
        batch_ids = set(c.batch_id for c in all_codes if c.batch_id)

        return {
            "total": total,
            "active": active,
            "used": used,
            "expired": expired,
            "disabled": total - active,
            "available": active - used,
            "batches": len(batch_ids),
        }
