"""
消息处理服务 - 基于新领域模型

负责：
1. 用户消息处理（使用 Room/Message 模型）
2. AI 响应生成
3. 消息持久化
4. WebSocket 推送

新架构：
- 消息属于 Room，不属于 Session
- 使用领域服务处理业务逻辑
- 使用 Repository 持久化
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple
from loguru import logger

from turing_test.backend.application.room_service import RoomApplicationService
from turing_test.backend.application.session_service import SessionApplicationService
from turing_test.backend.domain.models import RoomId, SessionId, UserId, ParticipantRole
from turing_test.backend.domain.repositories import AbstractUnitOfWork
from turing_test.backend.models.domain_models import Message as MessageORM


class NewMessageService:
    """
    新消息处理服务（基于领域模型）
    
    用法：
        service = NewMessageService(room_service, session_service, uow, websocket_manager)
        await service.handle_user_message(room_id, user_id, content)
    """
    
    def __init__(
        self,
        room_service: RoomApplicationService,
        session_service: SessionApplicationService,
        uow: AbstractUnitOfWork,
        websocket_manager: any,
    ):
        self._room_service = room_service
        self._session_service = session_service
        self._uow = uow
        self._websocket_manager = websocket_manager
    
    async def handle_user_message(
        self,
        room_id: str,
        user_id: int,
        content: str,
    ) -> Optional[MessageORM]:
        """
        处理用户消息
        
        流程：
        1. 获取用户会话
        2. 检查是否为用户回合
        3. 发送消息到 Room
        4. 更新会话状态
        5. WebSocket 推送
        6. 触发 AI 响应（如果是 Bot 对战）
        
        Args:
            room_id: 对话 ID
            user_id: 用户 ID
            content: 消息内容
            
        Returns:
            创建的消息对象
        """
        try:
            # 获取用户会话
            session = await self._session_service.get_session_by_room_and_user(
                room_id=room_id,
                user_id=user_id,
            )
            
            if not session:
                logger.warning(f"用户会话不存在：room_id={room_id}, user_id={user_id}")
                return None
            
            # 检查是否为用户回合
            if not session.turn_state.is_user_turn:
                await self._websocket_manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "NOT_USER_TURN",
                        "message": "请等待对方发送消息",
                    }
                })
                return None
            
            # 验证内容
            if not content or not content.strip():
                await self._websocket_manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "EMPTY_MESSAGE",
                        "message": "消息不能为空",
                    }
                })
                return None
            
            # 检测元对话
            is_meta, keyword = self._detect_meta_conversation(content)
            
            # 发送消息到 Room
            message = await self._room_service.send_message(
                room_id=room_id,
                sender_id=user_id,
                sender_type="user",
                content=content.strip(),
                is_meta=is_meta,
                meta_keyword=keyword if is_meta else None,
            )
            
            if not message:
                return None
            
            # 更新会话回合状态
            await self._session_service.update_turn(
                session_id=str(session.id),
                is_user_turn=False,  # 用户发完消息后，轮到对方
                increment_turn=True,
            )
            
            # WebSocket 推送
            await self._websocket_manager.send_to_room(room_id, {
                "type": "chat",
                "data": {
                    "id": message.id,
                    "sender": "user",
                    "content": content.strip(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_meta": is_meta,
                }
            })
            
            # 触发 AI 响应（如果是 Bot 对战）
            room = await self._room_service.get_room(room_id)
            if room and room.type.value == "human_vs_bot":
                asyncio.create_task(
                    self._trigger_ai_response(room_id, content.strip())
                )
            
            return message
            
        except Exception as e:
            logger.error(f"处理用户消息失败：{e}", exc_info=True)
            return None
    
    async def send_bot_message(
        self,
        room_id: str,
        content: str,
        bot_config_id: Optional[int] = None,
        is_meta: bool = False,
        meta_keyword: Optional[str] = None,
    ) -> Optional[MessageORM]:
        """
        发送 Bot 消息
        
        Args:
            room_id: 对话 ID
            content: 消息内容
            bot_config_id: Bot 配置 ID
            is_meta: 是否元对话
            meta_keyword: 元对话关键词
            
        Returns:
            创建的消息对象
        """
        message = await self._room_service.send_message(
            room_id=room_id,
            sender_id=None,  # Bot 没有 user_id
            sender_type="bot",
            content=content,
            is_meta=is_meta,
            meta_keyword=meta_keyword,
        )
        
        if message:
            # WebSocket 推送
            await self._websocket_manager.send_to_room(room_id, {
                "type": "chat",
                "data": {
                    "id": message.id,
                    "sender": "bot",
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_meta": is_meta,
                }
            })
        
        return message
    
    async def _trigger_ai_response(
        self,
        room_id: str,
        user_message: str,
    ):
        """触发 AI 响应"""
        try:
            # TODO: 调用 Bot 服务获取响应
            # from turing_test.backend.services.ai_bot_service import get_bot_response
            # bot_response = await get_bot_response(user_message, room_id)
            
            # 临时实现
            bot_response = "收到你的消息了。"
            
            # 发送 Bot 消息
            await self.send_bot_message(
                room_id=room_id,
                content=bot_response,
            )
            
            # 更新会话状态（轮到用户）
            # TODO: 需要获取 session_id
            
        except Exception as e:
            logger.error(f"触发 AI 响应失败：{e}", exc_info=True)
    
    def _detect_meta_conversation(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        检测元对话关键词
        
        Args:
            content: 消息内容
            
        Returns:
            (是否元对话，关键词)
        """
        meta_keywords = [
            "你是谁",
            "你是 AI",
            "你是真人",
            "你是 bot",
            "聊天",
            "规则",
        ]
        
        content_lower = content.lower()
        for keyword in meta_keywords:
            if keyword in content_lower:
                return True, keyword
        
        return False, None
    
    async def get_room_messages(
        self,
        room_id: str,
        limit: int = 50,
    ) -> list[MessageORM]:
        """
        获取对话消息列表
        
        Args:
            room_id: 对话 ID
            limit: 数量限制
            
        Returns:
            消息列表
        """
        # TODO: 实现消息查询
        return []


# 工厂函数
def create_new_message_service(
    room_service: RoomApplicationService,
    session_service: SessionApplicationService,
    uow: AbstractUnitOfWork,
    websocket_manager: any,
) -> NewMessageService:
    """创建消息服务实例"""
    return NewMessageService(room_service, session_service, uow, websocket_manager)
