"""
初始化领域模型数据库表

用法:
    python -m turing_test.backend.scripts.init_domain_db

或者直接导入:
    from turing_test.backend.scripts.init_domain_db import init_domain_tables
    await init_domain_tables()
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from turing_test.backend.database import engine, async_session_maker
from turing_test.backend.models.domain_models import (
    BotConfig,
    Match,
    Room,
    RoomParticipant,
    Message,
    UserSession,
    SessionScore,
    ScoreBreakdownItem,
)


async def init_domain_tables():
    """
    创建领域模型的所有表
    
    注意：这只创建新表，不影响现有表结构
    """
    print("正在创建领域模型表结构...")
    
    async with engine.begin() as conn:
        # 导入所有领域模型
        from turing_test.backend.models.domain_models import Base
        
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ 领域模型表创建完成:")
    print("   - bot_configs")
    print("   - matches")
    print("   - rooms")
    print("   - room_participants")
    print("   - messages")
    print("   - user_sessions")
    print("   - session_scores")
    print("   - score_breakdown_items")


async def verify_tables():
    """验证表是否创建成功"""
    print("\n正在验证表结构...")
    
    async with async_session_maker() as session:
        # 检查表是否存在
        result = await session.execute(
            text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name IN (
                    'bot_configs', 'matches', 'rooms', 
                    'room_participants', 'messages', 
                    'user_sessions', 'session_scores', 
                    'score_breakdown_items'
                )
                ORDER BY name
            """)
        )
        tables = result.scalars().all()
        
        if len(tables) == 8:
            print(f"✅ 所有 8 个表已创建：{', '.join(tables)}")
        else:
            print(f"⚠️  只创建了 {len(tables)} 个表：{', '.join(tables)}")
        
        return tables


async def main():
    """主函数"""
    try:
        await init_domain_tables()
        await verify_tables()
        print("\n✅ 数据库初始化完成!")
    except Exception as e:
        print(f"\n❌ 初始化失败：{e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
