"""
WebSocket 连接诊断工具

用于测试前后端 WebSocket 连接的完整性，包括：
1. 连接建立测试
2. 心跳检测测试
3. 消息收发测试
4. 断线重连测试
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import websockets
from loguru import logger


# =============================================================================
# 配置
# =============================================================================

BACKEND_URL = "ws://localhost:8000"
TEST_USER_ID = 9999


# =============================================================================
# 诊断测试类
# =============================================================================

class WebSocketDiagnostic:
    """WebSocket 连接诊断工具"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.websocket = None
        self.messages_received = []
        self.connection_start_time = None
        self.test_results = {
            "connection": False,
            "heartbeat": False,
            "message_send": False,
            "message_receive": False,
            "reconnect": False,
        }

    async def connect_match(self, timeout: int = 10) -> bool:
        """测试连接建立"""
        logger.info("=" * 60)
        logger.info(f"测试 1: 连接建立 (用户 ID: {self.user_id})")
        logger.info("=" * 60)

        uri = f"{BACKEND_URL}/ws/match?user_id={self.user_id}"
        self.connection_start_time = time.time()

        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(uri),
                timeout=timeout
            )
            logger.info(f"✅ 连接建立成功 (耗时：{time.time() - self.connection_start_time:.2f}s)")

            # 接收连接确认消息
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
            data = json.loads(message)
            logger.info(f"📥 收到连接确认：type={data.get('type')}")

            if data.get("type") == "connected":
                self.test_results["connection"] = True
                logger.info("✅ 连接测试通过")
                return True
            else:
                logger.warning(f"⚠️ 收到意外消息类型：{data.get('type')}")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ 连接超时")
            self.test_results["connection"] = False
            return False
        except Exception as e:
            logger.error(f"❌ 连接失败：{e}")
            self.test_results["connection"] = False
            return False

    async def test_heartbeat(self, timeout: int = 35) -> bool:
        """测试心跳机制"""
        logger.info("=" * 60)
        logger.info("测试 2: 心跳检测")
        logger.info("=" * 60)

        if not self.websocket:
            logger.error("❌ WebSocket 未连接")
            return False

        try:
            logger.info(f"⏳ 等待心跳消息 (最多 {timeout} 秒，后端心跳间隔 30 秒)...")
            logger.info("💡 提示：后端心跳监控在启动后 30 秒才发送第一次心跳")
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=2)
                    data = json.loads(message)
                    self.messages_received.append(data)
                    logger.info(f"📥 收到消息：type={data.get('type')}")

                    if data.get("type") == "ping":
                        elapsed = time.time() - start_time
                        logger.info(f"✅ 收到心跳消息 (耗时：{elapsed:.2f}s)")

                        # 响应心跳
                        pong_message = {"type": "pong", "data": {}}
                        await self.websocket.send(json.dumps(pong_message))
                        logger.info("📤 已发送心跳响应")

                        self.test_results["heartbeat"] = True
                        logger.info("✅ 心跳测试通过")
                        return True

                except asyncio.TimeoutError:
                    # 超时继续等待
                    continue

            logger.warning("⚠️ 等待心跳超时")
            logger.warning("💡 可能原因：后端心跳监控未启动，或等待时间不足 30 秒")
            self.test_results["heartbeat"] = False
            return False

        except Exception as e:
            logger.error(f"❌ 心跳测试失败：{e}")
            self.test_results["heartbeat"] = False
            return False

    async def test_join_queue(self) -> bool:
        """测试加入队列"""
        logger.info("=" * 60)
        logger.info("测试 3: 加入匹配队列")
        logger.info("=" * 60)

        if not self.websocket:
            logger.error("❌ WebSocket 未连接")
            return False

        try:
            # 发送 join 消息（与前端保持一致的格式）
            join_message = {"type": "join", "data": {}}
            await self.websocket.send(json.dumps(join_message))
            logger.info("📤 已发送加入队列消息：", json.dumps(join_message))

            # 等待响应（可能是 status 或 error）
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
            data = json.loads(message)
            self.messages_received.append(data)

            logger.info(f"📥 收到响应：type={data.get('type')}")

            # 接受 status 或 connected 作为成功响应
            if data.get("type") in ["status", "connected"]:
                self.test_results["message_send"] = True
                logger.info("✅ 消息发送测试通过")
                return True
            # 如果是 error，记录详细信息
            elif data.get("type") == "error":
                logger.warning(f"⚠️ 收到错误：{data.get('data', {}).get('message')}")
                # 仍然认为消息发送成功，只是业务逻辑可能有误
                self.test_results["message_send"] = True
                return True
            else:
                logger.warning(f"⚠️ 收到意外消息类型：{data.get('type')}")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ 等待响应超时")
            self.test_results["message_send"] = False
            return False
        except Exception as e:
            logger.error(f"❌ 加入队列失败：{e}")
            self.test_results["message_send"] = False
            return False

    async def test_reconnect(self) -> bool:
        """测试断线重连"""
        logger.info("=" * 60)
        logger.info("测试 4: 断线重连")
        logger.info("=" * 60)

        if not self.websocket:
            logger.error("❌ WebSocket 未连接")
            return False

        try:
            # 关闭当前连接
            await self.websocket.close()
            logger.info("🔌 已关闭连接")

            await asyncio.sleep(2)

            # 重新连接
            logger.info("🔄 尝试重新连接...")
            self.websocket = None
            success = await self.connect_match(timeout=10)

            if success:
                self.test_results["reconnect"] = True
                logger.info("✅ 重连测试通过")
                return True
            else:
                logger.warning("⚠️ 重连失败")
                return False

        except Exception as e:
            logger.error(f"❌ 重连测试失败：{e}")
            self.test_results["reconnect"] = False
            return False

    async def run_all_tests(self):
        """运行所有诊断测试"""
        logger.info("\n")
        logger.info("╔" + "═" * 58 + "╗")
        logger.info("║" + " " * 15 + "WebSocket 连接诊断工具" + " " * 15 + "║")
        logger.info("╚" + "═" * 58 + "╝")
        logger.info("")

        # 测试 1: 连接建立
        await self.connect_match()
        await asyncio.sleep(1)

        # 测试 2: 心跳检测
        await self.test_heartbeat()
        await asyncio.sleep(1)

        # 测试 3: 加入队列
        await self.test_join_queue()
        await asyncio.sleep(1)

        # 测试 4: 断线重连
        await self.test_reconnect()

        # 输出测试结果
        self.print_summary()

        # 清理资源
        await self.cleanup()

    def print_summary(self):
        """打印测试摘要"""
        logger.info("\n")
        logger.info("=" * 60)
        logger.info("测试摘要")
        logger.info("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for v in self.test_results.values() if v)

        for test_name, passed in self.test_results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            logger.info(f"  {test_name}: {status}")

        logger.info("")
        logger.info(f"总计：{passed_tests}/{total_tests} 测试通过")

        if passed_tests == total_tests:
            logger.info("🎉 所有测试通过！")
        else:
            logger.warning("⚠️ 部分测试失败，请检查后端服务状态")

        logger.info("=" * 60)

    async def cleanup(self):
        """清理资源"""
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 连接已关闭")


# =============================================================================
# 聊天 WebSocket 诊断
# =============================================================================

class ChatWebSocketDiagnostic(WebSocketDiagnostic):
    """聊天 WebSocket 诊断工具"""

    async def connect_chat(self, session_id: int, timeout: int = 10) -> bool:
        """测试聊天连接建立"""
        logger.info("=" * 60)
        logger.info(f"测试 1: 聊天连接建立 (会话 ID: {session_id})")
        logger.info("=" * 60)

        uri = f"{BACKEND_URL}/ws/chat?session_id={session_id}&user_id={self.user_id}"
        self.connection_start_time = time.time()

        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(uri),
                timeout=timeout
            )
            logger.info(f"✅ 连接建立成功 (耗时：{time.time() - self.connection_start_time:.2f}s)")

            # 接收连接确认消息
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
            data = json.loads(message)
            logger.info(f"📥 收到连接确认：type={data.get('type')}")

            if data.get("type") == "connected":
                self.test_results["connection"] = True
                logger.info("✅ 连接测试通过")
                return True
            else:
                logger.warning(f"⚠️ 收到意外消息类型：{data.get('type')}")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ 连接超时")
            self.test_results["connection"] = False
            return False
        except Exception as e:
            logger.error(f"❌ 连接失败：{e}")
            self.test_results["connection"] = False
            return False

    async def test_chat_message(self) -> bool:
        """测试聊天消息发送"""
        logger.info("=" * 60)
        logger.info("测试：聊天消息发送")
        logger.info("=" * 60)

        if not self.websocket:
            logger.error("❌ WebSocket 未连接")
            return False

        try:
            # 发送聊天消息（使用 'message' 类型，与前端保持一致）
            chat_message = {
                "type": "message",
                "data": {"content": "诊断测试消息"}
            }
            await self.websocket.send(json.dumps(chat_message))
            logger.info("📤 已发送聊天消息")

            # 等待响应
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
            data = json.loads(message)
            self.messages_received.append(data)

            logger.info(f"📥 收到响应：type={data.get('type')}")

            if data.get("type") in ["chat", "message"]:
                self.test_results["message_receive"] = True
                logger.info("✅ 消息接收测试通过")
                return True
            else:
                logger.warning(f"⚠️ 收到意外消息类型：{data.get('type')}")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ 等待响应超时")
            self.test_results["message_receive"] = False
            return False
        except Exception as e:
            logger.error(f"❌ 消息发送失败：{e}")
            self.test_results["message_receive"] = False
            return False

    async def run_chat_tests(self, session_id: int):
        """运行聊天诊断测试"""
        logger.info("\n")
        logger.info("╔" + "═" * 58 + "╗")
        logger.info("║" + " " * 12 + "聊天 WebSocket 诊断工具" + " " * 12 + "║")
        logger.info("╚" + "═" * 58 + "╝")
        logger.info("")

        # 测试 1: 连接建立
        await self.connect_chat(session_id)
        await asyncio.sleep(1)

        # 测试 2: 心跳检测
        await self.test_heartbeat()
        await asyncio.sleep(1)

        # 测试 3: 消息发送
        await self.test_chat_message()

        # 输出测试结果
        self.print_summary()

        # 清理资源
        await self.cleanup()


# =============================================================================
# 主函数
# =============================================================================

async def main():
    """主函数"""
    logger.info("🔧 WebSocket 诊断工具启动")
    logger.info(f"📡 后端地址：{BACKEND_URL}")
    logger.info("")

    # 匹配 WebSocket 诊断
    match_diagnostic = WebSocketDiagnostic(TEST_USER_ID)
    await match_diagnostic.run_all_tests()

    await asyncio.sleep(2)

    # 聊天 WebSocket 诊断（需要有效的 session_id）
    # 注意：这需要一个真实存在的会话 ID
    # chat_diagnostic = ChatWebSocketDiagnostic(TEST_USER_ID)
    # await chat_diagnostic.run_chat_tests(session_id=1)


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )

    # 运行诊断
    asyncio.run(main())
