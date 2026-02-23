"""
WebSocket 测试工具

用于测试匹配和聊天 WebSocket 功能。
"""

import asyncio
import json
import sys
import os

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import websockets
from loguru import logger


# =============================================================================
# 配置
# =============================================================================

BACKEND_URL = "ws://localhost:8000"
TEST_USER_ID = 1  # 测试用户 ID


# =============================================================================
# 匹配 WebSocket 测试
# =============================================================================

async def test_match_websocket():
    """测试匹配 WebSocket"""
    logger.info("=" * 50)
    logger.info("测试匹配 WebSocket")
    logger.info("=" * 50)

    uri = f"{BACKEND_URL}/ws/match?user_id={TEST_USER_ID}"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"✅ 连接成功: {uri}")

            # 接收连接确认
            message = await websocket.recv()
            data = json.loads(message)
            logger.info(f"收到消息: {data}")

            # 发送加入队列请求
            join_message = {
                "type": "join",
                "data": {}
            }
            await websocket.send(json.dumps(join_message))
            logger.info("已发送加入队列请求")

            # 监听消息
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60)
                    data = json.loads(message)
                    logger.info(f"收到消息: {data}")

                    # 如果匹配成功，退出循环
                    if data.get("type") == "match_found":
                        session_id = data.get("data", {}).get("session_id")
                        logger.info(f"✅ 匹配成功！会话 ID: {session_id}")
                        return session_id

                    # 如果匹配失败，退出循环
                    elif data.get("type") == "match_failed":
                        logger.warning(f"❌ 匹配失败: {data.get('data', {}).get('message')}")
                        return None

                except asyncio.TimeoutError:
                    logger.warning("等待消息超时")
                    break

    except Exception as e:
        logger.error(f"匹配 WebSocket 测试失败: {e}", exc_info=True)
        return None


# =============================================================================
# 聊天 WebSocket 测试
# =============================================================================

async def test_chat_websocket(session_id: int):
    """测试聊天 WebSocket"""
    logger.info("=" * 50)
    logger.info("测试聊天 WebSocket")
    logger.info("=" * 50)

    uri = f"{BACKEND_URL}/ws/chat?user_id={TEST_USER_ID}&session_id={session_id}"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"✅ 连接成功: {uri}")

            # 接收连接确认
            message = await websocket.recv()
            data = json.loads(message)
            logger.info(f"收到消息: {data}")

            # 发送测试消息
            test_message = {
                "type": "chat",
                "data": {
                    "content": "你好，我是测试用户"
                }
            }
            await websocket.send(json.dumps(test_message))
            logger.info("已发送测试消息")

            # 监听消息
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(message)
                    logger.info(f"收到消息: {data}")

                    # 收到对手回复，发送场中判断
                    if data.get("type") == "chat" and data.get("data", {}).get("sender") == "opponent":
                        logger.info("收到对手回复，发送场中判断")

                        judgment_message = {
                            "type": "mid_game_judgment",
                            "data": {
                                "user_guess": "ai"
                            }
                        }
                        await websocket.send(json.dumps(judgment_message))
                        logger.info("已发送场中判断")

                    # 如果收到场中判断结果，退出循环
                    elif data.get("type") == "mid_game_result":
                        logger.info(f"✅ 场中判断结果: {data}")
                        break

                    # 处理心跳
                    elif data.get("type") == "ping":
                        pong_message = {
                            "type": "pong",
                            "data": {}
                        }
                        await websocket.send(json.dumps(pong_message))
                        logger.debug("已发送心跳响应")

                except asyncio.TimeoutError:
                    logger.warning("等待消息超时")
                    break

    except Exception as e:
        logger.error(f"聊天 WebSocket 测试失败: {e}", exc_info=True)


# =============================================================================
# 主测试流程
# =============================================================================

async def main():
    """主测试流程"""
    logger.info("🧪 开始 WebSocket 测试")
    logger.info(f"📡 后端 URL: {BACKEND_URL}")
    logger.info(f"👤 测试用户 ID: {TEST_USER_ID}")
    logger.info()

    try:
        # 测试匹配 WebSocket
        session_id = await test_match_websocket()

        if session_id:
            # 测试聊天 WebSocket
            await test_chat_websocket(session_id)
        else:
            logger.warning("⚠️  未获取到会话 ID，跳过聊天测试")

        logger.info()
        logger.info("=" * 50)
        logger.info("✅ 测试完成")
        logger.info("=" * 50)

    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 配置日志
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )

    # 运行测试
    asyncio.run(main())
