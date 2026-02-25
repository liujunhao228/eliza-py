"""
匹配 WebSocket 端点（完善版）

处理匹配相关的 WebSocket 通信，使用 MatchService 实现真人匹配和 AI 备选逻辑。
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger
import json
from datetime import datetime, timezone

from turing_test.backend.websocket.manager import manager
from turing_test.backend.services.match_service import get_match_service
from config import settings

router = APIRouter()


# =============================================================================
# WebSocket 端点
# =============================================================================

@router.websocket("/match")
async def match_websocket(
    websocket: WebSocket,
    user_id: int = Query(..., description="用户 ID"),
):
    """
    匹配 WebSocket

    客户端连接流程:
    1. 建立连接
    2. 服务器发送连接确认
    3. 客户端可以发送消息

    支持的消息类型:
    - join: 加入匹配队列
    - cancel: 取消匹配
    - status: 查询匹配状态

    服务器发送的消息类型:
    - connected: 连接确认
    - match_found: 匹配成功
    - match_failed: 匹配失败
    - status: 匹配状态更新
    - queue_status: 队列状态更新
    - error: 错误消息
    """
    try:
        # 连接用户
        await manager.connect(user_id, websocket)
        logger.info(f"用户 {user_id} 连接到匹配 WebSocket")

        # 发送连接确认消息
        await manager.send_personal_message(user_id, {
            "type": "connected",
            "data": {
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        })

        # 主消息循环
        while True:
            try:
                # 接收消息
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                # 处理消息
                await manager.handle_message(user_id, data)

                # 处理加入队列
                if data.get("type") == "join":
                    await handle_join_queue(user_id, websocket)

                # 处理取消匹配
                elif data.get("type") == "cancel":
                    await handle_cancel_match(user_id, websocket)

                # 处理查询状态
                elif data.get("type") == "status":
                    await handle_status_query(user_id, websocket)

                # 处理心跳
                elif data.get("type") == "ping":
                    # 响应心跳
                    await manager.send_personal_message(user_id, {
                        "type": "pong",
                        "data": {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    })

                # 处理心跳响应
                elif data.get("type") == "pong":
                    # 心跳响应由 manager 处理
                    pass

                # 处理未知消息类型
                else:
                    logger.warning(f"收到未知消息类型：{data.get('type')}")
                    await manager.send_personal_message(user_id, {
                        "type": "error",
                        "data": {
                            "error_code": "UNKNOWN_MESSAGE_TYPE",
                            "message": f"未知的消息类型：{data.get('type')}",
                        }
                    })

            except json.JSONDecodeError:
                logger.warning(f"用户 {user_id} 发送了无效的 JSON")
                if manager.is_user_connected(user_id):
                    await manager.send_personal_message(user_id, {
                        "type": "error",
                        "data": {
                            "error_code": "INVALID_JSON",
                            "message": "消息格式错误，请发送有效的 JSON",
                        }
                    })
            except WebSocketDisconnect as e:
                # WebSocket 正常断开（code=0 表示正常关闭）
                logger.info(f"用户 {user_id} 连接已关闭 (code={e.code})")
                break  # 退出循环，不再尝试发送消息
            except Exception as e:
                # 检查是否是连接关闭相关的错误
                error_str = str(e).lower()
                if 'close' in error_str or 'disconnect' in error_str or 'connection was closed' in error_str:
                    logger.info(f"用户 {user_id} 连接已关闭：{e}")
                    break  # 退出循环，不再尝试发送消息
                # 其他错误才记录为 error 级别
                logger.error(f"处理用户 {user_id} 消息时出错：{e}", exc_info=True)
                if manager.is_user_connected(user_id):
                    await manager.send_personal_message(user_id, {
                        "type": "error",
                        "data": {
                            "error_code": "PROCESSING_ERROR",
                            "message": "处理消息时出错，请重试",
                        }
                    })

    except WebSocketDisconnect:
        logger.info(f"用户 {user_id} 正常断开连接")
    except Exception as e:
        logger.error(f"匹配 WebSocket 错误：{e}", exc_info=True)
    finally:
        # 清理资源（确保总是执行）
        match_service = get_match_service()
        # 从匹配队列移除（如果用户在队列中）
        try:
            await match_service.remove_from_queue(user_id)
        except Exception as e:
            logger.error(f"清理匹配队列时出错：{e}")
        # 断开连接（使用改进的 disconnect 方法）
        manager.disconnect(user_id)


async def handle_join_queue(user_id: int, websocket: WebSocket):
    """
    处理加入队列请求

    流程:
    1. 获取用户积分（用于优先级计算）
    2. 将用户加入匹配队列
    3. 发送确认消息
    4. 启动匹配任务
    """
    from turing_test.backend.database import async_session_maker
    from turing_test.backend.models import User
    from sqlalchemy import select
    
    match_service = get_match_service()

    # 检查用户是否已在队列中
    if match_service.is_user_waiting(user_id):
        await manager.send_personal_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "ALREADY_IN_QUEUE",
                "message": "您已经在匹配队列中",
            }
        })
        return

    # 获取用户积分
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            await manager.send_personal_message(user_id, {
                "type": "error",
                "data": {
                    "error_code": "USER_NOT_FOUND",
                    "message": "用户不存在",
                }
            })
            return
        
        user_score = user.score

    # 添加到匹配队列（传入用户积分）
    success = await match_service.add_to_queue(user_id, id(websocket), user_score)

    if not success:
        await manager.send_personal_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "QUEUE_ERROR",
                "message": "加入队列失败，请稍后再试",
            }
        })
        return

    # 发送状态更新
    position = await match_service.get_queue_position(user_id)
    queue_size = match_service.get_queue_size()

    await manager.send_personal_message(user_id, {
        "type": "status",
        "data": {
            "in_queue": True,
            "queue_size": queue_size,
            "queue_position": position,
            "estimated_wait_time": queue_size * 5,  # 估计每人 5 秒
        }
    })

    # 启动匹配任务
    await match_service.start_match_task(user_id, id(websocket))


async def handle_cancel_match(user_id: int, websocket: WebSocket):
    """
    处理取消匹配请求
    """
    match_service = get_match_service()

    if await match_service.remove_from_queue(user_id):
        await manager.send_personal_message(user_id, {
            "type": "status",
            "data": {
                "in_queue": False,
                "queue_size": match_service.get_queue_size(),
            }
        })
    else:
        await manager.send_personal_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "NOT_IN_QUEUE",
                "message": "您不在匹配队列中",
            }
        })


async def handle_status_query(user_id: int, websocket: WebSocket):
    """
    处理状态查询请求
    """
    match_service = get_match_service()

    position = await match_service.get_queue_position(user_id)
    queue_size = match_service.get_queue_size()

    await manager.send_personal_message(user_id, {
        "type": "status",
        "data": {
            "in_queue": match_service.is_user_waiting(user_id),
            "queue_size": queue_size,
            "queue_position": position,
            "estimated_wait_time": queue_size * 5 if position else None,
        }
    })
