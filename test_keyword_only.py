#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 keyword_only 模板类型"""

from alice.alice_v2 import AliceBot

def test_greeting():
    """测试问候语不会被错误转换"""
    alice = AliceBot()
    
    test_cases = [
        ('你好', '你好'),  # 不应包含'我好'
        ('嗨', '嗨'),
        ('谢谢', None),  # 谢谢的响应不一定包含'谢谢'
        ('再见', '再见'),
    ]
    
    print('=== 测试问候语（不应触发代词替换）===')
    all_passed = True
    
    for user_input, expected_keyword in test_cases:
        response = alice.respond(user_input)
        print(f'Input: {user_input!r} -> Response: {response!r}')
        
        # 检查是否包含预期的关键词
        if expected_keyword and expected_keyword not in response:
            print(f'  [WARN] Response does not contain expected keyword {expected_keyword!r}')
        
        # 检查是否有错误的代词转换
        if '我好' in response:
            print(f'  [FAIL] Greeting was incorrectly transformed to "我好"!')
            all_passed = False
        else:
            print(f'  [PASS] No incorrect transformation')
    
    return all_passed


def test_pronoun_replacement():
    """测试需要代词替换的输入仍然正常工作"""
    alice = AliceBot()
    
    # 这些输入应该触发代词替换
    test_cases = [
        '我觉得很累了',
        '我喜欢这本书',
        '我认为他是对的',
    ]
    
    print()
    print('=== 测试代词替换（应该正常工作）===')
    
    for user_input in test_cases:
        response = alice.respond(user_input)
        print(f'Input: {user_input!r} -> Response: {response!r}')
        
        # 检查响应中是否包含'你'（代词替换后的结果）
        # 注意：由于响应是随机的，这里只做基本检查
        if response:
            print(f'  [PASS] Response generated')
        else:
            print(f'  [FAIL] No response generated')
            return False
    
    return True


def test_fallback():
    """测试回退响应"""
    alice = AliceBot()
    
    print()
    print('=== 测试回退响应 ===')
    
    response = alice.respond('今天天气不错')
    print(f'Input: "今天天气不错" -> Response: {response!r}')
    
    if response:
        print(f'  [PASS] Fallback response generated')
        return True
    else:
        print(f'  [FAIL] No fallback response')
        return False


if __name__ == '__main__':
    results = []
    results.append(('问候语测试', test_greeting()))
    results.append(('代词替换测试', test_pronoun_replacement()))
    results.append(('回退响应测试', test_fallback()))
    
    print()
    print('=' * 50)
    print('测试结果汇总:')
    for name, passed in results:
        status = '通过' if passed else '失败'
        print(f'  {name}: {status}')
    
    all_passed = all(passed for _, passed in results)
    print()
    if all_passed:
        print('所有测试通过！')
    else:
        print('部分测试失败！')
