"""
匹配队列模块

负责管理匹配队列的加入/离开、排序和位置查询。
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from loguru import logger

from .statistics import MatchStatistics

if TYPE_CHECKING:
    from turing_test.backend.websocket.manager import ConnectionManager


class MatchPriority(Enum):
    """匹配优先级"""
    NORMAL = "normal"  # 普通用户
    RETURNING = "returning"  # 回流用户（积分较低）
    VIP = "vip"  # 高积分用户


class MatchQueue:
    """
    匹配队列管理

    负责：
    1. 用户加入/离开队列
    2. 队列排序（按优先级和加入时间）
    3. 位置查询
    4. 队列状态广播
    """

    def __init__(self, statistics: MatchStatistics):
        # 等待队列：user_id -> {timestamp, websocket_ref, priority, user_score}
        self.waiting_queue: Dict[int, dict] = {}
        # 用户会话映射：user_id -> websocket
        self.user_sessions: Dict[int, int] = {}  # user_id -> websocket_ref
        # 队列锁
        self._lock = asyncio.Lock()
        # 统计数据
        self.statistics = statistics

    def _calculate_priority(self, user_score: int) -> MatchPriority:
        """
        计算用户匹配优先级

        Args:
            user_score: 用户积分

        Returns:
            优先级枚举
        """
        # 积分低于 50 分为回流用户，优先匹配
        if user_score < 50:
            return MatchPriority.RETURNING
        # 积分高于 200 分为 VIP 用户，优先匹配
        elif user_score > 200:
            return MatchPriority.VIP
        else:
            return MatchPriority.NORMAL

    async def add(self, user_id: int, websocket_ref: int, user_score: int = 100) -> bool:
        """
        将用户加入队列

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
            user_score: 用户积分（用于优先级计算）

        Returns:
            是否成功加入队列
        """
        async with self._lock:
            if user_id in self.waiting_queue:
                logger.warning(f"用户 {user_id} 已在匹配队列中")
                return False

            # 计算匹配优先级
            priority = self._calculate_priority(user_score)

            # 记录加入时间
            join_time = datetime.now(timezone.utc).timestamp()
            self.waiting_queue[user_id] = {
                "timestamp": join_time,
                "websocket_ref": websocket_ref,
                "priority": priority,
                "user_score": user_score,
            }
            self.user_sessions[user_id] = websocket_ref

            logger.info(f"用户 {user_id} 加入匹配队列 (优先级：{priority.value}, 队列大小：{len(self.waiting_queue)})")

            # 广播队列状态
            await self.broadcast_status()

            return True

    async def remove(self, user_id: int) -> bool:
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

            # 计算等待时间
            wait_time = datetime.now(timezone.utc).timestamp() - self.waiting_queue[user_id]["timestamp"]

            del self.waiting_queue[user_id]
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

            logger.info(f"用户 {user_id} 离开匹配队列 (等待时间：{wait_time:.1f}秒，队列大小：{len(self.waiting_queue)})")

            # 广播队列状态
            await self.broadcast_status()

            return True

    def get_sorted_users(self, exclude_id: Optional[int] = None) -> List[Tuple[int, dict]]:
        """
        获取排序后的用户列表

        排序规则：
        1. 优先级顺序：RETURNING > VIP > NORMAL
        2. 同优先级时，先加入的在前

        Args:
            exclude_id: 要排除的用户 ID

        Returns:
            排序后的用户列表 [(user_id, data), ...]
        """
        priority_order = {
            MatchPriority.RETURNING: 0,
            MatchPriority.VIP: 1,
            MatchPriority.NORMAL: 2,
        }

        sorted_users = sorted(
            [
                (uid, data)
                for uid, data in self.waiting_queue.items()
                if uid != exclude_id
            ],
            key=lambda x: (
                priority_order[x[1]["priority"]],  # 优先级高的在前
                x[1]["timestamp"],  # 同优先级时，先加入的在前
            )
        )

        return sorted_users

    async def get_position(self, user_id: int) -> Optional[int]:
        """
        获取用户在队列中的位置

        Args:
            user_id: 用户 ID

        Returns:
            队列位置（从 1 开始），如果不在队列中则返回 None
        """
        if user_id not in self.waiting_queue:
            return None

        sorted_users = sorted(
            self.waiting_queue.keys(),
            key=lambda uid: self.waiting_queue[uid]["timestamp"]
        )

        try:
            return sorted_users.index(user_id) + 1
        except ValueError:
            return None

    def get_size(self) -> int:
        """获取队列大小"""
        return len(self.waiting_queue)

    def is_user_waiting(self, user_id: int) -> bool:
        """检查用户是否在等待队列中"""
        return user_id in self.waiting_queue

    def get_user_info(self, user_id: int) -> Optional[dict]:
        """获取用户队列信息"""
        return self.waiting_queue.get(user_id)

    async def broadcast_status(self):
        """广播队列状态给所有等待用户"""
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager

        queue_size = self.get_size()

        status_message = {
            "type": "queue_status",
            "data": {
                "waiting_count": queue_size,
                "estimated_wait_time": queue_size * 5,  # 估计每人 5 秒
            }
        }

        # 广播给所有等待用户
        for user_id in list(self.waiting_queue.keys()):
            await manager.send_personal_message(user_id, status_message)
