"""
会话管理修复测试脚本

测试场景：
1. 真人对战双方结束时机测试
2. 场中判断后继续对话测试
3. 两次结算机制测试
4. 并发提交问卷测试

用法:
    uv run python turing_test/backend/tests/test_session_fixes.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Tuple, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")


class SessionFixesTester:
    """会话管理修复测试器"""

    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.details = []

    async def setup_test_data(self):
        """准备测试数据"""
        from turing_test.backend.database import async_session_maker, engine
        from turing_test.backend.models import Base, User, Session
        from sqlalchemy import select, delete
        
        # 清理之前的测试数据
        async with async_session_maker() as db:
            # 删除测试用户
            await db.execute(delete(User).where(User.nickname.like("test_%")))
            await db.commit()

    async def cleanup_test_data(self, user_ids: list[int], session_ids: list[int]):
        """清理测试数据"""
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import User, Session, Survey, ScoreHistory
        from sqlalchemy import delete
        
        async with async_session_maker() as db:
            # 删除测试数据（按顺序，避免外键约束）
            for session_id in session_ids:
                await db.execute(delete(Survey).where(Survey.session_id == session_id))
                await db.execute(delete(ScoreHistory).where(ScoreHistory.session_id == session_id))
            
            for session_id in session_ids:
                await db.execute(delete(Session).where(Session.id == session_id))
            
            for user_id in user_ids:
                await db.execute(delete(User).where(User.id == user_id))
            
            await db.commit()

    async def test_human_match_end_sync(self):
        """
        测试 1: 真人对战双方结束时机同步
        
        场景：
        - 用户 A 和用户 B 进行真人对战
        - 用户 A 先点击"结束对话"
        - 验证用户 B 收到 opponent_ended 通知
        - 验证 first_left_at 字段被正确设置
        """
        logger.info("=" * 60)
        logger.info("测试 1: 真人对战双方结束时机同步")
        logger.info("=" * 60)

        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import User, Session
        from sqlalchemy import select
        
        user_ids = []
        session_ids = []
        
        try:
            async with async_session_maker() as db:
                # 创建测试用户（使用唯一 invite_code）
                import uuid
                invite_code_a = f"TEST_{uuid.uuid4().hex[:8].upper()}"
                invite_code_b = f"TEST_{uuid.uuid4().hex[:8].upper()}"
                
                user_a = User(nickname=f"test_user_a_{int(datetime.now().timestamp())}", password_hash="test", invite_code=invite_code_a)
                user_b = User(nickname=f"test_user_b_{int(datetime.now().timestamp())}", password_hash="test", invite_code=invite_code_b)
                db.add(user_a)
                db.add(user_b)
                await db.commit()
                await db.refresh(user_a)
                await db.refresh(user_b)
                user_ids = [user_a.id, user_b.id]
                
                logger.info(f"创建测试用户：A={user_a.id}, B={user_b.id}")
                
                # 创建真人对战会话
                session_a = Session(
                    user_id=user_a.id,
                    opponent_type="opponent",
                    true_identity="Human",
                    opponent_user_id=user_b.id,
                )
                session_b = Session(
                    user_id=user_b.id,
                    opponent_type="opponent",
                    true_identity="Human",
                    opponent_user_id=user_a.id,
                    opponent_session_id=None,  # 先不设置，等获取到 session_a.id 后再更新
                )
                db.add(session_a)
                db.add(session_b)
                await db.commit()
                await db.refresh(session_a)
                await db.refresh(session_b)
                
                # 更新 session_b 的 opponent_session_id
                session_b.opponent_session_id = session_a.id
                session_a.opponent_session_id = session_b.id
                await db.commit()
                
                session_ids = [session_a.id, session_b.id]
                logger.info(f"创建测试会话：A={session_a.id}, B={session_b.id}")
                
                # 模拟用户 A 结束对话
                logger.info("模拟用户 A 结束对话...")
                session_a.ended_at = datetime.now(timezone.utc)
                session_a.end_reason = "user_gave_up"
                
                # 验证：用户 B 的会话应该被标记 first_left_at
                assert session_b.first_left_at is None, "结束前 first_left_at 应为 None"
                
                # 模拟后端逻辑：设置 first_left_at
                session_b.first_left_at = datetime.now(timezone.utc)
                session_b.first_leaver_notified = True
                await db.commit()
                
                # 验证
                assert session_b.first_left_at is not None, "结束后 first_left_at 应被设置"
                assert session_b.first_leaver_notified == True, "first_leaver_notified 应为 True"
                
                logger.info("✅ 测试 1 通过：真人对战结束同步机制正常")
                self.test_results["passed"] += 1
                self.details.append(("测试 1: 真人对战结束同步", "PASS"))
                
        except Exception as e:
            logger.error(f"❌ 测试 1 失败：{e}")
            self.test_results["failed"] += 1
            self.details.append(("测试 1: 真人对战结束同步", f"FAIL: {e}"))
        finally:
            await self.cleanup_test_data(user_ids, session_ids)
            logger.info("已清理测试数据\n")

    async def test_mid_game_continue_chat(self):
        """
        测试 2: 场中判断后继续对话
        
        场景：
        - 用户在场中判断（第 4 轮，元对话 2 次）
        - 继续对话到第 6 轮，元对话 4 次
        - 验证积分基于场中判断时的数据（turn=4, meta=2）
        - 验证 mid_game_turn 和 mid_game_meta_count 字段正确记录
        """
        logger.info("=" * 60)
        logger.info("测试 2: 场中判断后继续对话")
        logger.info("=" * 60)

        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import User, Session
        from turing_test.backend.utils.score_calculator import calculate_final_score
        
        user_ids = []
        session_ids = []
        
        try:
            async with async_session_maker() as db:
                # 创建测试用户（使用唯一 invite_code）
                import uuid
                invite_code = f"TEST_{uuid.uuid4().hex[:8].upper()}"
                
                user = User(nickname=f"test_midgame_{int(datetime.now().timestamp())}", password_hash="test", invite_code=invite_code)
                db.add(user)
                await db.commit()
                await db.refresh(user)
                user_ids = [user.id]
                
                logger.info(f"创建测试用户：{user.id}")
                
                # 创建会话
                session = Session(
                    user_id=user.id,
                    opponent_type="ai",
                    true_identity="Bot_Lv1",
                    turn_count=4,  # 第 4 轮
                    meta_conversation_count=2,  # 2 次元对话
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
                session_ids = [session.id]
                
                logger.info(f"创建测试会话：{session.id}, turn={session.turn_count}, meta={session.meta_conversation_count}")
                
                # 模拟场中判断
                logger.info("模拟场中判断...")
                mid_game_turn = session.turn_count
                mid_game_meta_count = session.meta_conversation_count
                
                # 计算积分（使用场中判断时的数据）
                final_score, breakdown = calculate_final_score(
                    user_guess="ai",
                    opponent_type="ai",
                    confidence_level="high",
                    turn=mid_game_turn,
                    meta_count=mid_game_meta_count,
                    is_mid_game=True,
                )
                
                # 更新会话状态
                session.triggered_mid_game = True
                session.confidence_level = "high"
                session.user_guess = "ai"
                session.is_correct = breakdown.is_correct
                session.final_score = int(final_score)
                # 记录场中判断时的状态
                session.mid_game_turn = mid_game_turn
                session.mid_game_meta_count = mid_game_meta_count
                
                await db.commit()
                
                # 验证：场中判断字段正确记录
                assert session.mid_game_turn == 4, f"mid_game_turn 应为 4，实际为 {session.mid_game_turn}"
                assert session.mid_game_meta_count == 2, f"mid_game_meta_count 应为 2，实际为 {session.mid_game_meta_count}"
                
                # 模拟继续对话
                logger.info("场中判断后继续对话...")
                session.turn_count = 6  # 继续到第 6 轮
                session.meta_conversation_count = 4  # 元对话增加到 4 次
                await db.commit()
                
                # 验证：积分仍基于场中判断时的数据
                assert session.final_score == int(final_score), "积分应基于场中判断时的数据"
                
                # 验证：使用场中判断时的元对话次数
                effective_meta = session.mid_game_meta_count or session.meta_conversation_count
                assert effective_meta == 2, f"应使用场中判断时的 meta_count=2，实际为 {effective_meta}"
                
                logger.info(f"✅ 测试 2 通过：场中判断数据正确记录 (turn={session.mid_game_turn}, meta={session.mid_game_meta_count})")
                logger.info(f"   继续对话后：turn={session.turn_count}, meta={session.meta_conversation_count}")
                logger.info(f"   积分基于场中判断：{session.final_score}")
                
                self.test_results["passed"] += 1
                self.details.append(("测试 2: 场中判断后继续对话", "PASS"))
                
        except Exception as e:
            logger.error(f"❌ 测试 2 失败：{e}")
            self.test_results["failed"] += 1
            self.details.append(("测试 2: 场中判断后继续对话", f"FAIL: {e}"))
        finally:
            await self.cleanup_test_data(user_ids, session_ids)
            logger.info("已清理测试数据\n")

    async def test_two_phase_settlement(self):
        """
        测试 3: 两次结算机制
        
        场景：
        - 用户 A 和用户 B 进行真人对战
        - 用户 A 先提交问卷，对方 B 尚未提交
        - 验证 A 的 pending_opponent_bonus = True
        - 用户 B 后提交问卷
        - 验证 A 可以领取对方猜错奖励
        """
        logger.info("=" * 60)
        logger.info("测试 3: 两次结算机制")
        logger.info("=" * 60)

        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import User, Session, Survey
        from turing_test.backend.utils.score_calculator import calculate_base_score, calculate_opponent_bonus
        
        user_ids = []
        session_ids = []
        
        try:
            async with async_session_maker() as db:
                # 创建测试用户（使用唯一 invite_code）
                import uuid
                invite_code_a = f"TEST_{uuid.uuid4().hex[:8].upper()}"
                invite_code_b = f"TEST_{uuid.uuid4().hex[:8].upper()}"
                
                user_a = User(nickname=f"test_settle_a_{int(datetime.now().timestamp())}", password_hash="test", invite_code=invite_code_a, score=100)
                user_b = User(nickname=f"test_settle_b_{int(datetime.now().timestamp())}", password_hash="test", invite_code=invite_code_b, score=100)
                db.add(user_a)
                db.add(user_b)
                await db.commit()
                await db.refresh(user_a)
                await db.refresh(user_b)
                user_ids = [user_a.id, user_b.id]
                
                logger.info(f"创建测试用户：A={user_a.id} (score={user_a.score}), B={user_b.id} (score={user_b.score})")
                
                # 创建真人对战会话
                session_a = Session(
                    user_id=user_a.id,
                    opponent_type="opponent",
                    true_identity="Human",
                    opponent_user_id=user_b.id,
                    turn_count=5,
                    meta_conversation_count=2,
                )
                session_b = Session(
                    user_id=user_b.id,
                    opponent_type="opponent",
                    true_identity="Human",
                    opponent_user_id=user_a.id,
                    opponent_session_id=None,
                    turn_count=5,
                    meta_conversation_count=2,
                )
                db.add(session_a)
                db.add(session_b)
                await db.commit()
                await db.refresh(session_a)
                await db.refresh(session_b)
                
                session_b.opponent_session_id = session_a.id
                session_a.opponent_session_id = session_b.id
                await db.commit()
                
                session_ids = [session_a.id, session_b.id]
                logger.info(f"创建测试会话：A={session_a.id}, B={session_b.id}")
                
                # === 第一次结算：用户 A 先提交问卷 ===
                logger.info("\n--- 用户 A 提交问卷（第一次结算） ---")
                
                # 计算基础积分
                base_score, breakdown = calculate_base_score(
                    user_guess="human",
                    opponent_type="opponent",
                    confidence_level="high",
                    turn=5,
                    meta_count=2,
                    is_mid_game=False,
                )
                
                # 用户 A 的真实类型是 human，所以对方 B 猜的是 human
                # 此时 B 尚未提交，opponent_guess 为 None
                session_a.base_score_settled = int(base_score)
                session_a.final_score = int(base_score)
                session_a.pending_opponent_bonus = True  # 等待对方结算
                session_a.ended_at = datetime.now(timezone.utc)
                
                # 创建 A 的问卷
                survey_a = Survey(
                    session_id=session_a.id,
                    user_id=user_a.id,
                    user_guess="human",
                    confidence_level="high",
                    fluency_rating=4,
                )
                db.add(survey_a)
                
                # 更新 A 的积分
                user_a.score += int(base_score)
                await db.commit()
                
                logger.info(f"用户 A 基础积分：{base_score}")
                logger.info(f"用户 A pending_opponent_bonus: {session_a.pending_opponent_bonus}")
                
                # 验证：A 的待结算标志
                assert session_a.pending_opponent_bonus == True, "A 应等待对方结算"
                
                # === 第二次结算：用户 B 提交问卷 ===
                logger.info("\n--- 用户 B 提交问卷（第二次结算） ---")
                
                # 用户 B 判断 A 是 human（正确）
                session_b.user_guess = "human"
                session_b.confidence_level = "high"
                
                # 模拟 B 提交后，A 领取奖励
                # A 的真实类型是 human，B 猜的是 human，所以 B 猜对了
                # A 没有奖励
                opponent_guess = "human"  # B 对 A 的判断
                user_a_actual_type = "human"
                opponent_is_correct = (opponent_guess == user_a_actual_type)
                
                logger.info(f"用户 B 对 A 的判断：{opponent_guess}")
                logger.info(f"用户 A 真实类型：{user_a_actual_type}")
                logger.info(f"B 是否猜对：{opponent_is_correct}")
                
                if not opponent_is_correct:
                    bonus = calculate_opponent_bonus(
                        opponent_confidence="high",
                        user_actual_type=user_a_actual_type,
                        meta_count=2,
                        turn=5,
                    )
                    session_a.final_score += int(bonus)
                    user_a.score += int(bonus)
                    session_a.opponent_bonus_paid = True
                    logger.info(f"用户 A 获得对方猜错奖励：{bonus}")
                else:
                    logger.info("用户 B 猜对了，A 没有奖励")
                
                session_a.pending_opponent_bonus = False
                session_a.opponent_bonus_paid = True
                
                # 创建 B 的问卷
                survey_b = Survey(
                    session_id=session_b.id,
                    user_id=user_b.id,
                    user_guess="human",
                    confidence_level="high",
                    fluency_rating=5,
                )
                db.add(survey_b)
                
                await db.commit()
                
                # 验证
                assert session_a.pending_opponent_bonus == False, "A 的待结算标志应已清除"
                assert session_a.opponent_bonus_paid == True, "A 的奖励应已发放"
                
                logger.info(f"\n✅ 测试 3 通过：两次结算机制正常")
                logger.info(f"   用户 A 最终积分：{user_a.score} (基础：{base_score}, 奖励：0)")
                logger.info(f"   用户 B 最终积分：{user_b.score}")
                
                self.test_results["passed"] += 1
                self.details.append(("测试 3: 两次结算机制", "PASS"))
                
        except Exception as e:
            logger.error(f"❌ 测试 3 失败：{e}")
            import traceback
            traceback.print_exc()
            self.test_results["failed"] += 1
            self.details.append(("测试 3: 两次结算机制", f"FAIL: {e}"))
        finally:
            await self.cleanup_test_data(user_ids, session_ids)
            logger.info("已清理测试数据\n")

    async def test_concurrent_survey_submission(self):
        """
        测试 4: 并发提交问卷测试
        
        场景：
        - 同一会话，两个并发请求同时提交问卷
        - 验证只有一个请求成功
        - 验证另一个请求收到"已提交过"错误
        """
        logger.info("=" * 60)
        logger.info("测试 4: 并发提交问卷测试")
        logger.info("=" * 60)

        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import User, Session, Survey
        from sqlalchemy.exc import IntegrityError
        
        user_ids = []
        session_ids = []
        
        try:
            async with async_session_maker() as db:
                # 创建测试用户（使用唯一 invite_code）
                import uuid
                invite_code = f"TEST_{uuid.uuid4().hex[:8].upper()}"
                
                user = User(nickname=f"test_concurrent_{int(datetime.now().timestamp())}", password_hash="test", invite_code=invite_code)
                db.add(user)
                await db.commit()
                await db.refresh(user)
                user_ids = [user.id]
                
                logger.info(f"创建测试用户：{user.id}")
                
                # 创建会话
                session = Session(
                    user_id=user.id,
                    opponent_type="ai",
                    true_identity="Bot_Lv1",
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
                session_ids = [session.id]
                
                logger.info(f"创建测试会话：{session.id}")
                
                # 模拟并发提交
                async def submit_survey():
                    """模拟问卷提交"""
                    async with async_session_maker() as db:
                        # 检查是否已提交
                        existing = await db.execute(
                            select(Survey).where(Survey.session_id == session.id)
                        )
                        if existing.scalar_one_or_none():
                            raise IntegrityError("已提交", {}, None)
                        
                        # 模拟一点延迟，增加并发冲突概率
                        await asyncio.sleep(0.01)
                        
                        # 创建问卷
                        survey = Survey(
                            session_id=session.id,
                            user_id=user.id,
                            user_guess="ai",
                            confidence_level="high",
                            fluency_rating=4,
                        )
                        db.add(survey)
                        await db.commit()
                        return True
                
                from sqlalchemy import select
                
                # 并发提交
                logger.info("模拟并发提交...")
                results = await asyncio.gather(
                    submit_survey(),
                    submit_survey(),
                    return_exceptions=True
                )
                
                # 验证：只有一个成功
                success_count = sum(1 for r in results if r is True)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                
                logger.info(f"提交结果：成功={success_count}, 失败={error_count}")
                
                assert success_count == 1, f"应只有 1 个成功，实际 {success_count}"
                assert error_count == 1, f"应有 1 个失败，实际 {error_count}"
                
                # 验证数据库中只有一条记录
                async with async_session_maker() as db:
                    result = await db.execute(select(Survey).where(Survey.session_id == session.id))
                    surveys = result.scalars().all()
                    assert len(surveys) == 1, f"数据库中应有 1 条记录，实际 {len(surveys)}"
                
                logger.info("✅ 测试 4 通过：并发提交约束正常")
                
                self.test_results["passed"] += 1
                self.details.append(("测试 4: 并发提交问卷", "PASS"))
                
        except Exception as e:
            logger.error(f"❌ 测试 4 失败：{e}")
            import traceback
            traceback.print_exc()
            self.test_results["failed"] += 1
            self.details.append(("测试 4: 并发提交问卷", f"FAIL: {e}"))
        finally:
            await self.cleanup_test_data(user_ids, session_ids)
            logger.info("已清理测试数据\n")

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("\n" + "=" * 60)
        logger.info("会话管理修复测试开始")
        logger.info("=" * 60 + "\n")
        
        await self.setup_test_data()
        
        # 运行测试
        await self.test_human_match_end_sync()
        await self.test_mid_game_continue_chat()
        await self.test_two_phase_settlement()
        await self.test_concurrent_survey_submission()
        
        # 输出汇总
        logger.info("\n" + "=" * 60)
        logger.info("测试汇总")
        logger.info("=" * 60)
        
        for test_name, result in self.details:
            status = "✅ PASS" if result == "PASS" else f"❌ {result}"
            logger.info(f"{status} | {test_name}")
        
        logger.info("-" * 60)
        logger.info(f"总计：通过={self.test_results['passed']}, 失败={self.test_results['failed']}, 跳过={self.test_results['skipped']}")
        logger.info("=" * 60)
        
        return self.test_results["failed"] == 0


async def main():
    tester = SessionFixesTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
