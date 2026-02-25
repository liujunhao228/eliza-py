"""
聊天 WebSocket 端点（完善版）

处理聊天相关的 WebSocket 通信，优化消息处理和 AI 响应逻辑。
"""

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from loguru import logger
import json
import asyncio

from turing_test.backend.websocket.manager import manager
from turing_test.backend.database import async_session_maker
from config import settings

router = APIRouter()


# =============================================================================
# 元对话关键词检测
# =============================================================================

META_KEYWORDS = [
    '真人', '机器', 'AI', '机器人', '人工智能',
    '程序', '算法', '人类', '人', '电脑', '计算',
    '你是', '我是', '身份', '真假', '还是', '到底'
]


def is_meta_conversation(message: str) -> tuple[bool, Optional[str]]:
    """
    检测消息是否为元对话

    Args:
        message: 用户消息

    Returns:
        (是否为元对话，触发的关键词)
    """
    message_lower = message.lower()
    for keyword in META_KEYWORDS:
        if keyword in message_lower:
            return True, keyword
    return False, None


# =============================================================================
# 消息处理器
# =============================================================================

class ChatMessageHandler:
    """聊天消息处理器"""

    @staticmethod
    async def handle_connect(
        user_id: int,
        session_id: int,
        websocket: WebSocket,
        db: AsyncSession,
    ) -> Optional["Session"]:
        """
        处理用户连接

        Returns:
            会话对象，失败则返回 None
        """
        from turing_test.backend.models import Session

        # 验证会话
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            await manager.send_personal_message(user_id, {
                "type": "error",
                "data": {
                    "error_code": "SESSION_NOT_FOUND",
                    "message": "会话不存在",
                }
            })
            return None

        # 验证用户是否属于此会话
        if session.user_id != user_id:
            await manager.send_personal_message(user_id, {
                "type": "error",
                "data": {
                    "error_code": "SESSION_NOT_OWNED",
                    "message": "您不属于此会话",
                }
            })
            return None

        # 设置用户会话关联
        manager.set_user_session(user_id, session_id)

        # 发送连接确认消息
        await manager.send_personal_message(user_id, {
            "type": "connected",
            "data": {
                "session_id": session_id,
                "opponent_type": session.opponent_type,
                "is_honeypot": session.is_honeypot,
                "meta_conversation_count": session.meta_conversation_count,
                "turn_count": session.turn_count,
            }
        })

        return session

    @staticmethod
    async def process_message(
        user_id: int,
        session: "Session",
        data: dict,
        db: AsyncSession,
    ):
        """处理收到的消息"""
        msg_type = data.get("type")

        if msg_type in ["chat", "message"]:
            await handle_chat_message(user_id, session, data, db)
        elif msg_type == "mid_game_judgment":
            await handle_mid_game_judgment(user_id, session, data, db)
        elif msg_type == "end_session":
            await handle_end_session(user_id, session, db)
        elif msg_type == "pong":
            # 心跳响应由 manager 处理
            pass
        else:
            logger.warning(f"收到未知消息类型：{msg_type}")
            await manager.send_personal_message(user_id, {
                "type": "error",
                "data": {
                    "error_code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"未知的消息类型：{msg_type}",
                }
            })


# =============================================================================
# WebSocket 端点
# =============================================================================

@router.websocket("/chat")
async def chat_websocket(
    websocket: WebSocket,
    user_id: int = Query(..., description="用户 ID"),
    session_id: int = Query(..., description="会话 ID"),
):
    """
    聊天 WebSocket

    客户端连接流程:
    1. 建立连接并验证用户和会话
    2. 服务器发送连接确认和会话信息
    3. 客户端可以开始发送消息
    4. 定期处理心跳消息 (type: pong)

    支持的消息类型:
    - chat: 发送聊天消息
    - mid_game_judgment: 场中判断
    - end_session: 结束会话
    - pong: 心跳响应

    服务器发送的消息类型:
    - connected: 连接确认
    - chat: 聊天消息
    - typing: 打字提示
    - mid_game_result: 场中判断结果
    - error: 错误消息
    - ping: 心跳消息
    """
    async with async_session_maker() as db:
        try:
            # 连接用户
            await manager.connect(user_id, websocket)
            logger.info(f"用户 {user_id} 加入会话 {session_id}")

            # 验证会话并发送连接确认
            session = await ChatMessageHandler.handle_connect(
                user_id, session_id, websocket, db
            )
            if session is None:
                await manager.disconnect(user_id)
                return

            # 主消息循环
            while True:
                try:
                    # 接收消息
                    raw_data = await websocket.receive_text()
                    data = json.loads(raw_data)

                    # 处理消息
                    await manager.handle_message(user_id, data)

                    # 处理业务消息
                    await ChatMessageHandler.process_message(
                        user_id, session, data, db
                    )

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
                except WebSocketDisconnect:
                    logger.info(f"用户 {user_id} 连接已断开")
                    break  # 退出消息循环
                except Exception as e:
                    # 检查是否是连接关闭相关的错误
                    error_str = str(e).lower()
                    if 'close' in error_str or 'disconnect' in error_str or 'connection was closed' in error_str:
                        logger.info(f"用户 {user_id} 连接已关闭：{e}")
                        break  # 退出循环，不再尝试发送消息
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
            logger.error(f"聊天 WebSocket 错误：{e}", exc_info=True)
        finally:
            # 确保清理资源
            manager.disconnect(user_id)


