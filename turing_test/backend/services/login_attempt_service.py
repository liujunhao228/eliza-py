"""
登录尝试跟踪服务

用于防止暴力破解攻击，跟踪登录失败次数并实施账户锁定。

配置说明:
    - 最大失败次数：5 次
    - 锁定时长：15 分钟
    - 存储方式：内存（开发环境）/ Redis（生产环境）
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from loguru import logger


# =============================================================================
# 配置
# =============================================================================

@dataclass
class LoginAttemptConfig:
    """登录尝试配置"""
    max_attempts: int = 5           # 最大失败次数
    lockout_duration_minutes: int = 15  # 锁定时长（分钟）


# 全局配置实例
config = LoginAttemptConfig()


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class LoginAttemptTracker:
    """登录尝试跟踪器"""
    nickname: str
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    locked_until: Optional[datetime] = None

    def is_locked(self) -> bool:
        """检查账户是否被锁定"""
        if self.locked_until is None:
            return False
        if datetime.now(timezone.utc) < self.locked_until:
            return True
        # 锁定期已过，重置
        self.reset()
        return False

    def add_attempt(self) -> None:
        """记录一次失败尝试"""
        self.attempts += 1
        self.last_attempt_at = datetime.now(timezone.utc)

        if self.attempts >= config.max_attempts:
            self.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=config.lockout_duration_minutes
            )
            logger.warning(
                f"🔒 账户已锁定：{self.nickname}, "
                f"锁定至 {self.locked_until.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def reset(self) -> None:
        """重置跟踪器（登录成功或锁定期过后）"""
        self.attempts = 0
        self.last_attempt_at = None
        self.locked_until = None

    def get_lockout_remaining_seconds(self) -> int:
        """获取剩余锁定时间（秒）"""
        if self.locked_until is None:
            return 0
        remaining = (self.locked_until - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))


# =============================================================================
# 内存存储（开发环境）
# =============================================================================

class MemoryLoginAttemptStore:
    """内存存储登录尝试记录"""

    def __init__(self):
        self._trackers: Dict[str, LoginAttemptTracker] = {}
        self._lock = asyncio.Lock()

    async def get_tracker(self, nickname: str) -> Optional[LoginAttemptTracker]:
        """获取跟踪器"""
        async with self._lock:
            tracker = self._trackers.get(nickname)
            if tracker and tracker.is_locked():
                return tracker
            return tracker

    async def create_tracker(self, nickname: str) -> LoginAttemptTracker:
        """创建跟踪器"""
        async with self._lock:
            tracker = LoginAttemptTracker(nickname=nickname)
            self._trackers[nickname] = tracker
            return tracker

    async def record_failed_attempt(self, nickname: str) -> LoginAttemptTracker:
        """记录失败尝试"""
        async with self._lock:
            if nickname not in self._trackers:
                self._trackers[nickname] = LoginAttemptTracker(nickname=nickname)

            tracker = self._trackers[nickname]
            tracker.add_attempt()
            return tracker

    async def reset_tracker(self, nickname: str) -> None:
        """重置跟踪器（登录成功）"""
        async with self._lock:
            if nickname in self._trackers:
                self._trackers[nickname].reset()

    async def cleanup_expired(self) -> None:
        """清理过期的跟踪记录"""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = []

            for nickname, tracker in self._trackers.items():
                # 如果锁定期已过且没有新尝试，标记为清理
                if (tracker.locked_until and
                        now > tracker.locked_until and
                        tracker.last_attempt_at and
                        now - tracker.last_attempt_at > timedelta(minutes=30)):
                    expired_keys.append(nickname)

            for key in expired_keys:
                del self._trackers[key]


# 全局内存存储实例
_memory_store = MemoryLoginAttemptStore()


# =============================================================================
# 服务接口
# =============================================================================

class LoginAttemptService:
    """登录尝试服务"""

    def __init__(self, store: MemoryLoginAttemptStore = _memory_store):
        self.store = store

    async def check_lockout(self, nickname: str) -> tuple[bool, int]:
        """
        检查账户是否被锁定

        Returns:
            (是否锁定，剩余锁定时间秒数)
        """
        tracker = await self.store.get_tracker(nickname)
        if tracker is None:
            return False, 0

        if tracker.is_locked():
            return True, tracker.get_lockout_remaining_seconds()

        return False, 0

    async def record_failed_login(self, nickname: str) -> tuple[int, bool]:
        """
        记录失败登录

        Returns:
            (失败次数，是否已锁定)
        """
        tracker = await self.store.record_failed_attempt(nickname)
        return tracker.attempts, tracker.is_locked()

    async def record_successful_login(self, nickname: str) -> None:
        """记录成功登录（重置跟踪器）"""
        await self.store.reset_tracker(nickname)

    async def get_remaining_attempts(self, nickname: str) -> int:
        """获取剩余尝试次数"""
        tracker = await self.store.get_tracker(nickname)
        if tracker is None:
            return config.max_attempts
        return max(0, config.max_attempts - tracker.attempts)


# =============================================================================
# 依赖注入
# =============================================================================

_login_attempt_service: Optional[LoginAttemptService] = None


def get_login_attempt_service() -> LoginAttemptService:
    """获取登录尝试服务实例"""
    global _login_attempt_service
    if _login_attempt_service is None:
        _login_attempt_service = LoginAttemptService()
    return _login_attempt_service


# =============================================================================
# 后台任务
# =============================================================================

async def cleanup_expired_trackers(interval_minutes: int = 30) -> None:
    """
    后台任务：定期清理过期的跟踪记录

    Args:
        interval_minutes: 清理间隔（分钟）
    """
    while True:
        await asyncio.sleep(interval_minutes * 60)
        await _memory_store.cleanup_expired()
        logger.debug("已清理过期的登录尝试记录")
