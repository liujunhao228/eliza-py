"""
匹配服务（简化版）

极简匹配逻辑：
1. 用户加入队列后，20% 概率直接分配 AI（对照组）
2. 80% 概率尝试匹配真人（FIFO）
3. 无真人时暂存队列，等待下一位用户
4. 匹配结果暂存，前端固定等待 3 秒后主动请求
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, Optional

from loguru import logger

from config import settings


class MatchService:
    """
    简化匹配服务
    
    核心逻辑：
    - 20% 对照组：直接分配 AI
    - 80% 真人匹配：FIFO 匹配
    - 结果暂存：前端主动拉取
    """

    def __init__(self):
        # 等待队列：user_id -> {timestamp, websocket_ref, user_score}
        self.waiting_queue: Dict[int, dict] = {}
        # 匹配结果暂存：user_id -> result
        self.match_results: Dict[int, dict] = {}
        # 队列锁
        self._lock = asyncio.Lock()
        # 固定等待时间（秒）
        self.fixed_wait_time = settings.turing.match.fixed_wait_time
        # AI 对照组比例
        self.ai_control_rate = settings.turing.match.ai_control_group_rate
        # 钓鱼机器人概率
        self.honeypot_probability = settings.turing.match.honeypot_probability

    async def add_to_queue(self, user_id: int, websocket_ref: int, user_score: int = 100) -> bool:
        """
        将用户加入匹配队列并立即尝试匹配

        匹配逻辑：
        1. 20% 概率直接分配 AI（对照组）
        2. 80% 概率尝试匹配真人（FIFO）
        3. 无真人等待时，加入队列等待

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分

        Returns:
            是否成功加入队列
        """
        async with self._lock:
            if user_id in self.waiting_queue:
                logger.warning(f"用户 {user_id} 已在匹配队列中")
                return False

            # 20% 概率直接分配 AI（对照组）
            if random.random() < self.ai_control_rate:
                logger.info(f"用户 {user_id} 被分配到 AI 对照组")
                await self._assign_ai(user_id, websocket_ref, user_score)
                return True

            # 80% 概率尝试匹配真人
            opponent_id = self._find_opponent(user_id)

            if opponent_id:
                # 匹配到真人
                await self._create_human_match(user_id, opponent_id, websocket_ref)
            else:
                # 无真人等待，加入队列
                self.waiting_queue[user_id] = {
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "websocket_ref": websocket_ref,
                    "user_score": user_score,
                }
                logger.info(f"用户 {user_id} 加入等待队列 (队列大小：{len(self.waiting_queue)})")

            return True

    async def remove_from_queue(self, user_id: int) -> bool:
        """
        将用户从队列中移除
        
        Args:
            user_id: 用户 ID
            
        Returns:
            是否成功移除
        """
        async with self._lock:
            if user_id not in self.waiting_queue:
                return False
            
            del self.waiting_queue[user_id]
            logger.info(f"用户 {user_id} 离开等待队列")
            return True

    async def get_result(self, user_id: int) -> Optional[dict]:
        """
        获取暂存的匹配结果
        
        Args:
            user_id: 用户 ID
            
        Returns:
            匹配结果，如果不存在则返回 None
        """
        return self.match_results.get(user_id)

    async def clear_result(self, user_id: int):
        """清除暂存的匹配结果"""
        if user_id in self.match_results:
            del self.match_results[user_id]

    def _find_opponent(self, user_id: int) -> Optional[int]:
        """
        寻找匹配对手（FIFO）
        
        Args:
            user_id: 当前用户 ID
            
        Returns:
            对手用户 ID，如果没有则返回 None
        """
        if not self.waiting_queue:
            return None
        
        # 获取最早加入的用户（FIFO）
        earliest_user = min(self.waiting_queue.keys(), key=lambda uid: self.waiting_queue[uid]["timestamp"])
        
        # 排除自己
        if earliest_user == user_id:
            return None
        
        return earliest_user

    async def _create_human_match(self, user_id: int, opponent_id: int, websocket_ref: int):
        """
        创建真人匹配
        
        Args:
            user_id: 用户 ID
            opponent_id: 对手用户 ID
            websocket_ref: WebSocket 引用 ID
        """
        from turing_test.backend.websocket.manager import manager
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session

        # 从队列中移除对手
        async with self._lock:
            if opponent_id in self.waiting_queue:
                del self.waiting_queue[opponent_id]

        async with async_session_maker() as db:
            # 创建会话
            session = Session(
                user_id=user_id,
                opponent_type="human",
                is_honeypot=False,
                started_at=datetime.now(timezone.utc),
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        # 暂存结果
        result = {
            "session_id": session.id,
            "opponent_type": "human",
            "is_honeypot": False,
            "matched_at": datetime.now(timezone.utc).isoformat(),
        }
        self.match_results[user_id] = result
        
        # 同时暂存对手的结果
        self.match_results[opponent_id] = result

        logger.info(f"✅ 真人匹配成功：用户 {user_id} <-> 用户 {opponent_id}, 会话 ID: {session.id}")

    async def _assign_ai(self, user_id: int, websocket_ref: int, user_score: int):
        """
        分配 AI 对手
        
        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分
        """
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session

        # 判断是否为钓鱼机器人
        is_honeypot = random.random() < self.honeypot_probability

        async with async_session_maker() as db:
            session = Session(
                user_id=user_id,
                opponent_type="honeypot" if is_honeypot else "ai",
                is_honeypot=is_honeypot,
                started_at=datetime.now(timezone.utc),
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        # 暂存结果
        self.match_results[user_id] = {
            "session_id": session.id,
            "opponent_type": "honeypot" if is_honeypot else "ai",
            "is_honeypot": is_honeypot,
            "matched_at": datetime.now(timezone.utc).isoformat(),
        }

        # 异步发送开场白
        asyncio.create_task(self._send_opening_message(session.id, user_id, is_honeypot))

        logger.info(f"为用户 {user_id} 分配 {'钓鱼机器人' if is_honeypot else 'AI'}对手，会话 ID: {session.id}")

    async def _send_opening_message(self, session_id: int, user_id: int, is_honeypot: bool):
        """延迟发送开场白"""
        from turing_test.backend.services.session_state import session_state_manager
        from turing_test.backend.services.message_service import MessageService
        from config import get_config_manager
        from turing_test.backend.database import async_session_maker

        config_mgr = get_config_manager()
        opening_cfg = config_mgr.get('turing.ai_bot.opening', {})

        if is_honeypot:
            honeypot_cfg = opening_cfg.get('honeypot', {})
            probability = honeypot_cfg.get('probability', 0.5)
            delay_min = honeypot_cfg.get('delay_min', 5.0)
            delay_max = honeypot_cfg.get('delay_max', 15.0)
        else:
            probability = opening_cfg.get('probability', 0.7)
            delay_min = opening_cfg.get('delay_min', 2.0)
            delay_max = opening_cfg.get('delay_max', 5.0)

        if not opening_cfg.get('enabled', True):
            probability = 0.0

        # 等待随机延迟
        await asyncio.sleep(random.uniform(delay_min, delay_max))

        async with async_session_maker() as db:
            # 检查是否已有消息（用户先发言）
            state = session_state_manager.get(session_id)
            if state and state.turn_count > 0:
                logger.info(f"用户已先发言，跳过开场白：session_id={session_id}")
                return

            # 概率检测
            if random.random() >= probability:
                logger.info(f"跳过开场白（概率检测未通过）：session_id={session_id}")
                return

            # 发送开场白
            await MessageService.send_opening_message(
                session_id=session_id,
                user_id=user_id,
                db=db,
            )

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self.waiting_queue)

    def is_user_waiting(self, user_id: int) -> bool:
        """检查用户是否在等待队列中"""
        return user_id in self.waiting_queue

    def get_statistics(self) -> dict:
        """获取匹配服务统计信息"""
        return {
            "waiting_count": self.get_queue_size(),
            "active_match_tasks": 0,  # 简化后无任务
            "connected_users": 0,  # 简化后不追踪
            "match_statistics": {
                "total_matches": 0,
                "human_matches": 0,
                "ai_matches": 0,
                "honeypot_matches": 0,
            },
        }


# 全局匹配服务实例
match_service = MatchService()


def get_match_service() -> MatchService:
    """获取匹配服务实例"""
    return match_service
