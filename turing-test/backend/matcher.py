import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
from sqlalchemy.orm import Session
from models import Session as SessionModel, User
from config import MATCH_TIMEOUT


class MatchEngine:
    """匹配引擎 - 管理用户匹配队列"""

    def __init__(self):
        # 等待匹配的用户队列 (按等待时间排序)
        self.waiting_queue: list[int] = []  # 存储 user_id
        # 用户等待开始时间
        self.wait_start_time: Dict[int, datetime] = {}
        # 锁，防止并发问题
        self._lock = asyncio.Lock()
        # 后台超时检查任务
        self._timeout_task: Optional[asyncio.Task] = None
        # 已配对的会话记录 (session_id -> (user1_id, user2_id))
        self.active_sessions: Dict[int, tuple[int, Optional[int]]] = {}

    async def start_timeout_checker(self):
        """启动后台超时检查任务"""
        async def check_timeouts():
            while True:
                await asyncio.sleep(5)  # 每 5 秒检查一次
                async with self._lock:
                    now = datetime.utcnow()
                    timed_out_users = []
                    
                    for user_id, start_time in list(self.wait_start_time.items()):
                        wait_seconds = (now - start_time).total_seconds()
                        if wait_seconds > MATCH_TIMEOUT:
                            timed_out_users.append(user_id)
                    
                    # 处理超时用户，匹配 AI
                    for user_id in timed_out_users:
                        if user_id in self.waiting_queue:
                            self.waiting_queue.remove(user_id)
                        if user_id in self.wait_start_time:
                            del self.wait_start_time[user_id]
                        # 标记为需要自动匹配 AI（通过回调或状态标记）
                        # 这里通过 WebSocket 通知前端重新请求 AI 匹配
                        from websocket import manager
                        ws = manager.get_connection(user_id)
                        if ws:
                            try:
                                await ws.send_json({
                                    "type": "match_timeout",
                                    "message": "等待超时，正在为您匹配 AI 对手..."
                                })
                            except Exception:
                                pass

        self._timeout_task = asyncio.create_task(check_timeouts())

    async def stop_timeout_checker(self):
        """停止后台超时检查任务"""
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

    async def join_queue(self, user_id: int, db: Session) -> tuple[str, Optional[int], Optional[str]]:
        """
        用户加入匹配队列

        Returns:
            (状态，session_id, opponent_type)
            状态：'found_human' - 找到真人，'found_ai' - 匹配 AI，'waiting' - 继续等待
        """
        async with self._lock:
            now = datetime.utcnow()

            # 清理超时的等待用户
            await self._cleanup_timed_out_users(db)

            # 检查是否有其他人在等待（真人优先匹配）
            if self.waiting_queue:
                # 找到第一个等待的用户
                other_user_id = self.waiting_queue.pop(0)

                # 再次检查对方是否还在等待（双重确认）
                if other_user_id not in self.wait_start_time:
                    # 对方已经不在等待队列，当前用户加入队列
                    self.waiting_queue.append(user_id)
                    self.wait_start_time[user_id] = now
                    return ('waiting', None, None)

                # 创建真人 - 真人的会话
                session = SessionModel(
                    user_id=user_id,
                    opponent_type='human',
                    opponent_id=other_user_id,
                    status='active',
                    started_at=now
                )
                db.add(session)
                db.flush()  # 获取 session.id

                # 为对方创建会话记录
                other_session = SessionModel(
                    user_id=other_user_id,
                    opponent_type='human',
                    opponent_id=user_id,
                    status='active',
                    started_at=now
                )
                db.add(other_session)

                db.commit()

                # 清理等待时间记录
                if other_user_id in self.wait_start_time:
                    del self.wait_start_time[other_user_id]

                # 记录活跃会话
                self.active_sessions[session.id] = (user_id, other_user_id)

                return ('found_human', session.id, 'human')

            else:
                # 队列为空，当前用户加入等待
                self.waiting_queue.append(user_id)
                self.wait_start_time[user_id] = now

                return ('waiting', None, None)

    async def _cleanup_timed_out_users(self, db: Session):
        """清理超时的用户并自动匹配 AI"""
        now = datetime.utcnow()
        timed_out_users = []

        for user_id, start_time in list(self.wait_start_time.items()):
            wait_seconds = (now - start_time).total_seconds()
            if wait_seconds > MATCH_TIMEOUT:
                timed_out_users.append(user_id)

        for user_id in timed_out_users:
            # 从队列中移除
            if user_id in self.waiting_queue:
                self.waiting_queue.remove(user_id)
            if user_id in self.wait_start_time:
                del self.wait_start_time[user_id]

            # 自动创建 AI 会话
            session = SessionModel(
                user_id=user_id,
                opponent_type='ai',
                opponent_id=None,
                status='active',
                started_at=now
            )
            db.add(session)
            db.flush()
            db.commit()

            self.active_sessions[session.id] = (user_id, None)

            # 通知用户
            from websocket import manager
            ws = manager.get_connection(user_id)
            if ws:
                try:
                    await ws.send_json({
                        "type": "match_found",
                        "session_id": session.id,
                        "opponent_type": 'ai',
                        "message": "等待超时，已为您匹配 AI 对手"
                    })
                except Exception:
                    pass

    async def match_ai(self, user_id: int, db: Session) -> tuple[int, str]:
        """
        直接匹配 AI

        Returns:
            (session_id, opponent_type)
        """
        async with self._lock:
            now = datetime.utcnow()

            # 如果用户在等待队列中，移除
            if user_id in self.waiting_queue:
                self.waiting_queue.remove(user_id)
            if user_id in self.wait_start_time:
                del self.wait_start_time[user_id]

            # 创建 AI 会话
            session = SessionModel(
                user_id=user_id,
                opponent_type='ai',
                opponent_id=None,
                status='active',
                started_at=now
            )
            db.add(session)
            db.flush()
            db.commit()

            self.active_sessions[session.id] = (user_id, None)

            return session.id, 'ai'

    def leave_queue(self, user_id: int):
        """用户离开匹配队列"""
        if user_id in self.waiting_queue:
            self.waiting_queue.remove(user_id)
        if user_id in self.wait_start_time:
            del self.wait_start_time[user_id]

    def get_queue_status(self) -> dict:
        """获取队列状态"""
        now = datetime.utcnow()
        waiting_info = []
        for uid in self.waiting_queue:
            if uid in self.wait_start_time:
                wait_time = (now - self.wait_start_time[uid]).total_seconds()
                waiting_info.append({
                    "user_id": uid,
                    "wait_time": round(wait_time, 1)
                })

        return {
            "waiting_count": len(self.waiting_queue),
            "waiting_users": waiting_info,
            "active_sessions": len(self.active_sessions)
        }

    def get_user_wait_time(self, user_id: int) -> Optional[float]:
        """获取用户已等待的时间（秒）"""
        if user_id not in self.wait_start_time:
            return None
        now = datetime.utcnow()
        return (now - self.wait_start_time[user_id]).total_seconds()


# 全局匹配引擎实例
match_engine = MatchEngine()
