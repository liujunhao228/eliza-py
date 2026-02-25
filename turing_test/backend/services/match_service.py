"""
匹配服务

管理真人匹配队列，实现匹配算法和超时处理。
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from loguru import logger
from enum import Enum

if TYPE_CHECKING:
    from turing_test.backend.websocket.manager import ConnectionManager

from config import settings


class MatchPriority(Enum):
    """匹配优先级"""
    NORMAL = "normal"  # 普通用户
    RETURNING = "returning"  # 回流用户（积分较低）
    VIP = "vip"  # 高积分用户


class MatchStatistics:
    """匹配统计数据"""
    
    def __init__(self):
        self.total_matches = 0  # 总匹配次数
        self.human_matches = 0  # 真人匹配次数
        self.ai_matches = 0  # AI 匹配次数
        self.honeypot_matches = 0  # 钓鱼机器人匹配次数
        self.timeout_matches = 0  # 超时匹配次数
        
        # 等待时间统计（秒）
        self.wait_times: List[float] = []
        
        # 按时间段统计
        self.matches_by_hour: Dict[int, int] = {i: 0 for i in range(24)}
        
    def record_match(self, wait_time: float, match_type: str):
        """记录一次匹配"""
        self.total_matches += 1
        self.wait_times.append(wait_time)
        
        if match_type == "human":
            self.human_matches += 1
        elif match_type == "ai":
            self.ai_matches += 1
        elif match_type == "honeypot":
            self.honeypot_matches += 1
            
        # 按小时统计
        hour = datetime.now().hour
        self.matches_by_hour[hour] += 1
        
    def get_avg_wait_time(self) -> float:
        """获取平均等待时间"""
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times) / len(self.wait_times)
    
    def get_success_rate(self) -> float:
        """获取真人匹配成功率"""
        if self.total_matches == 0:
            return 0.0
        return self.human_matches / self.total_matches
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_matches": self.total_matches,
            "human_matches": self.human_matches,
            "ai_matches": self.ai_matches,
            "honeypot_matches": self.honeypot_matches,
            "timeout_matches": self.timeout_matches,
            "human_success_rate": f"{self.get_success_rate():.2%}",
            "avg_wait_time": f"{self.get_avg_wait_time():.1f}秒",
            "current_queue_size": len(self.wait_times) - len([t for t in self.wait_times if t > 0]),
        }


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
        # 等待队列：user_id -> {timestamp, websocket_ref, priority, user_score}
        self.waiting_queue: Dict[int, dict] = {}

        # 用户会话映射：user_id -> websocket
        self.user_sessions: Dict[int, int] = {}  # user_id -> websocket_ref

        # 匹配任务：user_id -> asyncio.Task
        self.match_tasks: Dict[int, asyncio.Task] = {}

        # 匹配超时时间（秒）
        self.match_timeout = settings.turing.match.timeout

        # 队列锁
        self._lock = asyncio.Lock()
        
        # 匹配统计
        self.statistics = MatchStatistics()
        
        # 用户匹配历史（用于防作弊）
        self.user_match_history: Dict[int, List[dict]] = {}
        
        # AI 响应时间分布配置
        self.ai_time_distribution = settings.turing.match.time_distribution
        self.honeypot_probability = settings.turing.match.honeypot_probability
        self.honeypot_high_meta_probability = settings.turing.match.honeypot_high_meta_probability

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
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager
        
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
            await self.broadcast_queue_status()

            return True
    
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

    async def remove_from_queue(self, user_id: int) -> bool:
        """
        将用户从匹配队列中移除

        Args:
            user_id: 用户 ID

        Returns:
            是否成功移除
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager
        
        async with self._lock:
            if user_id not in self.waiting_queue:
                return False

            # 计算等待时间
            wait_time = datetime.now(timezone.utc).timestamp() - self.waiting_queue[user_id]["timestamp"]

            del self.waiting_queue[user_id]
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

            # 取消匹配任务
            if user_id in self.match_tasks:
                self.match_tasks[user_id].cancel()
                del self.match_tasks[user_id]

            logger.info(f"用户 {user_id} 离开匹配队列 (等待时间：{wait_time:.1f}秒，队列大小：{len(self.waiting_queue)})")

            # 广播队列状态
            await self.broadcast_queue_status()

            return True

    async def find_match(self, user_id: int) -> Optional[int]:
        """
        寻找匹配的对手

        使用优先级 + FIFO 算法：
        1. 同优先级内按 FIFO 顺序匹配
        2. 不同优先级时，高优先级用户优先匹配
        3. 排除自己

        Args:
            user_id: 当前用户 ID

        Returns:
            匹配的用户 ID，如果没有匹配则返回 None
        """
        if user_id not in self.waiting_queue:
            return None

        if len(self.waiting_queue) < 2:
            return None

        user_priority = self.waiting_queue[user_id]["priority"]
        user_join_time = self.waiting_queue[user_id]["timestamp"]
        
        # 按优先级和加入时间排序
        # 优先级顺序：RETURNING > VIP > NORMAL
        priority_order = {
            MatchPriority.RETURNING: 0,
            MatchPriority.VIP: 1,
            MatchPriority.NORMAL: 2,
        }
        
        sorted_users = sorted(
            [
                (uid, data) 
                for uid, data in self.waiting_queue.items() 
                if uid != user_id
            ],
            key=lambda x: (
                priority_order[x[1]["priority"]],  # 优先级高的在前
                x[1]["timestamp"],  # 同优先级时，先加入的在前
            )
        )

        # 找到第一个匹配的用户
        for candidate_id, candidate_data in sorted_users:
            if candidate_id in self.waiting_queue:
                # 检查是否为重复匹配（防作弊）
                if self._is_repeat_match(user_id, candidate_id):
                    logger.info(f"跳过重复匹配：用户 {user_id} 和 {candidate_id}")
                    continue
                return candidate_id

        return None
    
    def _is_repeat_match(self, user_id: int, candidate_id: int) -> bool:
        """
        检查两个用户是否为重复匹配（防作弊）
        
        Args:
            user_id: 用户 ID
            candidate_id: 候选用户 ID
            
        Returns:
            是否为重复匹配
        """
        # 获取用户匹配历史
        user_history = self.user_match_history.get(user_id, [])
        
        # 检查最近 5 次匹配
        recent_matches = user_history[-5:]
        
        for match in recent_matches:
            if match.get("opponent_id") == candidate_id:
                return True
        
        return False
    
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

    async def start_match_task(self, user_id: int, websocket_ref: int):
        """
        启动匹配任务

        Args:
            user_id: 用户 ID
            websocket_ref: WebSocket 引用 ID
        """
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
        user_score = self.waiting_queue.get(user_id, {}).get("user_score", 100)

        try:
            while True:
                # 检查用户是否仍在队列中（如果已断开连接则退出）
                if user_id not in self.waiting_queue:
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
                opponent_id = await self.find_match(user_id)

                if opponent_id:
                    logger.info(f"✅ 匹配成功：用户 {user_id} <-> 用户 {opponent_id}")

                    # 计算等待时间
                    wait_time = datetime.now(timezone.utc).timestamp() - self.waiting_queue[user_id]["timestamp"]

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
                position = await self.get_queue_position(user_id)
                queue_size = self.get_queue_size()

                # 再次检查用户是否仍在线（避免在长时间等待后用户已断开）
                if not manager.is_user_connected(user_id):
                    logger.info(f"用户 {user_id} 已断开连接，退出匹配任务")
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
        is_honeypot = await self._should_assign_honeypot(user_id, user_score)
        
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
            wait_time = datetime.now(timezone.utc).timestamp() - self.waiting_queue[user_id]["timestamp"]
            self._record_match(user_id, -1, match_type, wait_time)  # -1 表示 AI 对手
            
            # 计算 AI 响应延迟
            ai_delay = self._calculate_ai_typing_delay()
            
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
    
    async def _should_assign_honeypot(self, user_id: int, user_score: int) -> bool:
        """
        判断是否应该分配钓鱼机器人
        
        Args:
            user_id: 用户 ID
            user_score: 用户积分
            
        Returns:
            是否分配钓鱼机器人
        """
        # 基础概率
        base_probability = self.honeypot_probability
        
        # 获取用户元对话历史
        user_history = self.user_match_history.get(user_id, [])
        
        # 检查用户最近是否频繁使用元对话（识别 AI 的关键词）
        recent_meta_count = 0
        for match in user_history[-5:]:
            if match.get("meta_count", 0) > 3:
                recent_meta_count += 1
        
        # 如果用户频繁使用元对话，提高钓鱼机器人概率
        if recent_meta_count >= 3:
            return random.random() < self.honeypot_high_meta_probability
        
        # 检查用户积分
        if user_score < 50:
            # 低积分用户（回流用户）降低钓鱼机器人概率
            return random.random() < (base_probability * 0.5)
        elif user_score > 200:
            # 高积分用户（VIP）提高钓鱼机器人概率
            return random.random() < (base_probability * 1.5)
        
        # 普通概率
        return random.random() < base_probability
    
    def _calculate_ai_typing_delay(self) -> float:
        """
        计算 AI 打字延迟，模拟人类打字行为
        
        Returns:
            延迟时间（秒）
        """
        # 根据配置的时间分布随机选择
        rand = random.random()
        
        cumulative = 0.0
        for period_name, period_config in self.ai_time_distribution.items():
            cumulative += period_config["probability"]
            if rand <= cumulative:
                # 在此时间段内随机选择
                delay = random.uniform(
                    period_config["min"],
                    period_config["max"]
                )
                return delay
        
        # 默认返回正常时间段
        normal_config = self.ai_time_distribution["normal"]
        return random.uniform(normal_config["min"], normal_config["max"])

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

    async def get_queue_position(self, user_id: int) -> Optional[int]:
        """
        获取用户在队列中的位置

        Args:
            user_id: 用户 ID

        Returns:
            队列位置（从 1 开始），如果不在队列中则返回 None
        """
        if user_id not in self.waiting_queue:
            return None

        # 按加入时间排序
        sorted_users = sorted(
            self.waiting_queue.keys(),
            key=lambda uid: self.waiting_queue[uid]["timestamp"]
        )

        try:
            return sorted_users.index(user_id) + 1
        except ValueError:
            return None

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self.waiting_queue)

    def is_user_waiting(self, user_id: int) -> bool:
        """检查用户是否在等待队列中"""
        return user_id in self.waiting_queue

    async def broadcast_queue_status(self):
        """
        广播队列状态给所有等待用户
        """
        # 延迟导入 manager 以避免循环导入
        from turing_test.backend.websocket.manager import manager
        
        queue_size = self.get_queue_size()

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
            "connected_users": len(self.user_sessions),
            "match_statistics": self.statistics.get_stats(),
        }


# 全局匹配服务实例
match_service = MatchService()


def get_match_service() -> MatchService:
    """获取匹配服务实例"""
    return match_service
