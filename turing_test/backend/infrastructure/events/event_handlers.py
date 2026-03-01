"""
领域事件处理器 - Event Handlers

负责处理领域事件，执行跨聚合根的业务逻辑

设计原则:
1. 事件驱动 - 响应领域事件
2. 最终一致性 - 异步更新相关聚合
3. 事务分离 - 每个处理器独立事务
"""

from loguru import logger

from turing_test.backend.infrastructure.events.event_bus import Event, EventType, EventHandler
from turing_test.backend.application.match_service import MatchApplicationService
from turing_test.backend.application.room_service import RoomApplicationService
from turing_test.backend.application.session_service import SessionApplicationService
from turing_test.backend.domain.models import RoomType, ParticipantRole


class MatchEventHandler(EventHandler):
    """
    匹配领域事件处理器
    
    处理：
    1. MatchRequested - 用户请求匹配，加入匹配池
    2. MatchCompleted - 匹配完成，创建 Room 和 UserSession
    3. MatchFailed - 匹配失败，通知用户
    4. MatchCancelled - 匹配取消，清理匹配池
    """
    
    def __init__(
        self,
        room_service: RoomApplicationService,
        session_service: SessionApplicationService,
        websocket_manager: any,
    ):
        self._room_service = room_service
        self._session_service = session_service
        self._websocket_manager = websocket_manager
    
    @property
    def event_types(self) -> list[EventType]:
        return [
            EventType.MATCH_REQUESTED,
            EventType.MATCH_COMPLETED,
            EventType.MATCH_FAILED,
            EventType.MATCH_CANCELLED,
        ]
    
    async def handle(self, event: Event) -> None:
        """处理匹配事件"""
        handler = getattr(self, f"_handle_{event.event_type.value.replace('.', '_')}", None)
        if handler:
            await handler(event)
    
    async def _handle_match_requested(self, event: Event) -> None:
        """处理匹配请求事件"""
        user_id = event.data.get("user_id")
        logger.info(f"收到匹配请求事件：user_id={user_id}")
        
        # TODO: 将用户加入匹配池
        # 这里需要集成现有的匹配池系统
        
        # 通知用户匹配已开始
        if self._websocket_manager:
            await self._websocket_manager.send_personal_message(user_id, {
                "type": "match_status",
                "data": {
                    "status": "searching",
                    "message": "正在为您寻找对手...",
                }
            })
    
    async def _handle_match_completed(self, event: Event) -> None:
        """处理匹配完成事件"""
        room_id = event.data.get("room_id")
        match_id = event.aggregate_id
        opponent_type = event.data.get("opponent_type")
        matched_opponent_id = event.data.get("matched_opponent_id")
        bot_config_id = event.data.get("bot_config_id")
        bot_level = event.data.get("bot_level")
        
        logger.info(
            f"匹配完成：match_id={match_id}, room_id={room_id}, "
            f"opponent_type={opponent_type}"
        )
        
        # 如果 Room 已存在，只需创建 UserSession
        # 这里假设 Room 由匹配服务创建
        
        # 为匹配发起者创建 UserSession
        user_id = event.data.get("user_id")
        if user_id:
            await self._session_service.create_session(
                user_id=user_id,
                room_id=room_id,
                match_id=match_id,
            )
        
        # 如果是真人对战，为对手创建 UserSession
        if matched_opponent_id:
            await self._session_service.create_session(
                user_id=matched_opponent_id,
                room_id=room_id,
                match_id=match_id,
            )
        
        # 添加 Bot 参与者（如果是 Bot 对战）
        if bot_config_id:
            await self._room_service.add_participant(
                room_id=room_id,
                user_id=None,  # Bot 没有 user_id
                role=ParticipantRole.BOT,
                bot_config_id=bot_config_id,
                bot_level=bot_level,
            )
        
        # 通知用户匹配成功
        if self._websocket_manager and user_id:
            await self._websocket_manager.send_personal_message(user_id, {
                "type": "match_found",
                "data": {
                    "room_id": room_id,
                    "opponent_type": opponent_type,
                    "message": "匹配成功！对话即将开始",
                }
            })
    
    async def _handle_match_failed(self, event: Event) -> None:
        """处理匹配失败事件"""
        user_id = event.data.get("user_id")
        reason = event.data.get("reason")
        
        logger.warning(f"匹配失败：user_id={user_id}, reason={reason}")
        
        # 通知用户匹配失败
        if self._websocket_manager and user_id:
            await self._websocket_manager.send_personal_message(user_id, {
                "type": "match_failed",
                "data": {
                    "reason": reason,
                    "message": f"匹配失败：{reason}",
                }
            })
    
    async def _handle_match_cancelled(self, event: Event) -> None:
        """处理匹配取消事件"""
        user_id = event.data.get("user_id")
        
        logger.info(f"匹配取消：user_id={user_id}")
        
        # 通知用户匹配已取消
        if self._websocket_manager and user_id:
            await self._websocket_manager.send_personal_message(user_id, {
                "type": "match_cancelled",
                "data": {
                    "message": "匹配已取消",
                }
            })


