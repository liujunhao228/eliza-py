"""
匹配 WebSocket 端点（基于新领域模型）

职责：
1. 用户连接管理
2. 匹配请求处理（使用 MatchApplicationService）
3. 匹配结果推送（通过事件驱动）
4. 心跳检测

新架构：
- 匹配请求通过 WebSocket 接收
- 使用 MatchApplicationService 处理业务逻辑
- 通过领域事件推送匹配结果
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Set
import json
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from turing_test.backend.websocket.manager import manager
from turing_test.backend.application.match_service import MatchApplicationService
from turing_test.backend.domain.repositories import AbstractUnitOfWork
from turing_test.backend.infrastructure.events.event_bus import EventBus, Event, EventType
from turing_test.backend.infrastructure.events.event_handlers import MatchEventHandler

router = APIRouter()

# 全局连接管理
_connected_users: Dict[int, WebSocket] = {}
_pending_matches: Set[int] = set()


@router.websocket("/match")
async def match_websocket(
    websocket: WebSocket,
    user_id: int = Query(..., description="用户 ID"),
):
    """
    匹配 WebSocket 端点

    支持的操作：
    1. join - 加入匹配队列
    2. cancel - 取消匹配
    3. ping/pong - 心跳检测

    推送的事件：
    1. match_status - 匹配状态更新
    2. match_found - 匹配成功
    3. match_failed - 匹配失败
    4. match_cancelled - 匹配取消
    """
    try:
        # 连接用户
        await manager.connect(user_id, websocket)
        _connected_users[user_id] = websocket
        logger.info(f"用户 {user_id} 连接到匹配 WebSocket")

        # 发送连接确认
        await _send_message(user_id, {
            "type": "connected",
            "data": {
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        })

        # 主消息循环
        while True:
            try:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
                msg_type = data.get("type")

                if msg_type == "join":
                    # 加入匹配队列
                    await _handle_join(user_id, data.get("data", {}))
                
                elif msg_type == "cancel":
                    # 取消匹配
                    await _handle_cancel(user_id)
                
                elif msg_type == "ping":
                    # 心跳请求
                    await _send_message(user_id, {"type": "pong"})
                
                elif msg_type == "pong":
                    # 心跳响应（由 manager 统一处理）
                    pass
                
                else:
                    logger.debug(f"收到未知消息类型：{msg_type}")

            except json.JSONDecodeError:
                logger.warning(f"用户 {user_id} 发送了无效的 JSON")
            except WebSocketDisconnect as e:
                logger.info(f"用户 {user_id} 断开连接 (code={e.code})")
                break
            except Exception as e:
                error_str = str(e).lower()
                if 'close' in error_str or 'disconnect' in error_str:
                    logger.info(f"用户 {user_id} 连接已关闭：{e}")
                    break
                logger.error(f"处理用户 {user_id} 消息时出错：{e}", exc_info=True)

    except WebSocketDisconnect:
        logger.info(f"用户 {user_id} 正常断开连接")
    except Exception as e:
        logger.error(f"匹配 WebSocket 错误：{e}", exc_info=True)
    finally:
        # 清理资源
        _connected_users.pop(user_id, None)
        _pending_matches.discard(user_id)
        manager.disconnect(user_id)
        logger.info(f"用户 {user_id} 已清理匹配状态")


async def _handle_join(user_id: int, data: dict):
    """
    处理加入匹配请求

    流程：
    1. 检查用户是否已有待处理匹配
    2. 获取用户积分
    3. 调用 MatchApplicationService.request_match
    4. 推送匹配状态
    """
    if user_id in _pending_matches:
        await _send_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "ALREADY_MATCHING",
                "message": "您已在匹配队列中",
            }
        })
        return

    try:
        # 获取用户积分（从数据库）
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import User
        
        async with async_session_maker() as session:
            user = await session.get(User, user_id)
            if not user:
                await _send_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "USER_NOT_FOUND",
                        "message": "用户不存在",
                    }
                })
                return
            
            user_score = user.score
        
        # 创建匹配请求
        async with async_session_maker() as session:
            from turing_test.backend.domain.repositories import SqlAlchemyUnitOfWork
            
            uow = SqlAlchemyUnitOfWork(session)
            event_bus = EventBus()
            
            match_service = MatchApplicationService(uow, event_bus)
            
            # 请求匹配
            match = await match_service.request_match(
                user_id=user_id,
                user_score=user_score,
                preferences=data.get("preferences", {}),
            )
            
            _pending_matches.add(user_id)
            
            # 推送匹配状态
            await _send_message(user_id, {
                "type": "match_status",
                "data": {
                    "status": "searching",
                    "match_id": str(match.id),
                    "message": "正在为您寻找对手...",
                    "user_score": user_score,
                }
            })
            
            logger.info(f"用户 {user_id} 加入匹配队列：match_id={match.id}")
            
            # TODO: 这里需要集成匹配池系统进行实际匹配
            # 临时模拟匹配成功
            # await _simulate_match(user_id, match.id, event_bus)
            
    except Exception as e:
        logger.error(f"处理加入匹配请求失败：user_id={user_id}, error={e}", exc_info=True)
        _pending_matches.discard(user_id)
        await _send_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "MATCH_ERROR",
                "message": f"匹配失败：{str(e)}",
            }
        })


async def _handle_cancel(user_id: int):
    """处理取消匹配请求"""
    if user_id not in _pending_matches:
        await _send_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "NOT_MATCHING",
                "message": "您不在匹配队列中",
            }
        })
        return

    try:
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.domain.repositories import SqlAlchemyUnitOfWork
        from turing_test.backend.domain.models import MatchId
        
        async with async_session_maker() as session:
            uow = SqlAlchemyUnitOfWork(session)
            event_bus = EventBus()
            
            match_service = MatchApplicationService(uow, event_bus)
            
            # 获取待处理匹配
            match = await match_service.get_pending_match(user_id)
            
            if match:
                # 取消匹配
                success = await match_service.cancel_match(str(match.id))
                if success:
                    _pending_matches.discard(user_id)
                    await _send_message(user_id, {
                        "type": "match_cancelled",
                        "data": {
                            "message": "匹配已取消",
                        }
                    })
                    logger.info(f"用户 {user_id} 取消匹配：match_id={match.id}")
            else:
                _pending_matches.discard(user_id)
                await _send_message(user_id, {
                    "type": "match_cancelled",
                    "data": {
                        "message": "未找到待处理匹配",
                    }
                })
                
    except Exception as e:
        logger.error(f"取消匹配失败：user_id={user_id}, error={e}", exc_info=True)


async def _send_message(user_id: int, message: dict):
    """发送消息给用户"""
    if user_id in _connected_users:
        websocket = _connected_users[user_id]
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败：user_id={user_id}, error={e}")


async def _simulate_match(user_id: int, match_id: str, event_bus: EventBus):
    """
    模拟匹配成功（临时实现）
    
    TODO: 替换为实际的匹配池逻辑
    """
    await asyncio.sleep(2)  # 模拟匹配延迟
    
    # 模拟匹配成功事件
    if event_bus:
        await event_bus.publish(
            Event(
                event_type=EventType.MATCH_COMPLETED,
                aggregate_id=match_id,
                aggregate_type="Match",
                data={
                    "user_id": user_id,
                    "room_id": "1",  # 临时 room_id
                    "opponent_type": "bot",
                    "bot_config_id": 1,
                    "bot_level": "lv2_typical",
                }
            )
        )
