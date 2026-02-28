"""
会话状态管理器（内存级，无数据库依赖）

设计原则：
1. 状态读写纯内存操作（零延迟）
2. 会话锁防止并发
3. 数据库仅用于消息持久化（异步）
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from loguru import logger
from sqlalchemy import select


@dataclass
class SessionState:
    """会话运行时状态（纯内存）"""
    session_id: int
    user_id: int
    turn_count: int = 0
    is_user_turn: bool = True
    meta_count: int = 0
    is_processing: bool = False
    is_honeypot: bool = False
    opponent_type: str = "ai"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # 对方猜错奖励字段
    opponent_guess: Optional[str] = None  # AI 对用户的判断 ('human' | 'ai')
    opponent_confidence: Optional[str] = None  # AI 判断的信心等级 ('low' | 'mid' | 'high')
    opponent_guess_confidence_score: float = 0.5  # AI 判断的置信度 (0-1)


class SessionStateManager:
    """
    会话状态管理器

    功能：
    1. 内存中维护会话状态（turn_count, is_user_turn 等）
    2. 会话锁防止并发处理消息
    3. 异步持久化到数据库
    4. 追踪开场白任务以便取消
    5. 定期清理超时会话
    """

    # 会话超时配置（秒）
    SESSION_TIMEOUT_SECONDS = 300  # 5 分钟无活动视为超时

    def __init__(self):
        self._states: Dict[int, SessionState] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
        self._opening_tasks: Dict[int, asyncio.Task] = {}  # 追踪待处理的开场白任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """启动后台清理任务"""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("[SessionState] 后台清理任务已启动")

    async def stop(self) -> None:
        """停止后台清理任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("[SessionState] 后台清理任务已停止")

    async def _cleanup_loop(self) -> None:
        """定期清理超时会话"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_timeout_sessions()
            except asyncio.CancelledError:
                logger.info("[SessionState] 清理任务已取消")
                break
            except Exception as e:
                logger.error(f"[SessionState] 清理任务出错：{e}", exc_info=True)

    async def _cleanup_timeout_sessions(self) -> None:
        """清理超时的会话"""
        now = datetime.now(timezone.utc)
        timeout_threshold = now - timedelta(seconds=self.SESSION_TIMEOUT_SECONDS)
        timeout_sessions: list[int] = []

        # 找出超时的会话
        for session_id, state in list(self._states.items()):
            if state.last_active < timeout_threshold:
                timeout_sessions.append(session_id)

        # 处理超时会话
        for session_id in timeout_sessions:
            try:
                await self._mark_session_timeout(session_id)
            except Exception as e:
                logger.error(f"清理超时会话失败：session_id={session_id}, error={e}")

    async def _mark_session_timeout(self, session_id: int) -> None:
        """标记会话为超时结束"""
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session

        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()

                if session and session.ended_at is None:
                    session.ended_at = datetime.now(timezone.utc)
                    session.end_reason = "sys_timeout"
                    await db.commit()
                    logger.info(
                        f"会话超时结束：session_id={session_id}, "
                        f"user_id={session.user_id}"
                    )
        except Exception as e:
            logger.error(f"标记会话超时失败：session_id={session_id}, error={e}")

        # 清理内存状态
        self.cleanup(session_id)
    
    async def create(
        self, 
        session_id: int, 
        user_id: int,
        is_honeypot: bool = False, 
        opponent_type: str = "ai"
    ) -> SessionState:
        """创建会话状态"""
        if session_id in self._states:
            return self._states[session_id]
        
        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            is_honeypot=is_honeypot,
            opponent_type=opponent_type,
        )
        self._states[session_id] = state
        self._locks[session_id] = asyncio.Lock()
        
        logger.info(f"[SessionState] 创建：session_id={session_id}")
        return state
    
    def get(self, session_id: int) -> Optional[SessionState]:
        """获取状态（无锁）"""
        return self._states.get(session_id)
    
    async def acquire(self, session_id: int, timeout: float = 10.0) -> bool:
        """获取会话锁"""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        
        try:
            acquired = await asyncio.wait_for(
                self._locks[session_id].acquire(),
                timeout=timeout
            )
            if acquired:
                state = self._states.get(session_id)
                if state:
                    state.is_processing = True
            return acquired
        except asyncio.TimeoutError:
            logger.warning(f"[SessionState] 获取锁超时：session_id={session_id}")
            return False
    
    def release(self, session_id: int):
        """释放会话锁"""
        state = self._states.get(session_id)
        if state:
            state.is_processing = False
            state.last_active = datetime.now(timezone.utc)
        
        if session_id in self._locks:
            lock = self._locks[session_id]
            if lock.locked():
                lock.release()
    
    def next_turn(self, session_id: int) -> tuple[int, bool]:
        """
        切换到下一回合
        
        Returns:
            (新的 turn_count, 是否为用户回合)
        """
        state = self._states.get(session_id)
        if not state:
            return 0, True
        
        state.turn_count += 1
        state.is_user_turn = not state.is_user_turn
        
        return state.turn_count, state.is_user_turn
    
    def is_user_turn(self, session_id: int) -> bool:
        """检查是否为用户回合"""
        state = self._states.get(session_id)
        return state.is_user_turn if state else True
    
    def cleanup(self, session_id: int):
        """清理会话状态（会话结束时调用）"""
        # 取消待处理的开场白任务
        self.cancel_opening_task(session_id, reason="会话结束")

        self._states.pop(session_id, None)
        self._locks.pop(session_id, None)
        logger.info(f"[SessionState] 清理：session_id={session_id}")

    def register_opening_task(self, session_id: int, task: asyncio.Task):
        """注册开场白任务"""
        self._opening_tasks[session_id] = task
        logger.debug(f"[SessionState] 注册开场白任务：session_id={session_id}")

    def cancel_opening_task(self, session_id: int, reason: str = "用户先发言") -> bool:
        """
        取消开场白任务

        Args:
            session_id: 会话 ID
            reason: 取消原因（"用户先发言" 或 "任务完成"）

        Returns:
            是否成功取消
        """
        if session_id in self._opening_tasks:
            task = self._opening_tasks[session_id]
            if not task.done():
                task.cancel()
            self._opening_tasks.pop(session_id, None)
            logger.info(f"[SessionState] 取消开场白任务（{reason}）：session_id={session_id}")
            return True
        return False


# 全局实例
session_state_manager = SessionStateManager()
