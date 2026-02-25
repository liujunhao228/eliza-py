"""
邀请码管理 API 路由

提供邀请码的生成、查询、禁用等管理功能。
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict

from turing_test.backend.database import get_db
from turing_test.backend.services.invite_code_service import get_invite_code_service, InviteCodeService
from turing_test.backend.schemas import SuccessResponse, ErrorResponse

router = APIRouter()


# =============================================================================
# Schema 定义
# =============================================================================

class InviteCodeResponse(BaseModel):
    """邀请码响应"""
    id: int
    code: str
    is_active: bool
    is_used: bool
    max_uses: int
    current_uses: int
    used_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    batch_id: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InviteCodeCreateRequest(BaseModel):
    """创建邀请码请求"""
    code: Optional[str] = Field(None, max_length=20, description="自定义邀请码，不传则自动生成")
    length: Optional[int] = Field(None, ge=4, le=20, description="自动生成时的长度")
    prefix: str = Field("", max_length=10, description="前缀")
    suffix: str = Field("", max_length=10, description="后缀")
    max_uses: int = Field(1, ge=-1, description="最大使用次数，-1 表示无限")
    expire_days: Optional[int] = Field(None, ge=1, description="过期天数")
    note: Optional[str] = Field(None, max_length=200, description="备注")


class InviteCodeBatchRequest(BaseModel):
    """批量创建邀请码请求"""
    count: int = Field(..., ge=1, le=1000, description="创建数量")
    length: Optional[int] = Field(None, ge=4, le=20, description="邀请码长度")
    prefix: str = Field("", max_length=10, description="前缀")
    suffix: str = Field("", max_length=10, description="后缀")
    max_uses: int = Field(1, ge=-1, description="最大使用次数")
    expire_days: Optional[int] = Field(None, ge=1, description="过期天数")
    note: Optional[str] = Field(None, max_length=200, description="备注")


class InviteCodeListRequest(BaseModel):
    """邀请码列表查询参数"""
    is_active: Optional[bool] = Field(None, description="筛选激活状态")
    is_used: Optional[bool] = Field(None, description="筛选使用状态")
    batch_id: Optional[str] = Field(None, description="筛选批次")
    limit: int = Field(100, ge=1, le=500, description="限制数量")
    offset: int = Field(0, ge=0, description="偏移量")


class InviteCodeStatsResponse(BaseModel):
    """邀请码统计响应"""
    total: int
    active: int
    used: int
    expired: int
    disabled: int
    available: int
    batches: int


class InviteCodeBatchResponse(BaseModel):
    """批量创建邀请码响应"""
    batch_id: str
    count: int
    codes: List[str]


# =============================================================================
# 路由
# =============================================================================

@router.post(
    "/create",
    response_model=InviteCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建邀请码",
    description="创建单个邀请码，可自定义或自动生成",
)
async def create_invite_code(
    request: InviteCodeCreateRequest,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """创建单个邀请码"""
    invite_code = await invite_code_service.create(
        code=request.code,
        length=request.length,
        prefix=request.prefix,
        suffix=request.suffix,
        max_uses=request.max_uses,
        expire_days=request.expire_days,
        note=request.note,
    )
    return InviteCodeResponse.model_validate(invite_code)


@router.post(
    "/batch",
    response_model=InviteCodeBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量创建邀请码",
    description="批量生成邀请码",
)
async def batch_create_invite_codes(
    request: InviteCodeBatchRequest,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """批量创建邀请码"""
    invite_codes = await invite_code_service.create_batch(
        count=request.count,
        length=request.length,
        prefix=request.prefix,
        suffix=request.suffix,
        max_uses=request.max_uses,
        expire_days=request.expire_days,
        note=request.note,
    )

    return InviteCodeBatchResponse(
        batch_id=invite_codes[0].batch_id if invite_codes else None,
        count=len(invite_codes),
        codes=[ic.code for ic in invite_codes],
    )


@router.get(
    "/list",
    response_model=List[InviteCodeResponse],
    summary="查询邀请码列表",
    description="查询邀请码列表，支持筛选",
)
async def list_invite_codes(
    is_active: Optional[bool] = Query(None, description="筛选激活状态"),
    is_used: Optional[bool] = Query(None, description="筛选使用状态"),
    batch_id: Optional[str] = Query(None, description="筛选批次"),
    limit: int = Query(100, ge=1, le=500, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """查询邀请码列表"""
    invite_codes = await invite_code_service.list(
        is_active=is_active,
        is_used=is_used,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )
    return [InviteCodeResponse.model_validate(ic) for ic in invite_codes]


@router.get(
    "/{code_id}",
    response_model=InviteCodeResponse,
    summary="查询邀请码详情",
    description="根据 ID 查询邀请码详情",
)
async def get_invite_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """查询邀请码详情"""
    invite_code = await invite_code_service.get_by_id(code_id)
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    return InviteCodeResponse.model_validate(invite_code)


@router.post(
    "/{code_id}/disable",
    response_model=InviteCodeResponse,
    summary="禁用邀请码",
    description="禁用指定邀请码",
)
async def disable_invite_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """禁用邀请码"""
    invite_code = await invite_code_service.disable(code_id)
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    return InviteCodeResponse.model_validate(invite_code)


@router.post(
    "/{code_id}/enable",
    response_model=InviteCodeResponse,
    summary="启用邀请码",
    description="启用已禁用的邀请码",
)
async def enable_invite_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """启用邀请码"""
    invite_code = await invite_code_service.enable(code_id)
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    return InviteCodeResponse.model_validate(invite_code)


@router.delete(
    "/{code_id}",
    response_model=SuccessResponse,
    summary="删除邀请码",
    description="删除指定邀请码",
)
async def delete_invite_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """删除邀请码"""
    success = await invite_code_service.delete(code_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    return SuccessResponse(message="邀请码已删除")


@router.get(
    "/stats",
    response_model=InviteCodeStatsResponse,
    summary="邀请码统计",
    description="获取邀请码使用统计",
)
async def get_invite_code_stats(
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """获取邀请码统计信息"""
    stats = await invite_code_service.get_stats()
    return InviteCodeStatsResponse(**stats)


@router.get(
    "/batch/{batch_id}",
    response_model=List[InviteCodeResponse],
    summary="查询批次邀请码",
    description="查询指定批次的所有邀请码",
)
async def get_batch_invite_codes(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    invite_code_service: InviteCodeService = Depends(get_invite_code_service)
):
    """查询批次邀请码"""
    invite_codes = await invite_code_service.list(batch_id=batch_id, limit=500)
    if not invite_codes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该批次不存在或没有邀请码"
        )
    return [InviteCodeResponse.model_validate(ic) for ic in invite_codes]
