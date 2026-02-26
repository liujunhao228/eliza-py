"""
历史会话与分享功能测试

测试覆盖:
1. 历史会话列表 API
2. 会话详情 API
3. 会话消息 API
4. 创建分享链接
5. 获取分享信息
6. 密码验证
7. 获取分享消息
8. 更新/删除分享
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from turing_test.backend.models import User, Session, Message, SessionShare
from turing_test.backend.database import get_db


# =============================================================================
# 测试夹具 (Fixtures)
# =============================================================================
# 注意：test_user、test_session、test_messages、auth_headers、client、db_session
# 已在 tests/conftest.py 中定义


# =============================================================================
# 历史会话 API 测试
# =============================================================================

class TestHistoryAPI:
    """历史会话 API 测试"""

    @pytest.mark.asyncio
    async def test_get_user_sessions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session
    ):
        """获取用户会话列表"""
        response = await client.get(
            f"/api/user/{test_session.user_id}/sessions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # 响应可能是列表或包含 items 的对象
        if isinstance(data, list):
            assert len(data) >= 1
            assert data[0]["id"] == test_session.id
        else:
            assert "items" in data
            assert len(data["items"]) >= 1
            assert data["items"][0]["id"] == test_session.id

    @pytest.mark.asyncio
    async def test_get_user_sessions_unauthorized(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """未授权访问其他用户会话"""
        # 尝试访问不存在的用户 ID
        response = await client.get(
            "/api/user/99999/sessions",
            headers=auth_headers
        )
        # 404 或 403 都是可以接受的
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_get_session_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session
    ):
        """获取会话详情"""
        response = await client.get(
            f"/api/session/{test_session.id}/detail",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session.id
        assert data["turn_count"] == test_session.turn_count

    @pytest.mark.asyncio
    async def test_get_session_messages(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session,
        test_messages: list[Message]
    ):
        """获取会话消息"""
        response = await client.get(
            f"/api/session/{test_session.id}/messages",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == len(test_messages)

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """获取不存在的会话"""
        response = await client.get(
            "/api/session/99999/detail",
            headers=auth_headers
        )
        assert response.status_code == 404


# =============================================================================
# 分享会话 API 测试
# =============================================================================

class TestShareAPI:
    """分享会话 API 测试"""

    @pytest.mark.asyncio
    async def test_create_share(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session
    ):
        """创建分享链接"""
        response = await client.post(
            f"/api/session/{test_session.id}/share",
            json={
                "is_public": True,
                "expires_days": 7
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "share_token" in data
        assert "share_url" in data

    @pytest.mark.asyncio
    async def test_create_share_duplicate(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session
    ):
        """重复创建分享"""
        # 第一次创建
        await client.post(
            f"/api/session/{test_session.id}/share",
            json={"is_public": True},
            headers=auth_headers
        )
        
        # 第二次创建应失败
        response = await client.post(
            f"/api/session/{test_session.id}/share",
            json={"is_public": True},
            headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_share_with_password(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session
    ):
        """创建带密码的分享"""
        response = await client.post(
            f"/api/session/{test_session.id}/share",
            json={
                "is_public": False,
                "password": "test_password_123"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_password"] is True

    @pytest.mark.asyncio
    async def test_get_share_info(
        self,
        client: AsyncClient,
        test_session: Session,
        db_session: AsyncSession
    ):
        """获取分享信息（公开）"""
        # 先创建分享
        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_share_token_123",
            is_public=True,
        )
        db_session.add(share)
        await db_session.commit()

        response = await client.get("/api/share/test_share_token_123")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == test_session.id

    @pytest.mark.asyncio
    async def test_verify_share_password(
        self,
        client: AsyncClient,
        test_session: Session,
        db_session: AsyncSession
    ):
        """验证分享密码"""
        import bcrypt
        
        password = "correct_password"
        password_hash = bcrypt.hashpw(
            password.encode('utf-8')[:72],
            bcrypt.gensalt()
        ).decode('utf-8')

        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_password_share",
            is_public=False,
            password_hash=password_hash,
        )
        db_session.add(share)
        await db_session.commit()

        # 正确密码
        response = await client.post(
            "/api/share/test_password_share/verify-password",
            json={"password": password}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data

        # 错误密码
        response = await client.post(
            "/api/share/test_password_share/verify-password",
            json={"password": "wrong_password"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_shared_messages(
        self,
        client: AsyncClient,
        test_session: Session,
        test_messages: list[Message],
        db_session: AsyncSession
    ):
        """获取分享会话消息"""
        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_messages_share",
            is_public=True,
        )
        db_session.add(share)
        await db_session.commit()

        response = await client.get("/api/share/test_messages_share/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == len(test_messages)

    @pytest.mark.asyncio
    async def test_get_shared_messages_expired(
        self,
        client: AsyncClient,
        test_session: Session,
        db_session: AsyncSession
    ):
        """获取已过期的分享消息"""
        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_expired_share",
            is_public=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db_session.add(share)
        await db_session.commit()

        response = await client.get("/api/share/test_expired_share/messages")
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_update_share(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session,
        db_session: AsyncSession
    ):
        """更新分享设置"""
        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_update_share",
            is_public=True,
        )
        db_session.add(share)
        await db_session.commit()

        response = await client.put(
            f"/api/share/{share.id}",
            json={"is_public": False, "expires_days": 30},
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_share(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session,
        db_session: AsyncSession
    ):
        """删除分享"""
        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_delete_share",
            is_public=True,
        )
        db_session.add(share)
        await db_session.commit()

        response = await client.delete(
            f"/api/share/{share.id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        # 验证已删除
        result = await db_session.execute(
            select(SessionShare).where(SessionShare.id == share.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_get_session_shares(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session,
        db_session: AsyncSession
    ):
        """获取会话的所有分享"""
        share = SessionShare(
            session_id=test_session.id,
            user_id=test_session.user_id,
            share_token="test_list_share",
            is_public=True,
        )
        db_session.add(share)
        await db_session.commit()

        response = await client.get(
            f"/api/session/{test_session.id}/shares",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


# =============================================================================
# 搜索功能测试
# =============================================================================

class TestSearchAPI:
    """搜索功能测试"""

    @pytest.mark.asyncio
    async def test_search_by_session_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_session: Session
    ):
        """按会话 ID 搜索"""
        response = await client.get(
            f"/api/user/{test_session.user_id}/sessions",
            params={"search": str(test_session.id)},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # 响应可能是列表或包含 items 的对象
        if isinstance(data, list):
            assert len(data) == 1
            assert data[0]["id"] == test_session.id
        else:
            assert len(data.get("items", [])) == 1
            assert data["items"][0]["id"] == test_session.id

    @pytest.mark.asyncio
    async def test_search_invalid_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User
    ):
        """搜索无效的 ID"""
        response = await client.get(
            f"/api/user/{test_user.id}/sessions",
            params={"search": "invalid_id"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # 响应可能是列表或包含 items 的对象
        if isinstance(data, list):
            assert len(data) == 0
        else:
            assert len(data.get("items", [])) == 0
