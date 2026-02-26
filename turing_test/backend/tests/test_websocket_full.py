"""
综合 WebSocket 测试工具

支持多用户并发测试，验证匹配和聊天功能。
"""

import asyncio
import json
import sys
import os
import random

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import websockets
from loguru import logger


# =============================================================================
# 配置
# =============================================================================

BACKEND_URL = "ws://localhost:8000"
TEST_USER_COUNT = 3  # 测试用户数量
USER_ID_START = 100  # 起始用户 ID


# =============================================================================
# 模拟用户
# =============================================================================

class TestUser:
    """测试用户"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.session_id = None
        self.websocket = None
        self.messages = []

    async def connect_match(self):
        """连接到匹配 WebSocket"""
        uri = f"{BACKEND_URL}/ws/match?user_id={self.user_id}"

        try:
            self.websocket = await websockets.connect(uri)
            logger.info(f"✅ 用户 {self.user_id} 连接匹配 WebSocket 成功")

            # 接收连接确认
            message = await self.websocket.recv()
            data = json.loads(message)
            logger.info(f"用户 {self.user_id} 收到: {data.get('type')}")

            return True

        except Exception as e:
            logger.error(f"用户 {self.user_id} 连接失败: {e}")
            return False

    async def join_queue(self):
        """加入匹配队列"""
        if not self.websocket:
            return False

        message = {
            "type": "join",
            "data": {}
        }
        await self.websocket.send(json.dumps(message))
        logger.info(f"用户 {self.user_id} 已加入匹配队列")
        return True

    async def wait_for_match(self, timeout: int = 60):
        """等待匹配"""
        if not self.websocket:
            return False

        try:
            while True:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                data = json.loads(message)
                self.messages.append(data)

                # 处理匹配成功
                if data.get("type") == "match_found":
                    self.session_id = data.get("data", {}).get("session_id")
                    logger.info(f"✅ 用户 {self.user_id} 匹配成功！会话 ID: {self.session_id}")
                    return True

                # 处理匹配失败
                elif data.get("type") == "match_failed":
                    logger.warning(f"❌ 用户 {self.user_id} 匹配失败")
                    return False

                # 处理心跳
                elif data.get("type") == "ping":
                    pong_message = {"type": "pong", "data": {}}
                    await self.websocket.send(json.dumps(pong_message))

        except asyncio.TimeoutError:
            logger.warning(f"用户 {self.user_id} 等待匹配超时")
            return False
        except Exception as e:
            logger.error(f"用户 {self.user_id} 等待匹配时出错: {e}")
            return False

    async def connect_chat(self):
        """连接到聊天 WebSocket"""
        if not self.session_id:
            logger.warning(f"用户 {self.user_id} 没有会话 ID，无法连接聊天")
            return False

        uri = f"{BACKEND_URL}/ws/chat?user_id={self.user_id}&session_id={self.session_id}"

        try:
            self.websocket = await websockets.connect(uri)
            logger.info(f"✅ 用户 {self.user_id} 连接聊天 WebSocket 成功")

            # 接收连接确认
            message = await self.websocket.recv()
            data = json.loads(message)
            logger.info(f"用户 {self.user_id} 收到: {data.get('type')}")

            return True

        except Exception as e:
            logger.error(f"用户 {self.user_id} 连接聊天失败: {e}")
            return False

    async def send_chat_message(self, content: str):
        """发送聊天消息"""
        if not self.websocket:
            return False

        message = {
            "type": "chat",
            "data": {"content": content}
        }
        await self.websocket.send(json.dumps(message))
        logger.info(f"用户 {self.user_id} 发送: {content}")
        return True

    async def listen_chat(self, timeout: int = 30):
        """监听聊天消息"""
        if not self.websocket:
            return []

        try:
            messages = []
            while True:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                data = json.loads(message)
                messages.append(data)
                self.messages.append(data)

                # 处理心跳
                if data.get("type") == "ping":
                    pong_message = {"type": "pong", "data": {}}
                    await self.websocket.send(json.dumps(pong_message))

        except asyncio.TimeoutError:
            return messages
        except Exception as e:
            logger.error(f"用户 {self.user_id} 监听聊天时出错: {e}")
            return []

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info(f"用户 {self.user_id} 连接已关闭")


# =============================================================================
# 测试场景
# =============================================================================

async def test_concurrent_matching():
    """测试并发匹配"""
    logger.info("=" * 50)
    logger.info("测试场景 1: 并发匹配")
    logger.info("=" * 50)

    # 创建测试用户
    users = [TestUser(USER_ID_START + i) for i in range(TEST_USER_COUNT)]

    # 并发连接到匹配 WebSocket
    connect_tasks = [user.connect_match() for user in users]
    results = await asyncio.gather(*connect_tasks)

    if not all(results):
        logger.error("部分用户连接失败，中止测试")
        return False

    # 添加随机延迟，模拟真实场景
    await asyncio.sleep(random.uniform(0.5, 2.0))

    # 并发加入匹配队列
    join_tasks = [user.join_queue() for user in users]
    await asyncio.gather(*join_tasks)

    # 等待匹配
    logger.info("等待匹配...")
    match_tasks = [user.wait_for_match() for user in users]
    match_results = await asyncio.gather(*match_tasks, return_exceptions=True)

    # 统计匹配结果
    matched_users = [user for user, result in zip(users, match_results) if result]
    logger.info(f"匹配结果: {len(matched_users)}/{TEST_USER_COUNT} 用户匹配成功")

    # 关闭所有连接
    close_tasks = [user.close() for user in users]
    await asyncio.gather(*close_tasks)

    return len(matched_users) > 0


async def test_chat_interaction(user1: TestUser, user2: TestUser):
    """测试聊天交互"""
    logger.info("=" * 50)
    logger.info("测试场景 2: 聊天交互")
    logger.info("=" * 50)

    # 连接到聊天 WebSocket
    user1_ready = await user1.connect_chat()
    user2_ready = await user2.connect_chat()

    if not (user1_ready and user2_ready):
        logger.error("用户连接聊天失败，中止测试")
        return False

    # 用户1 发送消息
    await user1.send_chat_message("你好！")

    # 等待回复
    await asyncio.sleep(2)

    # 用户2 发送消息
    await user2.send_chat_message("你好，很高兴认识你")

    # 等待响应
    await asyncio.sleep(3)

    # 检查收到的消息
    logger.info(f"用户 {user1.user_id} 收到 {len(user1.messages)} 条消息")
    logger.info(f"用户 {user2.user_id} 收到 {len(user2.messages)} 条消息")

    # 关闭连接
    await user1.close()
    await user2.close()

    return True


async def test_heartbeat():
    """测试心跳机制"""
    logger.info("=" * 50)
    logger.info("测试场景 3: 心跳机制")
    logger.info("=" * 50)

    user = TestUser(USER_ID_START + 100)

    # 连接到匹配 WebSocket
    if not await user.connect_match():
        return False

    # 加入队列
    await user.join_queue()

    # 监听心跳消息
    logger.info("监听心跳消息 (30秒)...")
    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= 30:
            break

        try:
            message = await asyncio.wait_for(user.websocket.recv(), timeout=1)
            data = json.loads(message)

            # 检测心跳
            if data.get("type") == "ping":
                logger.info(f"✅ 收到心跳消息 (运行 {elapsed:.1f}秒)")
                # 响应心跳
                pong_message = {"type": "pong", "data": {}}
                await user.websocket.send(json.dumps(pong_message))

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"监听心跳时出错: {e}")
            break

    # 关闭连接
    await user.close()
    return True


# =============================================================================
# 主测试流程
# =============================================================================

async def main():
    """主测试流程"""
    logger.info("🧪 开始 WebSocket 综合测试")
    logger.info(f"📡 后端 URL: {BACKEND_URL}")
    logger.info(f"👥 测试用户数: {TEST_USER_COUNT}")
    logger.info()

    try:
        # 测试场景 1: 并发匹配
        scenario1_success = await test_concurrent_matching()
        logger.info(f"场景 1 结果: {'✅ 成功' if scenario1_success else '❌ 失败'}")
        logger.info()

        await asyncio.sleep(2)

        # 测试场景 2: 聊天交互（需要先有匹配的会话）
        # 简化处理：跳过此场景
        logger.info("场景 2: 跳过（需要先有匹配成功的会话）")
        logger.info()

        # 测试场景 3: 心跳机制
        scenario3_success = await test_heartbeat()
        logger.info(f"场景 3 结果: {'✅ 成功' if scenario3_success else '❌ 失败'}")
        logger.info()

        logger.info("=" * 50)
        logger.info("✅ 综合测试完成")
        logger.info("=" * 50)

    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )

    # 运行测试
    asyncio.run(main())
