#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
密码强度验证测试
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from turing_test.backend.schemas import UserRegister
from pydantic import ValidationError


def test_password_validation():
    """测试密码强度验证"""
    
    test_cases = [
        # (密码，是否应该通过，预期错误信息)
        ("123", False, "密码长度至少 8 位"),
        ("1234567", False, "密码长度至少 8 位"),  # 7 位
        ("12345678", False, "密码必须包含大写字母"),
        ("abcdefgh", False, "密码必须包含大写字母"),
        ("ABCDEFGH", False, "密码必须包含小写字母"),
        ("Abcdefgh", False, "密码必须包含数字"),
        ("Test1234", True, None),  # 有效密码（8 位）
        ("MyP@ssw0rd", True, None),  # 有效密码（含特殊字符）
        ("SecurePass99", True, None),  # 有效密码
    ]
    
    print("=" * 60)
    print("密码强度验证测试")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for password, should_pass, expected_msg in test_cases:
        try:
            UserRegister(
                invite_code="ABCD1234",
                nickname="testuser",
                password=password
            )
            if should_pass:
                print(f"✅ 通过：密码 '{password}' - 符合强度要求")
                passed += 1
            else:
                print(f"❌ 失败：密码 '{password}' - 应该被拒绝但通过了")
                failed += 1
        except ValidationError as e:
            error_msg = e.errors()[0]["msg"]
            if not should_pass:
                print(f"✅ 通过：密码 '{password}' - 正确拒绝 ({error_msg})")
                passed += 1
            else:
                print(f"❌ 失败：密码 '{password}' - 应该通过但被拒绝 ({error_msg})")
                failed += 1
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = test_password_validation()
    sys.exit(0 if success else 1)
