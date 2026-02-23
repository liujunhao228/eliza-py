#!/usr/bin/env python3
"""测试登录 API"""

import asyncio
import sys
sys.path.insert(0, "F:/eliza-py")

from turing_test.backend.database import init_db, get_db, async_session_maker
from turing_test.backend.models import User, UserStats
from sqlalchemy import select
from datetime import datetime

async def test_login():
    """测试登录逻辑"""
    print("正在初始化数据库...")
    await init_db()
    
    print("正在创建测试用户...")
    async with async_session_maker() as session:
        # 检查用户是否存在
        result = await session.execute(
            select(User).where(User.invite_code == "TEST123")
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            print("用户不存在，创建新用户...")
            username = f"用户 TEST"
            
            user = User(
                invite_code="TEST123",
                username=username,
                score=100,
                highest_score=100,
                lowest_score=100,
            )
            session.add(user)
            await session.flush()
            
            # 创建用户统计记录
            user_stats = UserStats(user_id=user.id)
            session.add(user_stats)
            
            await session.commit()
            await session.refresh(user)
            
            print(f"用户创建成功：id={user.id}, username={user.username}")
        else:
            print(f"用户已存在：id={user.id}, username={user.username}")
        
        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await session.commit()
        
        # 尝试创建 UserResponse
        from turing_test.backend.schemas import UserResponse
        try:
            response = UserResponse.model_validate(user)
            print(f"UserResponse 创建成功：{response}")
        except Exception as e:
            print(f"UserResponse 创建失败：{e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_login())
