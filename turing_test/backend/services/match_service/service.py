"""
匹配服务主模块

整合队列、算法和统计模块，提供统一服务接口。
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

from loguru import logger

from config import settings

from .queue import MatchQueue, MatchPriority
from .algorithm import MatchAlgorithm
from .statistics import MatchStatistics

if TYPE_CHECKING:
    from turing_test.backend.websocket.manager import ConnectionManager


class MatchService:
    """
    匹配服务

    管理真人匹配队列，实现以下功能：
    1. 用户加入/离开匹配队列
    2. 真人匹配算法（FIFO 公平匹配 + 优先级）
    3. 匹配超时处理
    4. AI 备选匹配（含钓鱼机器人）
    5. 队列状态广播
    6. 匹配统计监控
    """

    def __init__(self):
        # 统计数据
        self.statistics = MatchStatistics()
        # 队列管理
        self.queue = MatchQueue(self.statistics)
        # 匹配算法
        self.algorithm = MatchAlgorithm()

        # 用户匹配任务：user_id -> asyncio.Task
        self.match_tasks: Dict[int, asyncio.Task] = {}

        # 匹配超时时间（秒）
        self.match_timeout = settings.turing.match.timeout

        # 用户匹配历史（用于防作弊）
        self.user_match_history: Dict[int, List[dict]] = {}

    async def add_to_queue(self, user_id: int, websocket_ref: int, user_score: int = 100) -> bool:
        """
        将用户加入匹配队列

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分（用于优先级计算）

        Returns:
            是否成功加入队列
        """
        return await self.queue.add(user_id, websocket_ref, user_score)

    async def remove_from_queue(self, user_id: int) -> bool:
        """
        将用户从匹配队列中移除

        Args:
            user_id: 用户 ID

        Returns:
            是否成功移除
        """
        # 取消匹配任务
        if user_id in self.match_tasks:
            self.match_tasks[user_id].cancel()
            del self.match_tasks[user_id]

        return await self.queue.remove(user_id)

    async def start_match_task(self, user_id: int, websocket_ref: int):
        """
        启动匹配任务

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager

        # 取消已有的匹配任务
        if user_id in self.match_tasks:
            self.match_tasks[user_id].cancel()

        # 创建新的匹配任务
        task = asyncio.create_task(self._match_loop(user_id, websocket_ref))
        self.match_tasks[user_id] = task
        logger.info(f"启动用户 {user_id} 的匹配任务")

    async def _match_loop(self, user_id: int, websocket_ref: int):
        """
        匹配循环

        实现文档：前端文档/03-技术架构/匹配机制设计.md

        流程：
        1. 生成匹配延迟（统一分布）
        2. 等待延迟，期间检查是否有真人加入
        3. 延迟结束后：
           - 有真人 → 80% 概率匹配真人 - 真人，20% 概率匹配 AI（实验对照）
           - 无真人 → 继续等待或超时后匹配 AI

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager

        start_time = datetime.now(timezone.utc)
        user_score = self.queue.get_user_info(user_id, {}).get("user_score", 100)

        # 生成匹配延迟（真人/AI 使用相同分布，消除时间线索）
        match_delay = self.algorithm.generate_match_delay()
        logger.info(f"用户 {user_id} 开始匹配，生成延迟：{match_delay:.2f}秒")

        try:
            # 等待匹配延迟，期间定期检查是否有真人加入
            elapsed = 0.0
            check_interval = 0.5  # 每 0.5 秒检查一次

            while elapsed < match_delay:
                # 检查用户是否仍在队列中
                if not self.queue.is_user_waiting(user_id):
                    logger.info(f"用户 {user_id} 已离开队列，退出匹配任务")
                    return

                # 检查用户是否已断开连接
                if not manager.is_user_connected(user_id):
                    logger.info(f"用户 {user_id} 已断开连接，退出匹配任务")
                    await self.remove_from_queue(user_id)
                    return

                # 检查是否有真人加入（队列中超过 1 人）
                queue_size = self.queue.get_size()
                if queue_size >= 2:
                    logger.info(f"延迟期间有真人加入，当前队列大小：{queue_size}")

                    # 有真人等待时，直接匹配真人（不消耗 20% 实验对照机会）
                    # 实验对照只在用户超时后匹配 AI 时生效
                    opponent_id = self.algorithm.find_match(
                        user_id,
                        self.queue.waiting_queue,
                        self.user_match_history
                    )

                    if opponent_id:
                        await self._create_human_match(
                            user_id, opponent_id, websocket_ref, start_time
                        )
                        return

                # 等待检查间隔
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                # 更新状态
                position = await self.queue.get_position(user_id)
                estimated_wait = max(0, int(self.match_timeout - (datetime.now(timezone.utc) - start_time).total_seconds()))
                await manager.send_personal_message(user_id, {
                    "type": "status",
                    "data": {
                        "in_queue": True,
                        "queue_size": self.queue.get_size(),
                        "queue_position": position,
                        "estimated_wait_time": estimated_wait,
                    }
                })

            # 延迟结束后，检查是否超时
            total_elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if total_elapsed >= self.match_timeout:
                logger.info(f"用户 {user_id} 匹配超时 ({self.match_timeout}秒)")
                self.statistics.timeout_matches += 1

                if manager.is_user_connected(user_id):
                    await self._assign_ai_with_honeypot(user_id, websocket_ref, user_score)
                await self.remove_from_queue(user_id)
                return

            # 延迟结束，仍无真人，匹配 AI
            logger.info(f"用户 {user_id} 延迟结束，仍无真人，匹配 AI")
            await self.remove_from_queue(user_id)
            await self._assign_ai_with_honeypot(user_id, websocket_ref, user_score)

        except asyncio.CancelledError:
            logger.info(f"用户 {user_id} 的匹配任务已取消")
            await self.remove_from_queue(user_id)
            return
        except Exception as e:
            logger.error(f"匹配用户 {user_id} 时出错：{e}", exc_info=True)
            await self.remove_from_queue(user_id)
            if manager.is_user_connected(user_id):
                await manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "MATCH_ERROR",
                        "message": "匹配过程中出错",
                    }
                })

    async def _create_human_match(
        self,
        user_id: int,
        opponent_id: int,
        websocket_ref: int,
        start_time: datetime
    ):
        """
        创建真人匹配

        Args:
            user_id: 用户 ID
            opponent_id: 对手用户 ID
            websocket_ref: WebSocket 引用 ID
            start_time: 开始时间
        """
        from turing_test.backend.websocket.manager import manager

        # 计算等待时间
        user_info = self.queue.get_user_info(user_id)
        wait_time = datetime.now(timezone.utc).timestamp() - user_info["timestamp"]

        # 从队列中移除两个用户
        await self.remove_from_queue(user_id)
        await self.remove_from_queue(opponent_id)

        # 创建会话
        session_id = await self._create_session(user_id, opponent_id, "human")

        # 记录匹配历史
        self._record_match(user_id, opponent_id, "human", wait_time)
        self._record_match(opponent_id, user_id, "human", wait_time)

        # 发送匹配成功消息给两个用户
        for uid in [user_id, opponent_id]:
            if not manager.is_user_connected(uid):
                logger.warning(f"用户 {uid} 已断开连接，跳过发送匹配成功消息")
                continue
            success = await manager.send_personal_message(uid, {
                "type": "match_found",
                "data": {
                    "session_id": session_id,
                    "opponent_type": "human",
                    "is_honeypot": False,
                    "matched_at": datetime.now(timezone.utc).isoformat(),
                    "wait_time": wait_time,
                }
            })
            if not success:
                logger.warning(f"发送匹配成功消息给用户 {uid} 失败")

        logger.info(f"✅ 真人匹配成功：用户 {user_id} <-> 用户 {opponent_id}, 等待时间：{wait_time:.2f}秒")

    async def _assign_ai_with_honeypot(
        self,
        user_id: int,
        websocket_ref: int,
        user_score: int
    ):
        """
        为用户分配 AI 对手（支持概率开场白）

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        from turing_test.backend.services.session_state import session_state_manager
        from turing_test.backend.services.message_service import MessageService
        from config import get_config_manager

        # 判断是否为钓鱼机器人
        is_honeypot = self.algorithm.should_assign_honeypot(
            user_id, user_score, self.user_match_history
        )

        async with async_session_maker() as db:
            # 创建会话
            session = Session(
                user_id=user_id,
                opponent_type="honeypot" if is_honeypot else "ai",
                is_honeypot=is_honeypot,
                started_at=datetime.now(timezone.utc),
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

            # 创建内存状态
            await session_state_manager.create(
                session_id=session.id,
                user_id=user_id,
                is_honeypot=is_honeypot,
                opponent_type="honeypot" if is_honeypot else "ai",
            )
            
            # 获取开场白配置
            config_mgr = get_config_manager()
            opening_cfg = config_mgr.get('turing.ai_bot.opening', {})
            
            # 根据类型选择配置
            if is_honeypot:
                honeypot_cfg = opening_cfg.get('honeypot', {})
                probability = honeypot_cfg.get('probability', 0.5)
                delay_min = honeypot_cfg.get('delay_min', 5.0)
                delay_max = honeypot_cfg.get('delay_max', 15.0)
            else:
                probability = opening_cfg.get('probability', 0.7)
                delay_min = opening_cfg.get('delay_min', 2.0)
                delay_max = opening_cfg.get('delay_max', 5.0)
            
            # 检查是否启用开场白
            if not opening_cfg.get('enabled', True):
                probability = 0.0
            
            logger.info(
                f"开场白配置：session_id={session.id}, "
                f"is_honeypot={is_honeypot}, probability={probability}"
            )

            match_type = "honeypot" if is_honeypot else "ai"
            logger.info(f"为用户 {user_id} 分配 {match_type} 对手，会话 ID: {session.id}")

            # 记录匹配历史
            user_info = self.queue.get_user_info(user_id)
            wait_time = datetime.now(timezone.utc).timestamp() - user_info["timestamp"]
            self._record_match(user_id, -1, match_type, wait_time)  # -1 表示 AI 对手

            # 发送匹配成功消息
            await manager.send_personal_message(user_id, {
                "type": "match_found",
                "data": {
                    "session_id": session.id,
                    "opponent_type": "honeypot" if is_honeypot else "ai",
                    "is_honeypot": is_honeypot,
                    "matched_at": datetime.now(timezone.utc).isoformat(),
                }
            })
            
            # 延迟发送开场白（带概率检测）
            async def send_opening_with_delay():
                # 等待随机延迟
                await asyncio.sleep(random.uniform(delay_min, delay_max))
                
                # 检查是否已有消息（用户先发言）
                state = session_state_manager.get(session_id)
                if state and state.turn_count > 0:
                    logger.info(f"用户已先发言，跳过开场白：session_id={session_id}")
                    return
                
                # 概率检测
                if random.random() >= probability:
                    logger.info(
                        f"跳过开场白（概率检测未通过）：session_id={session_id}, "
                        f"probability={probability}"
                    )
                    return
                
                # 发送开场白
                await MessageService.send_opening_message(
                    session_id=session.id,
                    user_id=user_id,
                    db=db,
                )
            
            asyncio.create_task(send_opening_with_delay())

    async def _create_session(
        self,
        user_id: int,
        opponent_id: int,
        opponent_type: str
    ) -> int:
        """
        创建新会话

        Args:
            user_id: 用户 ID
            opponent_id: 对手用户 ID
            opponent_type: 对手类型

        Returns:
            会话 ID
        """
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session

        async with async_session_maker() as db:
            # 创建会话（注意：真人匹配需要特殊处理，这里简化为单用户会话）
            # 实际应用中可能需要创建共享会话
            session = Session(
                user_id=user_id,
                opponent_type=opponent_type,
                is_honeypot=False,
                started_at=datetime.now(timezone.utc),
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

            logger.info(f"创建会话 {session.id}: 用户 {user_id} vs {opponent_type}")

            return session.id

    def _record_match(self, user_id: int, opponent_id: int, match_type: str, wait_time: float):
        """
        记录匹配历史

        Args:
            user_id: 用户 ID
            opponent_id: 对手用户 ID
            match_type: 匹配类型
            wait_time: 等待时间
        """
        # 记录用户匹配历史
        if user_id not in self.user_match_history:
            self.user_match_history[user_id] = []

        self.user_match_history[user_id].append({
            "opponent_id": opponent_id,
            "match_type": match_type,
            "wait_time": wait_time,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        })

        # 限制历史记录长度
        if len(self.user_match_history[user_id]) > 20:
            self.user_match_history[user_id] = self.user_match_history[user_id][-20:]

        # 记录统计
        self.statistics.record_match(wait_time, match_type)

    async def get_queue_position(self, user_id: int) -> Optional[int]:
        """
        获取用户在队列中的位置

        Args:
            user_id: 用户 ID

        Returns:
            队列位置（从 1 开始），如果不在队列中则返回 None
        """
        return await self.queue.get_position(user_id)

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.queue.get_size()

    def is_user_waiting(self, user_id: int) -> bool:
        """检查用户是否在等待队列中"""
        return self.queue.is_user_waiting(user_id)

    async def assign_ai_bot(self, user_id: int, websocket_ref: int) -> Optional[int]:
        """
        为用户分配 AI 机器人

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID

        Returns:
            会话 ID，如果失败则返回 None
        """
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        from turing_test.backend.websocket.manager import manager

        async with async_session_maker() as db:
            # 创建 AI 会话
            session = Session(
                user_id=user_id,
                opponent_type="ai",
                is_honeypot=False,
                started_at=datetime.utcnow(),
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

            logger.info(f"为用户 {user_id} 分配 AI 对手，会话 ID: {session.id}")

            # 发送匹配成功消息
            await manager.send_personal_message(user_id, {
                "type": "match_found",
                "data": {
                    "session_id": session.id,
                    "opponent_type": "ai",
                    "is_honeypot": False,
                    "matched_at": datetime.now(timezone.utc).isoformat(),
                }
            })

            return session.id

    def get_statistics(self) -> dict:
        """
        获取匹配服务统计信息

        Returns:
            统计信息字典
        """
        return {
            "waiting_count": self.get_queue_size(),
            "active_match_tasks": len(self.match_tasks),
            "connected_users": len(self.queue.user_sessions),
            "match_statistics": self.statistics.get_stats(),
        }


# 全局匹配服务实例
match_service = MatchService()


def get_match_service() -> MatchService:
    """获取匹配服务实例"""
    return match_service