async def handle_chat_message(
    user_id: int,
    session: "Session",
    data: dict,
    db: AsyncSession,
):
    """处理聊天消息"""
    from turing_test.backend.models import Message

    content = data.get("data", {}).get("content", "")

    # 验证消息内容
    if not content or not content.strip():
        await manager.send_personal_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "EMPTY_MESSAGE",
                "message": "消息内容不能为空",
            }
        })
        return

    max_length = settings.turing.performance.max_input_length
    if len(content) > max_length:
        await manager.send_personal_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "MESSAGE_TOO_LONG",
                "message": f"消息长度不能超过 {max_length} 字符",
            }
        })
        return

    # 检测元对话
    is_meta, keyword = is_meta_conversation(content)

    # 保存消息到数据库
    message = Message(
        session_id=session.id,
        sender="user",
        content=content,
        is_meta_conversation=is_meta,
        meta_keyword=keyword if is_meta else None,
    )
    db.add(message)

    # 更新会话统计
    if is_meta:
        session.meta_conversation_count += 1
        logger.info(f"检测到元对话，关键词：{keyword}")

    await db.commit()
    
    # 获取消息 ID
    await db.refresh(message)
    
    logger.debug(f"handle_chat_message: 用户消息已保存，message_id={message.id}")

    # 转发消息到会话中的其他用户
    await manager.send_to_session(session.id, {
        "type": "chat",
        "data": {
            "id": message.id,
            "sender": "user",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_meta_conversation": is_meta,
        }
    })

    # 如果是 AI 对手，生成响应
    if session.opponent_type in ["ai", "honeypot"]:
        logger.debug(f"开始处理 AI 响应：session_id={session.id}, opponent_type={session.opponent_type}, is_honeypot={session.is_honeypot}")
        await handle_ai_response(session.id, content, db)
    else:
        logger.debug(f"跳过 AI 响应：session_id={session.id}, opponent_type={session.opponent_type}")


async def handle_mid_game_judgment(
    user_id: int,
    session: "Session",
    data: dict,
    db: AsyncSession,
):
    """处理场中判断"""
    from turing_test.backend.models import User, ScoreHistory
    from turing_test.backend.utils.score_calculator import (
        calculate_final_score,
        get_score_breakdown_dict,
    )

    user_guess = data.get("data", {}).get("user_guess")

    # 验证判断类型
    if user_guess not in ["human", "ai"]:
        await manager.send_personal_message(user_id, {
            "type": "error",
            "data": {
                "error_code": "INVALID_JUDGMENT",
                "message": "判断类型必须是 'human' 或 'ai'",
            }
        })
        return

    # 获取用户
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
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

    # 计算积分（场中判断双倍乘数）
    turn = session.turn_count
    meta_count = session.meta_conversation_count

    final_score, breakdown = calculate_final_score(
        user_guess=user_guess,
        opponent_type=session.opponent_type,
        confidence_level="mid",  # 场中判断默认为中等信心
        turn=turn,
        meta_count=meta_count,
        is_mid_game=True,  # 场中判断双倍乘数
    )

    # 更新会话状态
    session.triggered_mid_game = True
    session.confidence_level = "mid"
    session.is_correct = breakdown.is_correct
    session.final_score = int(final_score)
    session.score_breakdown = get_score_breakdown_dict(breakdown)
    session.ended_at = datetime.now(timezone.utc)

    # 更新用户积分
    score_before = user.score
    user.score += int(final_score)

    if final_score > 0:
        user.total_score_earned += int(final_score)
    else:
        user.total_score_lost += abs(int(final_score))

    # 更新最高/最低分
    if user.score > user.highest_score:
        user.highest_score = user.score
    if user.score < user.lowest_score:
        user.lowest_score = user.score

    # 记录积分历史
    score_history = ScoreHistory(
        user_id=user.id,
        session_id=session.id,
        score_change=int(final_score),
        score_before=score_before,
        score_after=user.score,
        reason="mid_game_judgment",
    )
    db.add(score_history)

    await db.commit()

    logger.info(
        f"场中判断：user_id={user_id}, session_id={session.id}, "
        f"guess={user_guess}, opponent={session.opponent_type}, "
        f"correct={breakdown.is_correct}, score={final_score}"
    )

    # 发送结果
    await manager.send_personal_message(user_id, {
        "type": "mid_game_result",
        "data": {
            "session_id": session.id,
            "is_correct": breakdown.is_correct,
            "opponent_type": session.opponent_type,
            "final_score": int(final_score),
            "score_breakdown": get_score_breakdown_dict(breakdown),
        }
    })


