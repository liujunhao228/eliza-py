import asyncio
import json
import random
from datetime import datetime
from typing import Dict, Optional
from fastapi import WebSocket
from sqlalchemy.orm import Session
from models import Session as SessionModel, Message, User
from ai_bot import get_bot_response


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # user_id -> WebSocket 连接
        self.active_connections: Dict[int, WebSocket] = {}
        # session_id -> 两个用户的 user_id
        self.session_users: Dict[int, list[int]] = {}
        # user_id -> session_id
        self.user_sessions: Dict[int, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        """断开 WebSocket 连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # 清理会话映射
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            if session_id in self.session_users:
                self.session_users[session_id].remove(user_id)
            del self.user_sessions[user_id]
    
    async def send_personal_message(self, user_id: int, message: dict):
        """向特定用户发送消息"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
    
    async def broadcast_to_session(self, session_id: int, message: dict):
        """向会话中的所有用户发送消息"""
        if session_id in self.session_users:
            for user_id in self.session_users[session_id]:
                await self.send_personal_message(user_id, message)
    
    def register_session(self, session_id: int, user_id: int, opponent_id: Optional[int] = None):
        """注册会话"""
        self.user_sessions[user_id] = session_id
        users = [user_id]
        if opponent_id:
            users.append(opponent_id)
            self.user_sessions[opponent_id] = session_id
        self.session_users[session_id] = users
    
    def get_user_session(self, user_id: int) -> Optional[int]:
        """获取用户当前的会话 ID"""
        return self.user_sessions.get(user_id)
    
    def get_connection(self, user_id: int) -> Optional[WebSocket]:
        """获取用户的 WebSocket 连接"""
        return self.active_connections.get(user_id)


# 全局连接管理器
manager = ConnectionManager()


async def handle_chat_message(
    user_id: int,
    content: str,
    db: Session
) -> Optional[dict]:
    """
    处理聊天消息
    
    Returns:
        消息记录 dict，如果是 AI 回复则返回 AI 的消息
    """
    session_id = manager.get_user_session(user_id)
    if not session_id:
        return None
    
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return None
    
    # 保存用户消息
    user_message = Message(
        session_id=session_id,
        sender_id=user_id,
        is_ai=False,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(user_message)
    db.commit()
    
    user_msg_dict = {
        "type": "message",
        "data": {
            "id": user_message.id,
            "session_id": session_id,
            "sender_id": user_id,
            "is_ai": False,
            "content": content,
            "created_at": user_message.created_at.isoformat()
        }
    }
    
    # 广播给会话中的其他人
    await manager.broadcast_to_session(session_id, user_msg_dict)
    
    # 如果是 AI 对手，生成回复
    if session.opponent_type == 'ai':
        # 先等待打字延迟（模拟 AI 思考和输入）
        ai_response, delay = get_bot_response(content)
        await asyncio.sleep(delay)

        # 推送"正在输入"状态，增加真实感
        await manager.broadcast_to_session(session_id, {
            "type": "typing",
            "user_id": None  # None 表示 AI
        })

        # 短暂延迟后发送消息（模拟输入完成）
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # 保存 AI 消息
        ai_message = Message(
            session_id=session_id,
            sender_id=None,
            is_ai=True,
            content=ai_response,
            created_at=datetime.utcnow()
        )
        db.add(ai_message)
        db.commit()

        # 发送"停止输入"状态
        await manager.broadcast_to_session(session_id, {
            "type": "stop_typing",
            "user_id": None
        })

        ai_msg_dict = {
            "type": "message",
            "data": {
                "id": ai_message.id,
                "session_id": session_id,
                "sender_id": None,
                "is_ai": True,
                "content": ai_response,
                "created_at": ai_message.created_at.isoformat()
            }
        }

        # 发送 AI 回复
        await manager.broadcast_to_session(session_id, ai_msg_dict)

        return ai_msg_dict
    
    return user_msg_dict


async def handle_human_message(
    sender_id: int,
    content: str,
    db: Session
) -> dict:
    """
    处理真人之间的消息转发
    
    Returns:
        消息记录 dict
    """
    session_id = manager.get_user_session(sender_id)
    if not session_id:
        return {}
    
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session or session.opponent_type != 'human':
        return {}
    
    # 保存消息
    message = Message(
        session_id=session_id,
        sender_id=sender_id,
        is_ai=False,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    
    msg_dict = {
        "type": "message",
        "data": {
            "id": message.id,
            "session_id": session_id,
            "sender_id": sender_id,
            "is_ai": False,
            "content": content,
            "created_at": message.created_at.isoformat()
        }
    }
    
    # 转发给会话中的其他人
    await manager.broadcast_to_session(session_id, msg_dict)
    
    return msg_dict
