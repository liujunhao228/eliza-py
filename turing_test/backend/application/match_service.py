"""
应用服务层 - 应用服务实现

应用服务负责：
1. 协调领域对象完成业务用例
2. 事务管理
3. 领域事件发布
4. 权限校验（可选）
"""

from datetime import datetime, timezone
from typing import Optional, List, Any
from loguru import logger

from turing_test.backend.domain.services import (
    MatchAggregate,
)
from turing_test.backend.domain.models import (
    MatchId, RoomId, SessionId, UserId,
    MatchStatus, OpponentType,
    MatchRequest,
)
from turing_test.backend.domain.repositories import (
    AbstractUnitOfWork,
    MatchRepository,
    RoomRepository,
    UserSessionRepository,
)
from turing_test.backend.infrastructure.events.event_bus import Event, EventType


class MatchApplicationService:
    """
    匹配应用服务
    
    用例：
    1. 请求匹配 - 用户发起匹配请求
    2. 取消匹配 - 用户取消待处理匹配
    3. 完成匹配 - 匹配成功，创建 Room
    4. 失败处理 - 匹配失败或超时
    """
    
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        event_bus: Optional[Any] = None,
    ):
        """
        初始化匹配服务
        
        Args:
            uow: 工作单元
            event_bus: 事件总线
        """
        self._uow = uow
        self._event_bus = event_bus
    
    async def request_match(
        self,
        user_id: int,
        user_score: int,
        preferences: Optional[dict] = None,
    ) -> MatchAggregate:
        """
        请求匹配
        
        流程：
        1. 检查用户是否有待处理匹配
        2. 创建新的 Match 聚合根
        3. 保存到数据库
        4. 发布 MatchRequested 事件
        
        Args:
            user_id: 用户 ID
            user_score: 用户当前积分（快照）
            preferences: 匹配偏好
            
        Returns:
            创建的匹配聚合根
        """
        # 检查是否有待处理匹配
        existing = await self._uow.matches.get_pending_by_user(UserId(user_id))
        if existing:
            logger.warning(f"用户 {user_id} 已有待处理匹配：{existing.id}")
            return existing
        
        # 创建匹配聚合根
        match = MatchAggregate.create(
            user_id=UserId(user_id),
            user_score_snapshot=user_score,
            preferences=preferences or {},
        )
        
        # 保存到数据库
        await self._uow.matches.add(match)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.MATCH_REQUESTED,
                    aggregate_id=str(match.id),
                    aggregate_type="Match",
                    data={
                        "user_id": user_id,
                        "user_score": user_score,
                        "preferences": preferences,
                    },
                )
            )
        
        logger.info(f"用户 {user_id} 请求匹配：match_id={match.id}")
        return match
    
    async def cancel_match(self, match_id: str) -> bool:
        """
        取消匹配
        
        Args:
            match_id: 匹配 ID
            
        Returns:
            是否取消成功
        """
        match = await self._uow.matches.get(MatchId(match_id))
        if not match:
            logger.warning(f"匹配不存在：match_id={match_id}")
            return False
        
        if match.status != MatchStatus.PENDING:
            logger.warning(f"匹配状态不允许取消：match_id={match_id}, status={match.status}")
            return False
        
        # 取消匹配
        match.cancel()
        await self._uow.matches.update(match)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.MATCH_CANCELLED,
                    aggregate_id=match_id,
                    aggregate_type="Match",
                    data={"reason": "user_cancelled"},
                )
            )
        
        logger.info(f"匹配已取消：match_id={match_id}")
        return True
    
    async def complete_match(
        self,
        match_id: str,
        room_id: str,
        opponent_type: OpponentType,
        matched_opponent_id: Optional[int] = None,
        bot_config_id: Optional[int] = None,
        bot_level: Optional[str] = None,
        is_honeypot: bool = False,
    ) -> bool:
        """
        完成匹配（匹配成功）
        
        Args:
            match_id: 匹配 ID
            room_id: 创建的 Room ID
            opponent_type: 对手类型
            matched_opponent_id: 真人对手 ID（如果是真人对战）
            bot_config_id: Bot 配置 ID（如果是 Bot 对战）
            bot_level: Bot 等级
            is_honeypot: 是否钓鱼 Bot
            
        Returns:
            是否成功
        """
        match = await self._uow.matches.get(MatchId(match_id))
        if not match:
            logger.warning(f"匹配不存在：match_id={match_id}")
            return False
        
        if match.status != MatchStatus.PENDING:
            logger.warning(f"匹配状态不允许完成：match_id={match_id}, status={match.status}")
            return False
        
        # 完成匹配
        match.complete(
            room_id=RoomId(room_id),
            opponent_type=opponent_type,
            matched_opponent_id=UserId(matched_opponent_id) if matched_opponent_id else None,
            bot_config_id=bot_config_id,
            bot_level=bot_level,
            is_honeypot=is_honeypot,
        )
        
        await self._uow.matches.update(match)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.MATCH_COMPLETED,
                    aggregate_id=match_id,
                    aggregate_type="Match",
                    data={
                        "room_id": room_id,
                        "opponent_type": opponent_type.value,
                        "matched_opponent_id": matched_opponent_id,
                        "bot_config_id": bot_config_id,
                    },
                )
            )
        
        logger.info(f"匹配已完成：match_id={match_id}, room_id={room_id}")
        return True
    
    async def fail_match(
        self,
        match_id: str,
        reason: str = "unknown",
    ) -> bool:
        """
        失败匹配
        
        Args:
            match_id: 匹配 ID
            reason: 失败原因
            
        Returns:
            是否成功
        """
        match = await self._uow.matches.get(MatchId(match_id))
        if not match:
            logger.warning(f"匹配不存在：match_id={match_id}")
            return False
        
        if match.status != MatchStatus.PENDING:
            logger.warning(f"匹配状态不允许失败：match_id={match_id}, status={match.status}")
            return False
        
        # 失败处理
        match.fail(reason=reason)
        await self._uow.matches.update(match)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.MATCH_FAILED,
                    aggregate_id=match_id,
                    aggregate_type="Match",
                    data={"reason": reason},
                )
            )
        
        logger.info(f"匹配已失败：match_id={match_id}, reason={reason}")
        return True
    
    async def get_match(self, match_id: str) -> Optional[MatchAggregate]:
        """获取匹配详情"""
        return await self._uow.matches.get(MatchId(match_id))
    
    async def get_user_matches(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[MatchAggregate]:
        """获取用户匹配历史"""
        return await self._uow.matches.get_by_user_id(UserId(user_id), limit)
    
    async def get_pending_match(self, user_id: int) -> Optional[MatchAggregate]:
        """获取用户待处理匹配"""
        return await self._uow.matches.get_pending_by_user(UserId(user_id))


# 工厂函数
def create_match_application_service(
    uow: AbstractUnitOfWork,
    event_bus: Optional[Any] = None,
) -> MatchApplicationService:
    """创建匹配应用服务实例"""
    return MatchApplicationService(uow, event_bus)
