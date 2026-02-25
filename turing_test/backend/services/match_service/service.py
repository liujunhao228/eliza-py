"""
匹配服务主模块

整合队列、算法和统计模块，提供统一服务接口。
"""

import asyncio
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

        定期尝试匹配用户，处理超时

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager

        start_time = datetime.now(timezone.utc)
        user_score = self.queue.get_user_info(user_id, {}).get("user_score", 100)

        try:
            while True:
                # 检查用户是否仍在队列中（如果已断开连接则退出）
                if not self.queue.is_user_waiting(user_id):
                    logger.info(f"用户 {user_id} 已离开队列，退出匹配任务")
                    return

                # 检查用户是否已断开连接（双重检查）
                if not manager.is_user_connected(user_id):
                    logger.info(f"用户 {user_id} 已断开连接，退出匹配任务")
                    # 从队列移除，避免资源泄漏
                    await self.remove_from_queue(user_id)
                    return

                # 检查是否超时
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= self.match_timeout:
                    logger.info(f"用户 {user_id} 匹配超时 ({self.match_timeout}秒)")

                    # 记录超时统计
                    self.statistics.timeout_matches += 1

                    # 超时后匹配 AI（可能是钓鱼机器人）
                    # 先检查用户是否仍在线
                    if manager.is_user_connected(user_id):
                        await self._assign_ai_with_honeypot(user_id, websocket_ref, user_score)
                    else:
                        logger.info(f"用户 {user_id} 已断开，跳过 AI 匹配")

                    # 从队列移除
                    await self.remove_from_queue(user_id)
                    return

                # 尝试寻找匹配
                opponent_id = self.algorithm.find_match(
                    user_id,
                    self.queue.waiting_queue,
                    self.user_match_history
                )

                if opponent_id:
                    logger.info(f"✅ 匹配成功：用户 {user_id} <-> 用户 {opponent_id}")

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
                        # 检查用户是否仍在线
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

                    return

                # 定期更新状态
                position = await self.queue.get_position(user_id)
                queue_size = self.queue.get_size()

                # 再次检查用户是否仍在线（避免在长时间等待后用户已断开）
                if not manager.is_user_connected(user_id):
                    logger.info(f"用户 {user_id} 已断开，退出匹配任务")
                    await self.remove_from_queue(user_id)
                    return

                await manager.send_personal_message(user_id, {
                    "type": "status",
                    "data": {
                        "in_queue": True,
                        "queue_size": queue_size,
                        "queue_position": position,
                        "estimated_wait_time": max(0, int(self.match_timeout - elapsed)),
                    }
                })

                # 等待一段时间再重试（使用较短的等待时间以便更快检测断开）
                # 将 2 秒分成 4 个 0.5 秒的检查间隔
                for _ in range(4):
                    if not manager.is_user_connected(user_id):
                        logger.info(f"用户 {user_id} 已断开连接，退出匹配任务")
                        await self.remove_from_queue(user_id)
                        return
                    await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info(f"用户 {user_id} 的匹配任务已取消")
            # 确保从队列移除
            await self.remove_from_queue(user_id)
            # 优雅地处理取消，不重新抛出
            return
        except Exception as e:
            logger.error(f"匹配用户 {user_id} 时出错：{e}", exc_info=True)
            # 确保从队列移除
            await self.remove_from_queue(user_id)
            if manager.is_user_connected(user_id):
                await manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "MATCH_ERROR",
                        "message": "匹配过程中出错",
                    }
                })

    async def _assign_ai_with_honeypot(
        self,
        user_id: int,
        websocket_ref: int,
        user_score: int
    ):
        """
        为用户分配 AI 对手（可能是钓鱼机器人）

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session

        # 判断是否为钓鱼机器人
        is_honeypot = self.algorithm.should_assign_honeypot(
            user_id, user_score, self.user_match_history
        )

        async with async_session_maker() as db:
            # 创建 AI 会话
            session = Session(
                user_id=user_id,
                opponent_type="honeypot" if is_honeypot else "ai",
                is_honeypot=is_honeypot,
                started_at=datetime.now(timezone.utc),
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

            match_type = "honeypot" if is_honeypot else "ai"
            logger.info(f"为用户 {user_id} 分配 {match_type} 对手，会话 ID: {session.id}")

            # 记录匹配历史
            user_info = self.queue.get_user_info(user_id)
            wait_time = datetime.now(timezone.utc).timestamp() - user_info["timestamp"]
            self._record_match(user_id, -1, match_type, wait_time)  # -1 表示 AI 对手

            # 计算 AI 响应延迟
            ai_delay = self.algorithm.calculate_typing_delay()

            # 发送匹配成功消息
            await manager.send_personal_message(user_id, {
                "type": "match_found",
                "data": {
                    "session_id": session.id,
                    "opponent_type": "honeypot" if is_honeypot else "ai",
                    "is_honeypot": is_honeypot,
                    "matched_at": datetime.utcnow().isoformat(),
                    "ai_delay": ai_delay,  # AI 响应延迟（秒）
                }
            })

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
