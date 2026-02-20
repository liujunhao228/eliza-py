#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试规则触发日志"""

from alice.alice_v2 import AliceBot
import logging

# 设置日志级别为 DEBUG 以查看详细信息
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = AliceBot()

# 测试 1: 情感表达
print('=== 测试 1: 情感表达 ===')
response = bot.respond('我今天好开心')
print(f'响应：{response}')

# 测试 2: 问候
print('\n=== 测试 2: 问候 ===')
response = bot.respond('你好')
print(f'响应：{response}')

# 测试 3: 叙事
print('\n=== 测试 3: 叙事 ===')
response = bot.respond('我昨天去买了一本书')
print(f'响应：{response}')

# 测试 4: 问题
print('\n=== 测试 4: 问题 ===')
response = bot.respond('你为什么这样想？')
print(f'响应：{response}')

print('\n=== 测试完成 ===')
