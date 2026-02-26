"""
会话状态管理器（内存级，无数据库依赖）

设计原则：
1. 状态读写纯内存操作（零延迟）
2. 会话锁防止并发
3. 数据库仅用于消息持久化（异步）
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from loguru import logger


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


class SessionStateManager:
    """
    会话状态管理器
    
    功能：
    1. 内存中维护会话状态（turn_count, is_user_turn 等）
    2. 会话锁防止并发处理消息
    3. 异步持久化到数据库
    """
    
    def __init__(self):
        self._states: Dict[int, SessionState] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
    
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
        self._states.pop(session_id, None)
        self._locks.pop(session_id, None)
        logger.info(f"[SessionState] 清理：session_id={session_id}")


# 全局实例
session_state_manager = SessionStateManager()
