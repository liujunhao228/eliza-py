#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 示例运行脚本
用于正确设置Python路径并运行ltp-example.py
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path[:3]}...")  # 显示前3个路径

# 运行ltp-example.py
ltp_example_path = os.path.join(project_root, 'alice', 'nlp', 'engines', 'ltp-example.py')
print(f"运行文件: {ltp_example_path}")

if os.path.exists(ltp_example_path):
    # 使用exec执行文件内容
    with open(ltp_example_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 执行代码
    exec(code, {'__name__': '__main__'})
else:
    print(f"错误: 找不到文件 {ltp_example_path}")
