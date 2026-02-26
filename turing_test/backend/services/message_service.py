"""
消息处理服务

负责：
1. 用户消息处理
2. AI 响应生成
3. Bot 开场白发送
4. 会话状态管理（内存级）
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from turing_test.backend.models import Message
from turing_test.backend.websocket.manager import manager
from turing_test.backend.services.session_state import session_state_manager
from turing_test.backend.services.ai_bot_service import get_bot_response


class MessageService:
    """消息处理服务"""
    
    @staticmethod
    async def handle_user_message(
        session_id: int,
        user_id: int,
        content: str,
        db: AsyncSession,
    ) -> bool:
        """
        处理用户消息
        
        流程：
        1. 获取会话锁
        2. 检查是否为用户回合
        3. 保存消息到数据库
        4. 更新内存状态
        5. 触发 AI 响应（异步）
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            content: 消息内容
            db: 数据库会话
        
        Returns:
            是否处理成功
        """
        # 获取会话锁
        if not await session_state_manager.acquire(session_id):
            logger.warning(f"无法获取会话锁：session_id={session_id}")
            return False
        
        try:
            state = session_state_manager.get(session_id)
            if not state:
                logger.error(f"会话状态不存在：session_id={session_id}")
                return False
            
            # 检查回合
            if not state.is_user_turn:
                await manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "NOT_USER_TURN",
                        "message": "请等待对方发送消息"
                    }
                })
                return False
            
            # 验证内容
            if not content or not content.strip():
                await manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {
                        "error_code": "EMPTY_MESSAGE",
                        "message": "消息不能为空"
                    }
                })
                return False
            
            # 检测元对话
            is_meta, keyword = _detect_meta_conversation(content)
            
            # 保存消息（数据库）
            message = Message(
                session_id=session_id,
                sender="user",
                content=content.strip(),
                is_meta_conversation=is_meta,
                meta_keyword=keyword if is_meta else None,
            )
            db.add(message)
            
            # 更新内存状态
            turn_count, _ = session_state_manager.next_turn(session_id)
            if is_meta:
                state.meta_count += 1
            
            # 异步持久化 turn_count
            asyncio.create_task(_flush_turn_count(session_id, turn_count))
            
            await db.commit()
            await db.refresh(message)
            
            # 转发消息
            await manager.send_to_session(session_id, {
                "type": "chat",
                "data": {
                    "id": message.id,
                    "sender": "user",
                    "content": content.strip(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_meta_conversation": is_meta,
                }
            })
            
            # 触发 AI 响应（后台任务，不阻塞）
            asyncio.create_task(
                MessageService._trigger_ai_response(session_id, content.strip(), db)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"处理用户消息失败：{e}", exc_info=True)
            await db.rollback()
            return False
        finally:
            session_state_manager.release(session_id)
    
    @staticmethod
    async def _trigger_ai_response(
        session_id: int,
        user_message: str,
        db: AsyncSession,
    ):
        """触发 AI 响应（后台任务）"""
        state = session_state_manager.get(session_id)
        if not state:
            return
        
        # 检查在线用户
        session_users = manager.session_users.get(session_id, set())
        if not session_users:
            return
        
        # 发送打字提示
        await manager.send_to_session(session_id, {
            "type": "typing",
            "data": {"sender": "opponent", "is_typing": True}
        })
        
        # 判断是否为开场白后的第一条回复
        is_opening_response = state.turn_count == 1
        
        # 获取 AI 响应
        ai_response = "系统故障，请稍后再试"
        ai_delay = 1.0
        is_meta = False
        
        try:
            base_response, base_delay = await get_bot_response(
                user_message,
                is_opening=is_opening_response,
                is_honeypot=state.is_honeypot,
                session_turn_count=state.turn_count,
            )
            
            ai_response = base_response
            ai_delay = base_delay
            
            # 检测元对话
            is_meta, _ = _detect_meta_conversation(user_message)
            
            if state.is_honeypot:
                from turing_test.backend.services.honeypot_service import get_honeypot_service
                honeypot = get_honeypot_service()
                ai_response, ai_delay = honeypot.get_response_with_delay(
                    base_response=base_response,
                    session_id=session_id,
                    is_meta=is_meta,
                    user_message=user_message,
                    session_turn_count=state.turn_count,
                )
        except Exception as e:
            logger.error(f"获取 AI 响应失败：{e}")
        
        # 等待延迟（模拟打字）
        if ai_delay > 0:
            await asyncio.sleep(ai_delay)
        
        # 停止打字提示
        await manager.send_to_session(session_id, {
            "type": "stop_typing",
            "data": {"sender": "opponent", "is_typing": False}
        })
        
        # 保存 AI 消息
        ai_message = Message(
            session_id=session_id,
            sender="opponent",
            content=ai_response,
            is_meta_conversation=_detect_meta_conversation(ai_response)[0],
        )
        db.add(ai_message)
        
        # 更新内存状态
        turn_count, is_user_turn = session_state_manager.next_turn(session_id)
        asyncio.create_task(_flush_turn_count(session_id, turn_count))
        
        await db.commit()
        await db.refresh(ai_message)
        
        # 发送 AI 响应
        await manager.send_to_session(session_id, {
            "type": "chat",
            "data": {
                "id": ai_message.id,
                "sender": "opponent",
                "content": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_meta_conversation": _detect_meta_conversation(ai_response)[0],
            }
        })
        
        logger.info(
            f"AI 响应已发送：session_id={session_id}, "
            f"message_id={ai_message.id}, turn_count={turn_count}"
        )
    
    @staticmethod
    async def send_opening_message(
        session_id: int,
        user_id: int,
        db: AsyncSession,
    ):
        """
        发送 Bot 开场白
        
        注意：调用前应已完成概率检测和 turn_count 检查
        
        开场白来源：
        - 普通 AI: scripts/opening.yaml
        - 钓鱼机器人：scripts/opening_honeypot.yaml
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            db: 数据库会话
        """
        if not await session_state_manager.acquire(session_id):
            return
        
        try:
            state = session_state_manager.get(session_id)
            if not state:
                return
            
            # 再次检查是否已有消息（双重保护）
            if state.turn_count > 0:
                logger.info(f"会话已有消息，跳过开场白：session_id={session_id}")
                return
            
            # 获取开场白（从 LightweightAliceBot）
            from alice.bots.lightweight_alice_bot import LightweightAliceBot
            from alice.services.shared_nlp_service import SharedNLPService
            
            nlp_service = SharedNLPService()
            script_file = (
                "scripts/opening_honeypot.yaml" if state.is_honeypot 
                else "scripts/opening.yaml"
            )
            
            bot = LightweightAliceBot(
                nlp_service=nlp_service,
                opening_script=script_file,
                use_ltp=False,
            )
            
            opening = bot.get_opening_message()
            if not opening:
                opening = "你好，我是小图。"
            
            # 发送打字提示
            await manager.send_to_session(session_id, {
                "type": "typing",
                "data": {"sender": "opponent", "is_typing": True}
            })
            
            # 等待短暂延迟（主延迟已在匹配服务中等待）
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            await manager.send_to_session(session_id, {
                "type": "stop_typing",
                "data": {"sender": "opponent", "is_typing": False}
            })
            
            # 保存消息
            message = Message(
                session_id=session_id,
                sender="opponent",
                content=opening,
            )
            db.add(message)

            # 更新状态：开场白后轮到用户发言
            # turn_count 设为 1（表示已有 1 条消息），is_user_turn 设为 True
            state.turn_count = 1
            state.is_user_turn = True
            asyncio.create_task(_flush_turn_count(session_id, 1))
            
            await db.commit()
            await db.refresh(message)
            
            # 发送
            await manager.send_to_session(session_id, {
                "type": "chat",
                "data": {
                    "id": message.id,
                    "sender": "opponent",
                    "content": opening,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            })
            
            logger.info(f"开场白已发送：session_id={session_id}, content={opening[:20]}...")
            
        except Exception as e:
            logger.error(f"发送开场白失败：{e}", exc_info=True)
        finally:
            session_state_manager.release(session_id)


async def _flush_turn_count(session_id: int, turn_count: int):
    """异步持久化 turn_count 到数据库"""
    try:
        from turing_test.backend.database import async_session_maker
        from turing_test.backend.models import Session
        from sqlalchemy import update
        
        async with async_session_maker() as db:
            await db.execute(
                update(Session).where(Session.id == session_id)
                .values(turn_count=turn_count)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"持久化 turn_count 失败：{e}")


def _detect_meta_conversation(content: str) -> Tuple[bool, Optional[str]]:
    """
    检测元对话
    
    Args:
        content: 消息内容
        
    Returns:
        (是否为元对话，关键词)
    """
    keywords = ['真人', '机器', 'AI', '机器人', '人工智能', '程序', '算法']
    content_lower = content.lower()
    for kw in keywords:
        if kw in content_lower:
            return True, kw
    return False, None
