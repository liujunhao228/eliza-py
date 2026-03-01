"""
聊天 WebSocket 端点（重构版）

处理聊天相关的 WebSocket 通信，使用 MessageService 和 SessionStateManager
实现内存级状态管理和并发控制。
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
        from turing_test.backend.services.session_state import session_state_manager

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

        # 创建或获取内存状态
        await session_state_manager.create(
            session_id=session_id,
            user_id=user_id,
            is_honeypot=session.is_honeypot,
            opponent_type=session.opponent_type,
        )
        
        state = session_state_manager.get(session_id)

        # 发送连接确认消息（包含状态信息）
        await manager.send_personal_message(user_id, {
            "type": "connected",
            "data": {
                "session_id": session_id,
                "opponent_type": session.opponent_type,
                "is_honeypot": session.is_honeypot,
                "turn_count": state.turn_count if state else 0,
                "is_user_turn": state.is_user_turn if state else True,
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
        from turing_test.backend.services.message_service import MessageService

        msg_type = data.get("type")

        if msg_type in ["chat", "message"]:
            content = data.get("data", {}).get("content", "")
            # 使用新的 MessageService 处理用户消息
            await MessageService.handle_user_message(
                session_id=session.id,
                user_id=user_id,
                content=content,
                db=db,
            )
        elif msg_type == "mid_game_judgment":
            await handle_mid_game_judgment(user_id, session, data, db)
        elif msg_type == "end_session":
            # 从客户端获取结束原因，默认为 "user_gave_up"
            end_reason = data.get("data", {}).get("end_reason", "user_gave_up")
            await handle_end_session(user_id, session, db, end_reason)
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
            # 清理会话状态
            from turing_test.backend.services.session_state import session_state_manager
            session_state_manager.cleanup(session_id)

            # 如果会话未正常结束，标记为系统错误结束
            try:
                # 检查会话是否已结束
                from turing_test.backend.models import Session
                async with async_session_maker() as cleanup_db:
                    result = await cleanup_db.execute(
                        select(Session).where(Session.id == session_id)
                    )
                    session = result.scalar_one_or_none()
                    if session and session.ended_at is None:
                        # 会话未结束，标记为系统错误
                        session.ended_at = datetime.now(timezone.utc)
                        session.end_reason = "sys_error"
                        await cleanup_db.commit()
                        logger.info(
                            f"会话异常结束：user_id={user_id}, session_id={session_id}, "
                            f"reason=sys_error (连接异常断开)"
                        )
            except Exception as e:
                logger.error(f"标记会话异常结束时出错：{e}")


async def handle_mid_game_judgment(
    user_id: int,
    session: "Session",
    data: dict,
    db: AsyncSession,
):
    """处理场中判断（记录判断时的轮次和元对话次数）"""
    from turing_test.backend.models import User
    from turing_test.backend.utils.score_calculator import (
        calculate_final_score,
        get_score_breakdown_dict,
        apply_score_change,
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

    # === 关键：记录场中判断时的轮次和元对话次数 ===
    mid_game_turn = session.turn_count
    mid_game_meta_count = session.meta_conversation_count

    # 计算积分（使用场中判断时的数据）
    final_score, breakdown = calculate_final_score(
        user_guess=user_guess,
        opponent_type=session.opponent_type,
        confidence_level="high",  # 场中判断固定为高信心
        turn=mid_game_turn,  # 使用场中判断时的轮次
        meta_count=mid_game_meta_count,  # 使用场中判断时的元对话次数
        is_mid_game=True,  # 场中判断双倍乘数
    )

    # 更新会话状态
    session.triggered_mid_game = True
    session.confidence_level = "high"
    session.user_guess = user_guess
    session.is_correct = breakdown.is_correct
    session.final_score = int(final_score)
    session.score_breakdown = get_score_breakdown_dict(breakdown)
    # === 新增：记录场中判断时的状态 ===
    session.mid_game_turn = mid_game_turn
    session.mid_game_meta_count = mid_game_meta_count
    # 注意：场中判断不结束会话，仅记录积分，end_reason 由用户后续点击"结束对话"时设置

    # 使用统一函数更新用户积分
    apply_score_change(
        user=user,
        session=session,
        score_change=int(final_score),
        reason="mid_game_judgment",
        db=db,
    )

    # 提交事务
    await db.commit()
    await db.refresh(session)  # 刷新 session 对象，确保后续查询能获取最新值

    logger.info(
        f"场中判断：user_id={user_id}, session_id={session.id}, "
        f"guess={user_guess}, turn={mid_game_turn}, "
        f"meta_count={mid_game_meta_count}, "
        f"correct={breakdown.is_correct}, score={final_score}"
    )

    # 注意：场中判断后不向用户显示结果，结果在最终问卷提交时才揭晓
    # 仅发送确认消息，告知前端场中判断已成功提交
    await manager.send_personal_message(user_id, {
        "type": "mid_game_submitted",
        "data": {
            "session_id": session.id,
            "turn": mid_game_turn,
            "meta_count": mid_game_meta_count,
            "message": "场中判断已记录，结果将在最终问卷提交时揭晓",
        }
    })


async def handle_end_session(
    user_id: int,
    session: "Session",
    db: AsyncSession,
    end_reason: str = "user_gave_up",
):
    """
    处理结束会话（支持真人对战同步）

    注意：此函数仅标记会话结束，不进行积分结算。
    积分结算需在问卷提交时进行。

    Args:
        user_id: 用户 ID
        session: 会话对象
        db: 数据库会话
        end_reason: 结束原因
            - "user_normal_end": 用户已完成判断后正常结束
            - "user_gave_up": 用户放弃（未判断主动结束）
            - "sys_timeout": 系统超时
    """
    from turing_test.backend.models import User
    from turing_test.backend.websocket.manager import manager

    # 1. 设置结束时间和原因
    session.ended_at = datetime.now(timezone.utc)
    session.end_reason = end_reason

    # 2. 如果是真人对战，通知对方（对方是后离开的一方）
    if session.opponent_session_id and session.opponent_user_id:
        # 获取对方会话
        opponent_result = await db.execute(
            select(Session).where(Session.id == session.opponent_session_id)
        )
        opponent_session = opponent_result.scalar_one_or_none()
        
        if opponent_session and not opponent_session.ended_at:
            # 标记对方会话的"先离开一方"时间（当前用户是先离开者）
            opponent_session.first_left_at = datetime.now(timezone.utc)
            opponent_session.first_leaver_notified = True
            
            # 通过 WebSocket 通知对方
            await manager.send_personal_message(session.opponent_user_id, {
                "type": "opponent_ended",
                "data": {
                    "session_id": opponent_session.id,
                    "opponent_session_id": session.id,
                    "message": "对方已结束对话，您可以继续停留 10 秒后填写问卷，或立即结束",
                    "can_continue_seconds": 10,
                }
            })
            logger.info(
                f"通知对方离开：user_id={session.opponent_user_id}, "
                f"session_id={opponent_session.id}"
            )

    # 3. 提交事务
    await db.commit()

    logger.info(
        f"会话结束：user_id={user_id}, session_id={session.id}, "
        f"reason={end_reason}"
    )

    # 4. 发送通知给主动结束方（告知可以跳转问卷）
    await manager.send_personal_message(user_id, {
        "type": "session_ended",
        "data": {
            "session_id": session.id,
            "end_reason": end_reason,
            "turn_count": session.turn_count,
            "redirect_to_survey": True,  # 主动结束方直接跳转
            "message": "会话已结束，请提交问卷以结算积分",
        }
    })
