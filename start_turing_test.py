#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图灵测试社交实验平台启动脚本

用法:
    python start_turing_test.py

环境变量:
    PORT - 服务监听端口（默认：8000）
    HOST - 服务监听地址（默认：0.0.0.0）
"""

import os
import sys
import uvicorn

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 将项目根目录添加到 Python 路径，使 alice 模块可导入
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 从环境变量读取端口和地址（支持云平台部署）
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

if __name__ == '__main__':
    # 导入后端 main 模块
    from turing_test.backend.main import app

    print("=" * 50)
    print("图灵测试社交实验平台启动中...")
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"监听地址：http://{HOST}:{PORT}")
    print(f"端口：{PORT} (来自环境变量 PORT)")
    print("=" * 50)

    uvicorn.run(app, host=HOST, port=PORT)
