"""
对话应用服务 - Room Application Service

负责：
1. 创建对话空间
2. 管理参与者
3. 消息发送
4. 对话结束处理
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from loguru import logger

from turing_test.backend.domain.services import (
    RoomAggregate,
)
from turing_test.backend.domain.models import (
    RoomId, MatchId, UserId, MessageId,
    RoomType, RoomStatus, ParticipantRole,
    ParticipantInfo,
)
from turing_test.backend.domain.repositories import (
    AbstractUnitOfWork,
    RoomRepository,
    MatchRepository,
)
from turing_test.backend.infrastructure.events.event_bus import Event, EventType
from turing_test.backend.models.domain_models import Message as MessageORM


class RoomApplicationService:
    """
    对话应用服务
    
    用例：
    1. 创建对话 - 由匹配成功后创建
    2. 添加参与者 - 用户或 Bot 加入对话
    3. 发送消息 - 在对话中发送消息
    4. 结束对话 - 正常结束或超时
    """
    
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        event_bus: Optional[Any] = None,
    ):
        self._uow = uow
        self._event_bus = event_bus
    
    async def create_room(
        self,
        match_id: Optional[str] = None,
        room_type: RoomType = RoomType.HUMAN_VS_BOT,
    ) -> RoomAggregate:
        """
        创建对话空间
        
        Args:
            match_id: 关联的匹配 ID（可选）
            room_type: 对话类型
            
        Returns:
            创建的对话聚合根
        """
        # 创建 Room 聚合根
        room = RoomAggregate.create(
            match_id=MatchId(match_id) if match_id else None,
            room_type=room_type,
        )
        
        # 保存到数据库
        await self._uow.rooms.add(room)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.SESSION_CREATED,
                    aggregate_id=str(room.id),
                    aggregate_type="Room",
                    data={
                        "match_id": match_id,
                        "room_type": room_type.value,
                    },
                )
            )
        
        logger.info(f"创建对话空间：room_id={room.id}, type={room_type.value}")
        return room
    
    async def add_participant(
        self,
        room_id: str,
        user_id: Optional[int],
        role: ParticipantRole,
        bot_config_id: Optional[int] = None,
        bot_level: Optional[str] = None,
        is_honeypot: bool = False,
    ) -> bool:
        """
        添加参与者到对话
        
        Args:
            room_id: 对话 ID
            user_id: 用户 ID（Bot 为 None）
            role: 参与者角色
            bot_config_id: Bot 配置 ID
            bot_level: Bot 等级
            is_honeypot: 是否钓鱼 Bot
            
        Returns:
            是否添加成功
        """
        room = await self._uow.rooms.get(RoomId(room_id))
        if not room:
            logger.warning(f"对话不存在：room_id={room_id}")
            return False
        
        # 添加参与者
        room.add_participant(
            user_id=UserId(user_id) if user_id else None,
            role=role,
            bot_config_id=bot_config_id,
            bot_level=bot_level,
            is_honeypot=is_honeypot,
        )
        
        await self._uow.rooms.update(room)
        await self._uow.commit()
        
        logger.info(
            f"添加参与者到对话：room_id={room_id}, "
            f"user_id={user_id}, role={role.value}"
        )
        return True
    
    async def send_message(
        self,
        room_id: str,
        sender_id: Optional[int],
        sender_type: str,
        content: str,
        is_meta: bool = False,
        meta_keyword: Optional[str] = None,
    ) -> Optional[MessageORM]:
        """
        发送消息到对话
        
        Args:
            room_id: 对话 ID
            sender_id: 发送者 ID（Bot 为 None）
            sender_type: 发送者类型 (user/bot)
            content: 消息内容
            is_meta: 是否元对话
            meta_keyword: 元对话关键词
            
        Returns:
            创建的消息 ORM 对象
        """
        room = await self._uow.rooms.get(RoomId(room_id))
        if not room:
            logger.warning(f"对话不存在：room_id={room_id}")
            return None
        
        if room.status != RoomStatus.ACTIVE:
            logger.warning(f"对话已结束：room_id={room_id}, status={room.status}")
            return None
        
        # 创建消息 ORM 对象
        message = MessageORM(
            room_id=int(room_id),
            sender_id=sender_id,
            sender_type=sender_type,
            content=content,
            is_meta=is_meta,
            meta_keyword=meta_keyword,
        )
        self._uow._session.add(message)
        
        # 更新对话统计
        room.add_message(
            sender_id=UserId(sender_id) if sender_id else None,
            sender_type=sender_type,
            content=content,
            is_meta=is_meta,
            meta_keyword=meta_keyword,
        )
        
        await self._uow.rooms.update(room)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.SESSION_MESSAGE_SENT,
                    aggregate_id=room_id,
                    aggregate_type="Room",
                    data={
                        "message_id": message.id,
                        "sender_id": sender_id,
                        "sender_type": sender_type,
                        "is_meta": is_meta,
                    },
                )
            )
        
        return message
    
    async def end_room(
        self,
        room_id: str,
        end_reason: str,
        first_leaver_id: Optional[int] = None,
    ) -> bool:
        """
        结束对话
        
        Args:
            room_id: 对话 ID
            end_reason: 结束原因
            first_leaver_id: 先离开者 ID（真人对战）
            
        Returns:
            是否成功
        """
        room = await self._uow.rooms.get(RoomId(room_id))
        if not room:
            logger.warning(f"对话不存在：room_id={room_id}")
            return False
        
        # 结束对话
        room.end(
            end_reason=end_reason,
            first_leaver_id=UserId(first_leaver_id) if first_leaver_id else None,
        )
        
        await self._uow.rooms.update(room)
        await self._uow.commit()
        
        # 发布事件
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    event_type=EventType.SESSION_ENDED,
                    aggregate_id=room_id,
                    aggregate_type="Room",
                    data={
                        "end_reason": end_reason,
                        "first_leaver_id": first_leaver_id,
                    },
                )
            )
        
        logger.info(f"对话已结束：room_id={room_id}, reason={end_reason}")
        return True
    
    async def get_room(self, room_id: str) -> Optional[RoomAggregate]:
        """获取对话详情"""
        return await self._uow.rooms.get(RoomId(room_id))
    
    async def get_active_rooms(self, limit: int = 20) -> List[RoomAggregate]:
        """获取活跃对话"""
        return await self._uow.rooms.get_active(limit)


def create_room_application_service(
    uow: AbstractUnitOfWork,
    event_bus: Optional[Any] = None,
) -> RoomApplicationService:
    """创建对话应用服务实例"""
    return RoomApplicationService(uow, event_bus)
