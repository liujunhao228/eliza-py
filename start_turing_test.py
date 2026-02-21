#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图灵测试社交实验平台启动脚本

用法:
    python start_turing_test.py
"""

import os
import sys
import uvicorn

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 将项目根目录添加到 Python 路径，使 alice 模块可导入
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == '__main__':
    # 导入后端 main 模块
    from turing_test.backend.main import app
    
    print("=" * 50)
    print("图灵测试社交实验平台启动中...")
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"访问地址：http://localhost:8000")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
