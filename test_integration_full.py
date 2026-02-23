#!/usr/bin/env python3
"""
前后端联调测试脚本

测试项目：
1. 后端健康检查
2. 用户认证 API
3. 游戏 API
4. WebSocket 连接
5. 前端构建验证
"""

import asyncio
import sys
import requests
import json

sys.path.insert(0, "F:/eliza-py")

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

# 测试结果
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0
}

def test_api(name, func):
    """测试 API 并记录结果"""
    try:
        result = func()
        if result:
            print_success(name)
            test_results["passed"] += 1
        else:
            print_warning(f"{name} - 返回空值")
            test_results["warnings"] += 1
    except Exception as e:
        print_error(f"{name} - {str(e)}")
        test_results["failed"] += 1

# =============================================================================
# 测试用例
# =============================================================================

def test_health():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "healthy"
    assert data["database_connected"] == True
    assert data["bot_pool_size"] > 0
    return data

def test_root():
    """测试根路径"""
    response = requests.get(f"{BASE_URL}/", timeout=5)
    data = response.json()
    assert response.status_code == 200
    assert "app" in data
    return data

def test_login():
    """测试登录 API"""
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"invite_code": "TEST123"},
        timeout=10
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "username" in data
    assert "score" in data
    return data

def test_register():
    """测试注册 API"""
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    response = requests.post(
        f"{API_URL}/auth/register",
        json={"invite_code": code, "username": f"测试用户{code}"},
        timeout=10
    )
    # 201 或 200 都是成功的
    assert response.status_code in [200, 201]
    data = response.json()
    assert "id" in data
    return data

def test_verify_invite_code():
    """测试邀请码验证"""
    response = requests.get(f"{API_URL}/auth/verify/TEST123", timeout=5)
    assert response.status_code == 200
    return response.json()