class RoomEventHandler(EventHandler):
    """
    对话领域事件处理器
    
    处理：
    1. SessionCreated - 对话创建，初始化
    2. SessionMessageSent - 消息发送，通知接收方
    3. SessionEnded - 对话结束，触发积分结算
    """
    
    def __init__(
        self,
        session_service: SessionApplicationService,
        websocket_manager: any,
    ):
        self._session_service = session_service
        self._websocket_manager = websocket_manager
    
    @property
    def event_types(self) -> list[EventType]:
        return [
            EventType.SESSION_CREATED,
            EventType.SESSION_STARTED,
            EventType.SESSION_MESSAGE_SENT,
            EventType.SESSION_ENDED,
        ]
    
    async def handle(self, event: Event) -> None:
        """处理对话事件"""
        handler = getattr(self, f"_handle_{event.event_type.value.replace('.', '_')}", None)
        if handler:
            await handler(event)
    
    async def _handle_session_created(self, event: Event) -> None:
        """处理对话创建事件"""
        room_id = event.aggregate_id
        logger.info(f"对话已创建：room_id={room_id}")
    
    async def _handle_session_started(self, event: Event) -> None:
        """处理对话开始事件"""
        room_id = event.aggregate_id
        logger.info(f"对话已开始：room_id={room_id}")
    
    async def _handle_session_message_sent(self, event: Event) -> None:
        """处理消息发送事件"""
        room_id = event.aggregate_id
        message_id = event.data.get("message_id")
        sender_id = event.data.get("sender_id")
        sender_type = event.data.get("sender_type")
        
        logger.debug(f"消息已发送：message_id={message_id}, room_id={room_id}")
        
        # 通过 WebSocket 推送消息给相关用户
        # TODO: 需要获取 Room 中的所有参与者并推送
    
    async def _handle_session_ended(self, event: Event) -> None:
        """处理对话结束事件"""
        room_id = event.aggregate_id
        end_reason = event.data.get("end_reason")
        
        logger.info(f"对话已结束：room_id={room_id}, reason={end_reason}")
        
        # TODO: 触发所有参与者的积分结算


class ScoreEventHandler(EventHandler):
    """
    积分领域事件处理器
    
    处理：
    1. ScoreSettled - 积分结算，更新用户总积分
    2. ScoreBonusClaimed - 奖励申领，发放额外奖励
    """
    
    def __init__(
        self,
        db_session_factory: any,
    ):
        self._db_session_factory = db_session_factory
    
    @property
    def event_types(self) -> list[EventType]:
        return [
            EventType.SCORE_SETTLED,
            EventType.SCORE_BONUS_CLAIMED,
        ]
    
    async def handle(self, event: Event) -> None:
        """处理积分事件"""
        handler = getattr(self, f"_handle_{event.event_type.value.replace('.', '_')}", None)
        if handler:
            await handler(event)
    
    async def _handle_score_settled(self, event: Event) -> None:
        """处理积分结算事件"""
        session_id = event.aggregate_id
        final_score = event.data.get("final_score")
        
        logger.info(f"积分已结算：session_id={session_id}, final_score={final_score}")
        
        # TODO: 更新用户总积分
        # 需要获取 UserSession 的 user_id 并更新 User.score
    
    async def _handle_score_bonus_claimed(self, event: Event) -> None:
        """处理奖励申领事件"""
        session_id = event.aggregate_id
        bonus_amount = event.data.get("bonus_amount")
        
        logger.info(f"奖励已申领：session_id={session_id}, amount={bonus_amount}")


# 工厂函数
def create_match_event_handler(
    room_service: RoomApplicationService,
    session_service: SessionApplicationService,
    websocket_manager: any,
) -> MatchEventHandler:
    """创建匹配事件处理器"""
    return MatchEventHandler(room_service, session_service, websocket_manager)


def create_room_event_handler(
    session_service: SessionApplicationService,
    websocket_manager: any,
) -> RoomEventHandler:
    """创建对话事件处理器"""
    return RoomEventHandler(session_service, websocket_manager)


def create_score_event_handler(
    db_session_factory: any,
) -> ScoreEventHandler:
    """创建积分事件处理器"""
    return ScoreEventHandler(db_session_factory)
