"""
WebSocket 连接管理器（改进版）

管理所有活跃的 WebSocket 连接，支持心跳机制和连接统计。
"""

from typing import Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
import json
import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict


class ConnectionState:
    """连接状态"""

    def __init__(self, websocket: WebSocket, user_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        self.session_id: Optional[int] = None
        self.is_alive = True

    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.now(timezone.utc)

    def is_stale(self, timeout_seconds: int = 60) -> bool:
        """检查连接是否过期"""
        elapsed = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
        return elapsed > timeout_seconds


class ConnectionManager:
    """WebSocket 连接管理器（改进版）"""

    def __init__(
        self,
        heartbeat_interval: int = 30,  # 心跳间隔（秒）
        heartbeat_timeout: int = 90,    # 心跳超时（秒）= 3 次心跳间隔
    ):
        # 用户 ID 到连接状态的映射
        self.active_connections: Dict[int, ConnectionState] = {}

        # 会话 ID 到用户 ID 列表的映射
        self.session_users: Dict[int, Set[int]] = {}

        # 连接统计
        self.total_connections = 0
        self.total_disconnections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.heartbeat_sent_count = 0
        self.heartbeat_timeout_count = 0

        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = heartbeat_interval  # 心跳间隔（秒）
        self._heartbeat_timeout = heartbeat_timeout    # 心跳超时（秒）

        # 用户断开连接标志
        self._disconnecting_users: Set[int] = set()

        # 速率限制：IP -> 连接时间戳列表
        self._connection_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._rate_limit_window = 60  # 时间窗口（秒）
        self._rate_limit_max = 10     # 每个窗口内最大连接数

    async def start_heartbeat_monitor(self):
        """启动心跳监控任务"""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("❤️ 心跳监控任务已启动")

    async def stop_heartbeat_monitor(self):
        """停止心跳监控任务"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                # 等待任务完成取消，设置超时避免无限等待
                await asyncio.wait_for(self._heartbeat_task, timeout=5.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning("⚠️ 心跳监控任务取消超时")
            self._heartbeat_task = None
            logger.info("❤️ 心跳监控任务已停止")

    async def _heartbeat_loop(self):
        """心跳监控循环"""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                # 检查过期连接（使用 list() 创建快照，避免迭代过程中字典被修改）
                stale_connections = [
                    user_id
                    for user_id, conn in list(self.active_connections.items())
                    if conn.is_stale(self._heartbeat_timeout)
                ]

                for user_id in stale_connections:
                    logger.warning(f"用户 {user_id} 心跳超时，强制断开")
                    self.heartbeat_timeout_count += 1
                    await self.disconnect(user_id)

                # 向所有活跃连接发送心跳（使用 list() 创建快照）
                for user_id, conn in list(self.active_connections.items()):
                    try:
                        if conn.websocket is None:
                            logger.warning(f"用户 {user_id} 的 websocket 为 None，跳过心跳")
                            continue
                        await conn.websocket.send_json({
                            "type": "ping",
                            "data": {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        })
                        self.heartbeat_sent_count += 1
                    except Exception as e:
                        logger.error(f"发送心跳给用户 {user_id} 失败：{e}")
                        await self.disconnect(user_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳监控错误：{e}", exc_info=True)

    async def connect(self, user_id: int, websocket: WebSocket):
        """
        连接用户（带速率限制）

        Args:
            user_id: 用户 ID
            websocket: WebSocket 连接

        Raises:
            WebSocketDisconnect: 如果触发速率限制
        """
        # 获取客户端 IP
        client_ip = websocket.client.host if websocket.client else "unknown"

        # 检查速率限制
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self._rate_limit_window)

        # 清理过期记录
        self._connection_attempts[client_ip] = [
            t for t in self._connection_attempts[client_ip]
            if t > window_start
        ]

        # 检查是否超出限制
        if len(self._connection_attempts[client_ip]) >= self._rate_limit_max:
            logger.warning(f"速率限制：IP {client_ip} 在 {self._rate_limit_window}秒内连接超过{self._rate_limit_max}次")
            await websocket.close(code=429, reason="连接过于频繁，请稍后再试")
            return

        # 记录本次连接
        self._connection_attempts[client_ip].append(now)

        try:
            await websocket.accept()

            # 创建连接状态
            connection = ConnectionState(websocket, user_id)
            self.active_connections[user_id] = connection

            # 更新统计
            self.total_connections += 1

            logger.info(f"✅ 用户 {user_id} 已连接 (总连接数：{len(self.active_connections)})")

            # 发送连接确认消息
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "user_id": user_id,
                    "connected_at": connection.connected_at.isoformat(),
                }
            })

        except Exception as e:
            logger.error(f"用户 {user_id} 连接失败：{e}", exc_info=True)
            raise

    def disconnect(self, user_id: int):
        """断开用户连接"""
        if user_id in self._disconnecting_users:
            # 已经在断开中，避免重复处理
            return
            
        # 标记为用户正在断开，防止重入
        self._disconnecting_users.add(user_id)
        
        try:
            if user_id in self.active_connections:
                connection = self.active_connections[user_id]
                connection.is_alive = False

                # 清理会话关联
                if connection.session_id is not None:
                    self._remove_user_from_session(user_id, connection.session_id)

                del self.active_connections[user_id]
                self.total_disconnections += 1

                logger.info(
                    f"❌ 用户 {user_id} 已断开连接 "
                    f"(总连接数：{len(self.active_connections)}, "
                    f"连接时长：{(datetime.now(timezone.utc) - connection.connected_at).total_seconds():.1f}秒)"
                )
        finally:
            # 移除断开标志
            self._disconnecting_users.discard(user_id)

    async def send_personal_message(self, user_id: int, message: dict):
        """发送个人消息"""
        if user_id in self._disconnecting_users:
            # 用户正在断开连接，不再发送消息
            logger.debug(f"send_personal_message: 用户 {user_id} 正在断开连接，跳过")
            return False

        if user_id not in self.active_connections:
            logger.warning(f"用户 {user_id} 不在线，无法发送消息")
            return False

        connection = self.active_connections[user_id]
        if not connection.is_alive:
            logger.warning(f"用户 {user_id} 连接已失效")
            return False

        try:
            await connection.websocket.send_json(message)
            self.total_messages_sent += 1
            logger.debug(f"send_personal_message: 用户 {user_id} 发送成功，type={message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"发送消息给用户 {user_id} 失败：{e}")
            await self.disconnect(user_id)
            return False

    async def broadcast(self, message: dict, exclude: Optional[List[int]] = None):
        """广播消息"""
        if exclude is None:
            exclude = []

        sent_count = 0
        failed_count = 0

        for user_id, connection in list(self.active_connections.items()):
            if user_id not in exclude and connection.is_alive:
                try:
                    await connection.websocket.send_json(message)
                    self.total_messages_sent += 1
                    sent_count += 1
                except Exception as e:
                    logger.error(f"广播消息给用户 {user_id} 失败：{e}")
                    await self.disconnect(user_id)
                    failed_count += 1

        if failed_count > 0:
            logger.warning(f"广播完成：发送 {sent_count}, 失败 {failed_count}")

        return sent_count

    async def send_to_session(self, session_id: int, message: dict):
        """发送消息到会话中的用户"""
        if session_id not in self.session_users:
            logger.warning(f"会话 {session_id} 没有关联的用户")
            return 0

        sent_count = 0
        for user_id in list(self.session_users[session_id]):
            success = await self.send_personal_message(user_id, message)
            if success:
                sent_count += 1
        
        logger.debug(f"send_to_session: session_id={session_id}, users={list(self.session_users[session_id])}, sent_count={sent_count}")
        return sent_count

    def set_user_session(self, user_id: int, session_id: int):
        """设置用户的会话关联"""
        if user_id not in self.active_connections:
            logger.warning(f"用户 {user_id} 未连接，无法设置会话")
            return False

        connection = self.active_connections[user_id]
        connection.session_id = session_id

        if session_id not in self.session_users:
            self.session_users[session_id] = set()

        self.session_users[session_id].add(user_id)
        logger.info(f"用户 {user_id} 关联到会话 {session_id}")
        return True

    def _remove_user_from_session(self, user_id: int, session_id: int):
        """从会话中移除用户"""
        if session_id in self.session_users:
            self.session_users[session_id].discard(user_id)
            if not self.session_users[session_id]:
                del self.session_users[session_id]
                logger.info(f"会话 {session_id} 没有用户，已清理")

    def is_user_connected(self, user_id: int) -> bool:
        """检查用户是否在线"""
        # 如果用户正在断开连接中，视为未连接
        if user_id in self._disconnecting_users:
            return False
        connection = self.active_connections.get(user_id)
        return connection is not None and connection.is_alive

    def get_user_websocket(self, user_id: int) -> Optional[WebSocket]:
        """获取用户的 WebSocket 连接"""
        connection = self.active_connections.get(user_id)
        return connection.websocket if connection else None

    def get_online_count(self) -> int:
        """获取在线用户数"""
        return len(self.active_connections)

    def get_session_online_count(self, session_id: int) -> int:
        """获取会话中的在线用户数"""
        if session_id not in self.session_users:
            return 0
        return len(self.session_users[session_id])

    def get_user_session_id(self, user_id: int) -> Optional[int]:
        """获取用户当前会话 ID"""
        connection = self.active_connections.get(user_id)
        return connection.session_id if connection else None

    def get_connection_info(self, user_id: int) -> Optional[dict]:
        """获取用户连接信息"""
        connection = self.active_connections.get(user_id)
        if connection is None:
            return None

        return {
            "user_id": connection.user_id,
            "session_id": connection.session_id,
            "connected_at": connection.connected_at.isoformat(),
            "last_heartbeat": connection.last_heartbeat.isoformat(),
            "is_alive": connection.is_alive,
        }

    def get_statistics(self) -> dict:
        """获取连接统计"""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "active_sessions": len(self.session_users),
            "heartbeat_sent_count": self.heartbeat_sent_count,
            "heartbeat_timeout_count": self.heartbeat_timeout_count,
        }

    async def handle_message(self, user_id: int, message: dict):
        """处理收到的消息"""
        self.total_messages_received += 1

        # 处理心跳响应
        if message.get("type") == "pong":
            connection = self.active_connections.get(user_id)
            if connection:
                connection.update_heartbeat()
            return

        # 其他消息类型由各自的处理函数处理
        pass


# 全局连接管理器实例（可配置心跳参数）
# heartbeat_interval: 心跳间隔（秒），默认 30 秒
# heartbeat_timeout: 心跳超时（秒），默认 90 秒（3 次心跳间隔）
manager = ConnectionManager(heartbeat_interval=30, heartbeat_timeout=90)