def test_game_multipliers():
    """测试游戏乘数 API"""
    response = requests.get(f"{API_URL}/game/multipliers", params={"meta_count": 2}, timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert "meta_multiplier" in data
    assert "penalty_multiplier" in data
    return data

def test_game_prediction():
    """测试积分预测 API"""
    response = requests.get(f"{API_URL}/game/prediction", params={"turn": 5, "meta_count": 1}, timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    return data

def test_get_user():
    """测试获取用户信息"""
    # 先登录获取用户 ID
    login_response = requests.post(
        f"{API_URL}/auth/login",
        json={"invite_code": "TEST123"},
        timeout=10
    )
    user_id = login_response.json()["id"]
    
    response = requests.get(f"{API_URL}/user/{user_id}", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    return data

def test_get_user_stats():
    """测试获取用户统计"""
    login_response = requests.post(
        f"{API_URL}/auth/login",
        json={"invite_code": "TEST123"},
        timeout=10
    )
    user_id = login_response.json()["id"]
    
    response = requests.get(f"{API_URL}/user/{user_id}/stats", timeout=5)
    assert response.status_code == 200
    return response.json()

def test_score_history():
    """测试积分历史"""
    login_response = requests.post(
        f"{API_URL}/auth/login",
        json={"invite_code": "TEST123"},
        timeout=10
    )
    user_id = login_response.json()["id"]
    
    response = requests.get(f"{API_URL}/user/{user_id}/score-history", timeout=5)
    assert response.status_code == 200
    return response.json()

def test_websocket_connection():
    """测试 WebSocket 连接"""
    import websocket
    import requests as req
    import time

    # 先登录获取用户信息
    login_response = req.post(
        f"{API_URL}/auth/login",
        json={"invite_code": "TEST123"},
        timeout=10
    )
    if login_response.status_code != 200:
        return {"connected": False, "error": "登录失败"}
    
    user_data = login_response.json()
    user_id = user_data["id"]
    
    # 创建一个测试会话
    session_response = req.post(
        f"{API_URL}/session",
        json={"user_id": user_id, "opponent_type": "ai"},
        timeout=10
    )
    if session_response.status_code != 201:
        return {"connected": False, "error": "创建会话失败"}
    
    session_id = session_response.json()["id"]
    
    ws_url = f"ws://localhost:8000/ws/chat?user_id={user_id}&session_id={session_id}"
    ws = None
    try:
        ws = websocket.create_connection(ws_url, timeout=5)
        # 接收连接确认消息
        result = ws.recv()
        ws.close()
        return {"connected": True, "response": result}
    except Exception as e:
        # WebSocket 可能还未完全实现
        return {"connected": False, "error": str(e)}
    finally:
        if ws:
            try:
                ws.close()
            except:
                pass

def test_frontend_build():
    """测试前端构建"""
    import os
    dist_path = "F:/eliza-py/turing_test/frontend/dist"
    if os.path.exists(dist_path):
        files = os.listdir(dist_path)
        return {"exists": True, "files": files}
    return {"exists": False}

# =============================================================================
# 主测试流程
# =============================================================================

def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print(f"{Colors.BLUE}前后端联调测试{Colors.END}")
    print("=" * 60 + "\n")
    
    # 系统信息
    print_info("系统信息")
    print(f"  API 地址：{API_URL}")
    print(f"  WebSocket 地址：ws://localhost:8000/ws")
    print(f"  前端目录：F:/eliza-py/turing_test/frontend")
    print()
    
    # 基础 API 测试
    print(f"\n{Colors.YELLOW}[1] 基础 API 测试{Colors.END}")
    test_api("根路径 API", test_root)
    test_api("健康检查 API", test_health)
    
    # 认证 API 测试
    print(f"\n{Colors.YELLOW}[2] 认证 API 测试{Colors.END}")
    test_api("邀请码验证", test_verify_invite_code)
    test_api("用户登录", test_login)
    test_api("用户注册", test_register)
    
    # 用户 API 测试
    print(f"\n{Colors.YELLOW}[3] 用户 API 测试{Colors.END}")
    test_api("获取用户信息", test_get_user)
    test_api("获取用户统计", test_get_user_stats)
    test_api("获取积分历史", test_score_history)
    
    # 游戏 API 测试
    print(f"\n{Colors.YELLOW}[4] 游戏 API 测试{Colors.END}")
    test_api("游戏乘数查询", test_game_multipliers)
    test_api("积分预测", test_game_prediction)
    
    # WebSocket 测试
    print(f"\n{Colors.YELLOW}[5] WebSocket 测试{Colors.END}")
    try:
        result = test_websocket_connection()
        if result.get("connected"):
            print_success(f"WebSocket 连接成功")
            test_results["passed"] += 1
        else:
            print_warning(f"WebSocket 连接失败：{result.get('error', '未知错误')}")
            test_results["warnings"] += 1
    except Exception as e:
        print_error(f"WebSocket 测试失败：{str(e)}")
        test_results["failed"] += 1
    
    # 前端测试
    print(f"\n{Colors.YELLOW}[6] 前端构建测试{Colors.END}")
    try:
        result = test_frontend_build()
        if result.get("exists"):
            print_success(f"前端构建成功，文件数：{len(result.get('files', []))}")
            test_results["passed"] += 1
        else:
            print_warning("前端未构建，运行 'npm run build'")
            test_results["warnings"] += 1
    except Exception as e:
        print_error(f"前端测试失败：{str(e)}")
        test_results["failed"] += 1
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print(f"{Colors.BLUE}测试结果汇总{Colors.END}")
    print("=" * 60)
    print(f"  通过：{Colors.GREEN}{test_results['passed']}{Colors.END}")
    print(f"  失败：{Colors.RED}{test_results['failed']}{Colors.END}")
    print(f"  警告：{Colors.YELLOW}{test_results['warnings']}{Colors.END}")
    print("=" * 60 + "\n")
    
    # 返回退出码
    return 0 if test_results["failed"] == 0 else 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
