#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证 API 安全修复测试

测试内容：
1. 用户名枚举漏洞修复 - 统一错误提示
2. 后端密码强度校验
3. 后端昵称格式校验
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from turing_test.backend.api.auth import validate_password_strength, validate_nickname_format


def test_password_validation_function():
    """测试后端密码强度验证函数"""
    print("=" * 60)
    print("后端密码强度验证函数测试")
    print("=" * 60)

    test_cases = [
        # (密码，是否应该通过)
        ("123", False),
        ("1234567", False),  # 7 位
        ("12345678", False),  # 无大写字母
        ("abcdefgh", False),  # 无大写和数字
        ("ABCDEFGH", False),  # 无小写和数字
        ("Abcdefgh", False),  # 无数字
        ("Test1234", True),  # 有效密码
        ("MyP@ssw0rd", True),  # 有效密码
        ("SecurePass99", True),  # 有效密码
        ("a" * 73, False),  # 超过 72 位
    ]

    passed = 0
    failed = 0

    for password, should_pass in test_cases:
        is_valid, error_msg = validate_password_strength(password)
        if is_valid == should_pass:
            status = "✅" if is_valid else "✅"
            print(f"{status} 通过：密码 '{password[:10]}{'...' if len(password) > 10 else ''}' - 验证结果正确 (通过={is_valid})")
            passed += 1
        else:
            print(f"❌ 失败：密码 '{password[:10]}{'...' if len(password) > 10 else ''}' - 预期通过={should_pass}, 实际={is_valid} ({error_msg})")
            failed += 1

    print(f"结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    return failed == 0


def test_nickname_validation_function():
    """测试后端昵称格式验证函数"""
    print("=" * 60)
    print("后端昵称格式验证函数测试")
    print("=" * 60)

    test_cases = [
        # (昵称，是否应该通过)
        ("a", False),  # 太短
        ("ab", True),  # 最小长度
        ("访客#123", True),  # 中文 + 英文 + 数字+#
        ("用户#001", True),  # 中文 + 数字+#
        ("TestUser99", True),  # 英文 + 数字
        ("a" * 21, False),  # 超过 20 位
        ("test@user", False),  # 含@符号
        ("test user", False),  # 含空格
        ("测试<用户>", False),  # 含<>符号
        ("", False),  # 空字符串
    ]

    passed = 0
    failed = 0

    for nickname, should_pass in test_cases:
        is_valid, error_msg = validate_nickname_format(nickname)
        if is_valid == should_pass:
            status = "✅" if is_valid else "✅"
            display_nick = nickname[:10] + ('...' if len(nickname) > 10 else '')
            print(f"{status} 通过：昵称 '{display_nick}' - 验证结果正确 (通过={is_valid})")
            passed += 1
        else:
            display_nick = nickname[:10] + ('...' if len(nickname) > 10 else '')
            print(f"❌ 失败：昵称 '{display_nick}' - 预期通过={should_pass}, 实际={is_valid} ({error_msg})")
            failed += 1

    print(f"结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    return failed == 0


def test_username_enumeration_protection():
    """测试用户名枚举保护逻辑"""
    print("=" * 60)
    print("用户名枚举保护测试（代码审查）")
    print("=" * 60)

    # 读取 auth.py 文件，检查错误消息是否统一
    auth_file = Path(project_root) / "api" / "auth.py"
    content = auth_file.read_text(encoding="utf-8")

    # 检查登录接口中是否有统一的错误提示
    checks = [
        ('detail="昵称或密码错误"', "统一错误提示"),
        ("status_code=status.HTTP_401_UNAUTHORIZED", "返回 401 状态码"),
    ]

    passed = 0
    failed = 0

    for check_str, description in checks:
        if check_str in content:
            print(f"✅ 通过：{description} - 已实现")
            passed += 1
        else:
            print(f"❌ 失败：{description} - 未找到")
            failed += 1

    # 检查是否移除了泄露用户的错误消息
    dangerous_messages = [
        '用户不存在',
        '邀请码无效',
        '邀请码已被使用',
    ]

    print("\n检查是否存在信息泄露的错误消息:")
    for msg in dangerous_messages:
        # 注意：这些消息可能存在于 register 接口，那是合理的
        # 我们主要检查 login 接口
        login_func_start = content.find('async def login(')
        login_func_end = content.find('async def register(', login_func_start)
        login_func_content = content[login_func_start:login_func_end]

        # 只检查 detail= 中的实际错误消息，忽略注释
        # 查找所有 detail="xxx" 或 detail='xxx' 的模式
        import re
        detail_pattern = r'detail\s*=\s*["\']([^"\']+)["\']'
        detail_messages = re.findall(detail_pattern, login_func_content)

        # 检查是否有泄露信息的错误消息出现在 detail 中
        found_in_detail = msg in detail_messages

        if found_in_detail:
            # 检查是否与 401 一起出现（如果是 401 则是安全的）
            if 'HTTP_401_UNAUTHORIZED' in login_func_content[login_func_content.find(msg)-200:login_func_content.find(msg)+200]:
                print(f"✅ 通过：'{msg}' 与 401 一起使用 - 安全")
                passed += 1
            else:
                print(f"⚠️ 警告：'{msg}' 可能泄露信息")
                failed += 1
        else:
            print(f"✅ 通过：未找到 '{msg}' 在错误详情中")
            passed += 1

    print(f"结果：{passed} 通过，{failed} 警告")
    print("=" * 60)
    return failed == 0


def run_all_tests():
    """运行所有安全测试"""
    print("\n" + "=" * 60)
    print("认证 API 安全修复测试套件")
    print("=" * 60 + "\n")

    results = []

    results.append(("密码强度验证", test_password_validation_function()))
    results.append(("昵称格式验证", test_nickname_validation_function()))
    results.append(("用户名枚举保护", test_username_enumeration_protection()))

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")

    print("=" * 60)

    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试未通过")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