async def handle_end_session(
    user_id: int,
    session: "Session",
    db: AsyncSession,
):
    """处理结束会话"""
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(f"用户 {user_id} 结束会话 {session.id}")


async def handle_ai_response(
    session_id: int,
    user_message: str,
    db: AsyncSession,
):
    """
    处理 AI 响应

    使用 AliceBot 生成真实的响应，支持打字延迟模拟。
    对于钓鱼机器人，添加更多人类行为特征。
    """
    from turing_test.backend.models import Message, Session
    from sqlalchemy import select
    from turing_test.backend.websocket.manager import manager

    # 获取会话中的用户 ID
    session_users = manager.session_users.get(session_id, set())
    user_ids = list(session_users)
    
    logger.debug(f"handle_ai_response: session_id={session_id}, session_users={session_users}, user_ids={user_ids}")
    logger.debug(f"handle_ai_response: 用户连接状态={[(uid, manager.is_user_connected(uid)) for uid in user_ids]}")

    # 检查是否还有在线用户
    if not user_ids or not any(manager.is_user_connected(uid) for uid in user_ids):
        logger.warning(f"会话 {session_id} 中没有在线用户，跳过 AI 响应")
        return

    # 发送打字提示
    typing_sent = await manager.send_to_session(session_id, {
        "type": "typing",
        "data": {
            "sender": "opponent",
            "is_typing": True,
        }
    })
    
    logger.debug(f"handle_ai_response: 打字提示发送结果={typing_sent}")

    if typing_sent == 0:
        logger.warning(f"会话 {session_id} 中没有可接收消息的用户，跳过 AI 响应")
        return

    ai_response = "系统出现故障，请稍后再试。"
    ai_delay = 1.0
    is_meta = False

    try:
        # 调用 AI Bot 服务生成响应
        from turing_test.backend.services.ai_bot_service import get_bot_response
        base_response, base_delay = await get_bot_response(user_message)

        # 检测是否为元对话
        is_meta, _ = is_meta_conversation(user_message)

        # 如果是钓鱼机器人，使用钓鱼机器人服务增强拟真度
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one()

        if session.is_honeypot:
            from turing_test.backend.services.honeypot_service import get_honeypot_service
            honeypot_service = get_honeypot_service()

            # 生成带拟人特征的响应
            ai_response, ai_delay = honeypot_service.get_response_with_delay(
                base_response=base_response,
                session_id=session_id,
                is_meta=is_meta,
                user_message=user_message,
            )

            # 记录元对话响应
            if is_meta:
                honeypot_service.record_meta_response(session_id)
        else:
            # 普通 AI 机器人
            ai_response = base_response
            ai_delay = base_delay

        logger.info(f"AI 响应生成成功：session_id={session_id}, 响应长度={len(ai_response)}, 延迟={ai_delay:.2f}秒")

    except Exception as e:
        logger.error(f"生成 AI 响应失败：{e}", exc_info=True)

    # 发送停止打字提示（无论 AI 响应是否成功都发送）
    stop_typing_result = await manager.send_to_session(session_id, {
        "type": "stop_typing",
        "data": {
            "sender": "opponent",
            "is_typing": False,
        }
    })

    logger.info(f"handle_ai_response: 停止打字提示发送结果={stop_typing_result}")

    # 保存 AI 消息
    message = Message(
        session_id=session_id,
        sender="opponent",
        content=ai_response,
        is_meta_conversation=is_meta_conversation(ai_response)[0],
    )
    db.add(message)

    # 更新轮数
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one()
    session.turn_count += 2  # 一轮包括用户和对手各一条消息

    await db.commit()

    # 获取消息 ID 用于前端显示
    await db.refresh(message)
    message_id = message.id
    logger.debug(f"handle_ai_response: AI 消息已保存，message_id={message_id}")

    # 发送 AI 响应
    send_result = await manager.send_to_session(session_id, {
        "type": "chat",
        "data": {
            "id": message_id,
            "sender": "opponent",
            "content": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_meta_conversation": is_meta_conversation(ai_response)[0],
        }
    })

    logger.info(f"handle_ai_response: AI 响应已发送：session_id={session_id}, 发送结果={send_result}, 响应长度={len(ai_response)}, message_id={message_id}")
