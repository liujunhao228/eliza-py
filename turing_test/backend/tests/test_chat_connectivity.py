#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天应用连通性测试脚本

测试 bots 与前端聊天应用的完整连接流程：
1. 测试后端服务健康状态
2. 测试 WebSocket 连接
3. 测试 Bot 池响应
4. 模拟完整聊天流程

用法:
    python turing_test/backend/test_chat_connectivity.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = "F:/eliza-py"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import websockets
import httpx


# =============================================================================
# 配置
# =============================================================================

WS_BASE_URL = "ws://localhost:8000/ws"
HTTP_BASE_URL = "http://localhost:8000"


# =============================================================================
# 测试工具函数
# =============================================================================

def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(msg: str):
    """打印成功消息"""
    print(f"✅ {msg}")


def print_error(msg: str):
    """打印错误消息"""
    print(f"❌ {msg}")


def print_info(msg: str):
    """打印信息"""
    print(f"ℹ️  {msg}")


# =============================================================================
# 测试 1: 健康检查
# =============================================================================

async def test_health_check():
    """测试后端服务健康状态"""
    print_header("测试 1: 后端服务健康检查")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HTTP_BASE_URL}/health", timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"服务状态：{data.get('status', 'unknown')}")
                print_success(f"数据库连接：{'正常' if data.get('database_connected') else '断开'}")
                print_success(f"Bot 池大小：{data.get('bot_pool_size', 0)}")
                return True
            else:
                print_error(f"健康检查失败：HTTP {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print_error("无法连接到后端服务，请确保后端已启动")
        return False
    except Exception as e:
        print_error(f"健康检查出错：{e}")
        return False


# =============================================================================
# 测试 2: 创建测试用户和会话
# =============================================================================

async def create_test_user_and_session():
    """
    创建测试用户和 AI 会话
    
    流程：
    1. 使用邀请码登录/创建用户
    2. 通过 WebSocket 加入匹配队列
    3. 等待匹配超时后自动分配 AI 对手
    """
    print_header("测试 2: 创建测试用户和会话")
    
    # 使用一个测试邀请码（从 invite_codes.txt 中选取）
    test_invite_codes = [
        "203C9H", "YDX2N1", "COH818", "SZC1R5", "ER67H1",
        "NLAABR", "Z14QCH", "JV5HRY", "LVZUP5", "PREAGO"
    ]
    
    try:
        async with httpx.AsyncClient() as client:
            user_id = None
            
            # 1. 使用邀请码登录/创建用户
            print_info("使用邀请码登录/创建用户...")
            
            for invite_code in test_invite_codes:
                login_data = {"invite_code": invite_code}
                
                try:
                    response = await client.post(
                        f"{HTTP_BASE_URL}/api/auth/login",
                        json=login_data,
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        user_info = response.json()
                        user_id = user_info.get('user_id') or user_info.get('id')
                        username = user_info.get('username', 'unknown')
                        score = user_info.get('score', 0)
                        print_success(f"登录成功 - 用户：{username}, ID: {user_id}, 积分：{score}")
                        print_info(f"  使用邀请码：{invite_code}")
                        break
                    elif response.status_code == 400:
                        # 邀请码不存在，尝试下一个
                        continue
                    else:
                        print_error(f"登录失败：HTTP {response.status_code}")
                        
                except Exception as e:
                    print_error(f"尝试邀请码 {invite_code} 失败：{e}")
                    continue
            
            if not user_id:
                print_error("所有测试邀请码都无法使用")
                return None, None
            
            # 2. 通过 WebSocket 加入匹配队列，等待 AI 匹配
            print_info("通过 WebSocket 加入匹配队列...")
            print_info("等待匹配超时后自动分配 AI 对手（约 30-45 秒）...")
            
            ws_url = f"{WS_BASE_URL}/match?user_id={user_id}"
            
            try:
                async with websockets.connect(ws_url) as websocket:
                    print_success("WebSocket 匹配连接成功")
                    
                    # 发送加入队列消息
                    await websocket.send(json.dumps({"type": "join"}))
                    print_info("已发送加入队列请求")
                    
                    # 等待匹配结果
                    session_id = None
                    wait_time = 0
                    max_wait = 50  # 最多等待 50 秒
                    
                    while wait_time < max_wait:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            data = json.loads(response)
                            msg_type = data.get('type')
                            
                            print_info(f"收到消息：{msg_type}")
                            
                            if msg_type == 'match_found':
                                match_data = data.get('data', {})
                                session_id = match_data.get('session_id')
                                opponent_type = match_data.get('opponent_type')
                                is_honeypot = match_data.get('is_honeypot')
                                
                                print_success(f"匹配成功!")
                                print_info(f"  会话 ID: {session_id}")
                                print_info(f"  对手类型：{opponent_type}")
                                print_info(f"  是否钓鱼机器人：{is_honeypot}")
                                
                                # 断开匹配 WebSocket
                                await websocket.send(json.dumps({"type": "cancel"}))
                                break
                                
                            elif msg_type == 'queue_status':
                                queue_data = data.get('data', {})
                                position = queue_data.get('queue_position', '?')
                                estimated = queue_data.get('estimated_wait_time', '?')
                                print_info(f"  队列位置：{position}, 预计等待：{estimated}秒")
                                
                            elif msg_type == 'match_failed':
                                print_error(f"匹配失败：{data.get('data', {}).get('reason')}")
                                break
                                
                        except asyncio.TimeoutError:
                            wait_time += 5
                            print_info(f"等待中... ({wait_time}/{max_wait}秒)")
                    
                    if session_id:
                        return user_id, session_id
                    else:
                        print_error("匹配超时，未获得会话 ID")
                        return user_id, None
                        
            except Exception as e:
                print_error(f"WebSocket 匹配失败：{e}")
                return user_id, None
                
    except Exception as e:
        print_error(f"创建会话出错：{e}")
        import traceback
        traceback.print_exc()
        return None, None


# =============================================================================
# 测试 3: WebSocket 连接测试
# =============================================================================

async def test_websocket_connection(user_id: int, session_id: int):
    """测试 WebSocket 连接"""
    print_header("测试 3: WebSocket 连接测试")
    
    ws_url = f"{WS_BASE_URL}/chat?session_id={session_id}&user_id={user_id}"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print_success("WebSocket 连接成功")
            
            # 等待连接确认消息
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print_info(f"收到连接确认：{data.get('type')}")
                
                if data.get('type') == 'connected':
                    conn_data = data.get('data', {})
                    print_success(f"会话类型：{conn_data.get('opponent_type')}")
                    print_success(f"是否钓鱼机器人：{conn_data.get('is_honeypot')}")
                    return True
                else:
                    print_error(f"意外的消息类型：{data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                print_error("等待连接确认超时")
                return False
                
    except websockets.exceptions.InvalidStatusCode as e:
        print_error(f"WebSocket 连接失败：HTTP {e.status_code}")
        return False
    except Exception as e:
        print_error(f"WebSocket 连接出错：{e}")
        return False


# =============================================================================
# 测试 4: 聊天消息测试
# =============================================================================

async def test_chat_messages(user_id: int, session_id: int):
    """测试聊天消息收发"""
    print_header("测试 4: 聊天消息测试")
    
    ws_url = f"{WS_BASE_URL}/chat?session_id={session_id}&user_id={user_id}"
    
    test_messages = [
        "你好！",
        "今天天气怎么样？",
        "你喜欢什么类型的音乐？",
    ]
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # 等待连接确认
            await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print_success("WebSocket 已连接")
            
            for i, content in enumerate(test_messages):
                print_info(f"\n发送消息 {i+1}: {content}")
                
                # 发送消息
                message = {
                    "type": "chat",
                    "data": {"content": content}
                }
                await websocket.send(json.dumps(message))
                
                # 接收响应（可能有多条消息）
                received_typing = False
                received_chat = False
                
                for _ in range(5):  # 最多等待 5 条消息
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(response)
                        msg_type = data.get('type')
                        
                        if msg_type == 'typing':
                            typing_data = data.get('data', {})
                            status = "开始输入" if typing_data.get('is_typing') else "停止输入"
                            if typing_data.get('is_typing') and not received_typing:
                                print_info(f"  对手 {status}...")
                                received_typing = True
                                
                        elif msg_type == 'chat':
                            chat_data = data.get('data', {})
                            sender = chat_data.get('sender')
                            msg_content = chat_data.get('content')
                            
                            if sender == 'opponent':
                                print_success(f"  对手回复：{msg_content}")
                                received_chat = True
                                break
                                
                    except asyncio.TimeoutError:
                        break
                
                if not received_chat:
                    print_error("  未收到对手回复")
                
                # 等待一下再发送下一条
                await asyncio.sleep(1)
            
            # 结束会话
            print_info("\n结束会话...")
            await websocket.send(json.dumps({
                "type": "end_session",
                "data": {}
            }))
            
            print_success("聊天测试完成")
            return True
            
    except Exception as e:
        print_error(f"聊天测试出错：{e}")
        return False


# =============================================================================
# 测试 5: Bot 池状态检查
# =============================================================================

async def test_bot_pool_status():
    """测试 Bot 池状态"""
    print_header("测试 5: Bot 池状态检查")
    
    try:
        # 通过导入服务直接检查
        from turing_test.backend.services.ai_bot_service import get_ai_bot_service
        
        ai_bot_service = await get_ai_bot_service()
        stats = ai_bot_service.get_pool_stats()
        
        print_success(f"Bot 池状态:")
        print_info(f"  总实例数：{stats.get('total_instances', 0)}")
        print_info(f"  活跃实例数：{stats.get('active_instances', 0)}")
        print_info(f"  最小实例数：{stats.get('min_instances', 0)}")
        print_info(f"  最大实例数：{stats.get('max_instances', 0)}")
        
        return True
        
    except ImportError:
        print_error("无法导入 Bot 服务模块")
        return False
    except Exception as e:
        print_error(f"Bot 池状态检查出错：{e}")
        return False


# =============================================================================
# 测试 6: 元对话检测测试
# =============================================================================

async def test_meta_conversation(user_id: int, session_id: int):
    """测试元对话检测"""
    print_header("测试 6: 元对话检测测试")
    
    ws_url = f"{WS_BASE_URL}/chat?session_id={session_id}&user_id={user_id}"
    
    meta_messages = [
        "你是真人还是 AI？",
        "你的身份是什么？",
        "你是机器人吗？",
    ]
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # 等待连接确认
            await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            for content in meta_messages:
                print_info(f"\n发送元对话消息：{content}")
                
                message = {
                    "type": "chat",
                    "data": {"content": content}
                }
                await websocket.send(json.dumps(message))
                
                # 接收响应
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(response)
                    
                    if data.get('type') == 'chat':
                        chat_data = data.get('data', {})
                        if chat_data.get('sender') == 'opponent':
                            print_success(f"  对手回复：{chat_data.get('content')}")
                except asyncio.TimeoutError:
                    print_error("  未收到回复")
                
                await asyncio.sleep(1)
            
            # 结束会话
            await websocket.send(json.dumps({
                "type": "end_session",
                "data": {}
            }))
            
            print_success("元对话测试完成")
            return True
            
    except Exception as e:
        print_error(f"元对话测试出错：{e}")
        return False


# =============================================================================
# 主测试流程
# =============================================================================

async def run_all_tests():
    """运行所有测试"""
    print_header("🚀 开始聊天应用连通性测试")
    print_info(f"后端地址：{HTTP_BASE_URL}")
    print_info(f"WebSocket 地址：{WS_BASE_URL}")
    
    results = {
        "health_check": False,
        "bot_pool_status": False,
        "user_session_create": False,
        "websocket_connection": False,
        "chat_messages": False,
        "meta_conversation": False,
    }
    
    # 1. 健康检查
    results["health_check"] = await test_health_check()
    if not results["health_check"]:
        print_error("\n后端服务未运行，无法继续测试")
        print_info("\n请先启动后端服务：")
        print_info("  python start_turing_test.py")
        return results
    
    # 2. Bot 池状态
    results["bot_pool_status"] = await test_bot_pool_status()
    
    # 3. 创建用户和会话
    user_id, session_id = await create_test_user_and_session()
    if user_id and session_id:
        results["user_session_create"] = True
        
        # 4. WebSocket 连接测试
        results["websocket_connection"] = await test_websocket_connection(user_id, session_id)
        
        if results["websocket_connection"]:
            # 5. 聊天消息测试
            results["chat_messages"] = await test_chat_messages(user_id, session_id)
            
            # 6. 元对话检测测试（需要新建会话）
            # 重新创建会话
            _, new_session_id = await create_test_user_and_session()
            if new_session_id:
                results["meta_conversation"] = await test_meta_conversation(user_id, new_session_id)
    
    # 打印测试结果
    print_header("📊 测试结果汇总")
    
    test_names = {
        "health_check": "后端健康检查",
        "bot_pool_status": "Bot 池状态",
        "user_session_create": "用户/会话创建",
        "websocket_connection": "WebSocket 连接",
        "chat_messages": "聊天消息收发",
        "meta_conversation": "元对话检测",
    }
    
    passed = 0
    total = len(results)
    
    for key, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_names[key]}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print_success("🎉 所有测试通过！bots 与前端聊天应用连接正常")
    else:
        print_error(f"⚠️  有 {total - passed} 项测试失败，请检查日志")
    
    return results


def main():
    """主函数"""
    print("=" * 60)
    print("  聊天应用连通性测试工具")
    print("=" * 60)
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print_error(f"测试过程中出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
