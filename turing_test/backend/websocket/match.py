"""
匹配 WebSocket 端点（简化版）

简化逻辑：
- 仅用于连接确认和心跳
- 匹配通过 HTTP API 实现
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger
import json
from datetime import datetime, timezone

from turing_test.backend.websocket.manager import manager

router = APIRouter()


@router.websocket("/match")
async def match_websocket(
    websocket: WebSocket,
    user_id: int = Query(..., description="用户 ID"),
):
    """
    匹配 WebSocket（简化版）

    仅用于：
    - 连接确认
    - 心跳检测

    心跳机制：由后端单向发起 ping，前端响应 pong
    """
    try:
        # 连接用户
        await manager.connect(user_id, websocket)
        logger.info(f"用户 {user_id} 连接到匹配 WebSocket")

        # 发送连接确认
        await manager.send_personal_message(user_id, {
            "type": "connected",
            "data": {
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        })

        # 主消息循环（仅处理心跳响应）
        while True:
            try:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                # 仅处理心跳响应（由后端单向发起 ping，前端响应 pong）
                if data.get("type") == "pong":
                    # 心跳响应由 manager 统一处理
                    pass
                else:
                    logger.debug(f"收到消息：{data.get('type')}")

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
        from turing_test.backend.services.match_service import get_match_service
        match_service = get_match_service()
        try:
            # 从匹配队列移除
            await match_service.remove_from_queue(user_id)
            # 清理匹配结果缓存（避免用户重新匹配时冲突）
            await match_service.clear_result(user_id)
            logger.info(f"用户 {user_id} 已清理匹配状态")
        except Exception as e:
            logger.error(f"清理匹配状态时出错：{e}")
        manager.disconnect(user_id)
