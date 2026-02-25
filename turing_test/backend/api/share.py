"""
分享会话 API

提供创建、管理和访问会话分享链接的功能。
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from jose import jwt, JWTError
import bcrypt

from turing_test.backend.database import get_db
from turing_test.backend.models import User, Session, SessionShare, Message
from turing_test.backend.schemas import (
    CreateShareRequest,
    CreateShareResponse,
    ShareInfoResponse,
    SharedMessagesResponse,
    UpdateShareRequest,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
    SuccessResponse,
    MessageResponse,
)
from config import settings
from loguru import logger

router = APIRouter()
FRONTEND_URL = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')


def _normalize_opponent_type(opponent_type: str) -> str:
    if opponent_type == "honeypot":
        return "ai"
    return opponent_type


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="认证格式错误")
    try:
        payload = jwt.decode(token, settings.turing.auth.secret_key, algorithms=[settings.turing.auth.algorithm])
        user_id = int(payload.get("sub", 0))
        if user_id == 0:
            raise HTTPException(status_code=401, detail="无效的 token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 已过期或无效")


def generate_share_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode('utf-8')[:72]
    return bcrypt.checkpw(plain_bytes, hashed.encode('utf-8'))


def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)) -> str:
    to_encode = data.copy()
    expire = now_utc() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.turing.auth.secret_key, algorithm=settings.turing.auth.algorithm)


@router.post("/session/{session_id}/share", response_model=CreateShareResponse, tags=["分享会话"])
async def create_session_share(
    session_id: int, request: CreateShareRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="仅会话所有者可创建分享")
    
    existing_result = await db.execute(
        select(SessionShare).where(
            SessionShare.session_id == session_id,
            SessionShare.user_id == current_user_id,
            (SessionShare.expires_at.is_(None) | (SessionShare.expires_at > now_utc()))
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该会话已有有效分享链接")
    
    share_token = generate_share_token()
    expires_at = now_utc() + timedelta(days=request.expires_days) if request.expires_days else None
    password_hash = hash_password(request.password) if request.password else None
    
    share = SessionShare(
        session_id=session_id, user_id=current_user_id, share_token=share_token,
        is_public=request.is_public, expires_at=expires_at, password_hash=password_hash,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    
    logger.info(f"创建分享：user_id={current_user_id}, session_id={session_id}, token={share_token}")
    return CreateShareResponse(
        share_id=share.id, share_token=share_token,
        share_url=f"{FRONTEND_URL}/share/{share_token}",
        expires_at=share.expires_at, has_password=share.password_hash is not None,
    )


@router.get("/share/{share_token}", response_model=ShareInfoResponse, tags=["分享会话"])
async def get_share_info(share_token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SessionShare).options(joinedload(SessionShare.session)).where(SessionShare.share_token == share_token)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")
    
    is_expired = share.expires_at is not None and share.expires_at < now_utc()
    session = share.session
    return ShareInfoResponse(
        session_id=session.id, opponent_type=_normalize_opponent_type(session.opponent_type),
        turn_count=session.turn_count, final_score=session.final_score, is_correct=session.is_correct,
        started_at=session.started_at, ended_at=session.ended_at, view_count=share.view_count,
        is_expired=is_expired, requires_password=share.password_hash is not None,
    )


@router.post("/share/{share_token}/verify-password", response_model=VerifyPasswordResponse, tags=["分享会话"])
async def verify_share_password(share_token: str, request: VerifyPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SessionShare).where(SessionShare.share_token == share_token))
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")
    if not share.password_hash:
        return VerifyPasswordResponse(success=True, message="该分享无需密码")
    if not verify_password(request.password, share.password_hash):
        raise HTTPException(status_code=403, detail="密码错误")
    
    access_token = create_access_token({"sub": f"share:{share_token}", "share_token": share_token})
    return VerifyPasswordResponse(success=True, message="密码验证通过", access_token=access_token)


@router.get("/share/{share_token}/messages", response_model=SharedMessagesResponse, tags=["分享会话"])
async def get_shared_messages(
    share_token: str, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SessionShare).options(joinedload(SessionShare.session)).where(SessionShare.share_token == share_token)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")
    
    session = share.session
    if share.expires_at and share.expires_at < now_utc():
        raise HTTPException(status_code=410, detail="分享已过期")
    
    if share.password_hash:
        if not authorization:
            raise HTTPException(status_code=401, detail="需要密码验证")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="认证格式错误")
        try:
            payload = jwt.decode(token, settings.turing.auth.secret_key, algorithms=[settings.turing.auth.algorithm])
            if payload.get("share_token") != share_token:
                raise HTTPException(status_code=403, detail="访问令牌无效")
        except JWTError:
            raise HTTPException(status_code=403, detail="访问令牌已过期或无效")
    
    msg_result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()
    share.view_count += 1
    await db.commit()
    
    return SharedMessagesResponse(
        session_id=session.id, opponent_type=_normalize_opponent_type(session.opponent_type),
        messages=[
            MessageResponse(
                id=msg.id, session_id=msg.session_id, sender=msg.sender, content=msg.content,
                is_meta_conversation=msg.is_meta_conversation, meta_keyword=msg.meta_keyword,
                created_at=msg.created_at,
            ) for msg in messages
        ],
    )


@router.put("/share/{share_id}", response_model=CreateShareResponse, tags=["分享会话"])
async def update_share(
    share_id: int, request: UpdateShareRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SessionShare).where(SessionShare.id == share_id))
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")
    if share.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="仅分享所有者可更新")
    
    if request.is_public is not None:
        share.is_public = request.is_public
    if request.expires_days is not None:
        share.expires_at = now_utc() + timedelta(days=request.expires_days)
    if request.password is not None:
        share.password_hash = hash_password(request.password) if request.password else None
    
    await db.commit()
    await db.refresh(share)
    return CreateShareResponse(
        share_id=share.id, share_token=share.share_token,
        share_url=f"{FRONTEND_URL}/share/{share.share_token}",
        expires_at=share.expires_at, has_password=share.password_hash is not None,
    )


@router.delete("/share/{share_id}", response_model=SuccessResponse, tags=["分享会话"])
async def delete_share(
    share_id: int, current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SessionShare).where(SessionShare.id == share_id))
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")
    if share.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="仅分享所有者可删除")
    
    logger.info(f"删除分享：user_id={current_user_id}, share_id={share_id}")
    await db.delete(share)
    await db.commit()
    return SuccessResponse(success=True, message="分享链接已删除")
