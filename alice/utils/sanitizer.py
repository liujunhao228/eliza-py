#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敏感信息脱敏工具模块

根据编码规范，日志中不应该包含敏感信息：
- 个人身份信息（姓名、电话、邮箱等）
- 认证信息（密码、token 等）
- 其他隐私数据

使用示例:
    from alice.utils.sanitizer import sanitize_text, sanitize_for_logging

    # 脱敏用户输入
    safe_text = sanitize_text(user_input, max_length=100)

    # 脱敏日志上下文
    safe_context = sanitize_for_logging({
        'user_input': user_input,
        'user_id': user_id,
        'token': token
    })
"""

import re
from typing import Any, Dict, List, Optional, Union


# 敏感信息模式
SENSITIVE_PATTERNS = {
    'phone': re.compile(r'1[3-9]\d{9}'),  # 手机号
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # 邮箱
    'id_card': re.compile(r'\b\d{17}[\dXx]|\d{15}\b'),  # 身份证号
    'bank_card': re.compile(r'\b\d{16,19}\b'),  # 银行卡号
    'password': re.compile(r'(?i)(password|passwd|pwd|secret|token|api_key|apikey)\s*[=:]\s*\S+'),  # 密码/密钥
    'url_with_token': re.compile(r'(token|access_token|api_key)=\S+'),  # URL 中的 token
}

# 需要脱敏的键名
SENSITIVE_KEYS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'access_token', 'refresh_token', 'auth_token', 'credential', 'private_key'
}


def sanitize_text(
    text: str,
    max_length: int = 100,
    truncate_at_end: bool = True,
) -> str:
    """
    脱敏文本

    Args:
        text: 原始文本
        max_length: 最大长度（超过则截断）
        truncate_at_end: 是否在末尾截断（True=保留开头，False=保留结尾）

    Returns:
        脱敏后的文本
    """
    if not text:
        return ""

    # 先进行敏感模式替换
    result = text

    # 替换手机号
    result = SENSITIVE_PATTERNS['phone'].sub(
        lambda m: m.group()[:3] + '*' * 4 + m.group()[-4:],
        result
    )

    # 替换邮箱
    result = SENSITIVE_PATTERNS['email'].sub(
        lambda m: m.group()[0] + '*' * 5 + '@***.***',
        result
    )

    # 替换身份证号
    result = SENSITIVE_PATTERNS['id_card'].sub(
        lambda m: m.group()[:6] + '*' * 8 + m.group()[-4:],
        result
    )

    # 替换银行卡号
    result = SENSITIVE_PATTERNS['bank_card'].sub(
        lambda m: '*' * 12 + m.group()[-4:],
        result
    )

    # 替换密码/密钥
    result = SENSITIVE_PATTERNS['password'].sub(
        lambda m: m.group().split('=')[0] + '=***' if '=' in m.group() else m.group().split(':')[0] + ':***',
        result
    )

    # 替换 URL 中的 token
    result = SENSITIVE_PATTERNS['url_with_token'].sub(
        lambda m: m.group().split('=')[0] + '=***',
        result
    )

    # 截断长文本
    if len(result) > max_length:
        if truncate_at_end:
            result = result[:max_length] + '...'
        else:
            result = '...' + result[-max_length:]

    return result


def sanitize_value(value: Any) -> Any:
    """
    脱敏单个值

    Args:
        value: 任意值

    Returns:
        脱敏后的值
    """
    if isinstance(value, str):
        return sanitize_text(value)
    elif isinstance(value, (int, float, bool, type(None))):
        return value
    elif isinstance(value, (list, tuple)):
        return type(value)(sanitize_value(v) for v in value)
    elif isinstance(value, dict):
        return sanitize_dict(value)
    else:
        # 其他类型转为字符串后脱敏
        return sanitize_text(str(value))


def sanitize_dict(
    data: Dict[str, Any],
    sensitive_keys: Optional[set] = None,
) -> Dict[str, Any]:
    """
    脱敏字典

    Args:
        data: 原始字典
        sensitive_keys: 额外的敏感键名集合

    Returns:
        脱敏后的字典
    """
    if not data:
        return {}

    keys_to_check = SENSITIVE_KEYS.copy()
    if sensitive_keys:
        keys_to_check.update(sensitive_keys)

    result = {}
    for key, value in data.items():
        # 检查键名是否敏感
        key_lower = key.lower()
        if key_lower in keys_to_check:
            result[key] = '***'
        else:
            result[key] = sanitize_value(value)

    return result


def sanitize_for_logging(
    data: Union[str, Dict[str, Any]],
    max_length: int = 100,
) -> Union[str, Dict[str, Any]]:
    """
    为日志记录脱敏数据

    Args:
        data: 待脱敏的数据（字符串或字典）
        max_length: 字符串最大长度

    Returns:
        脱敏后的数据
    """
    if isinstance(data, str):
        return sanitize_text(data, max_length=max_length)
    elif isinstance(data, dict):
        return sanitize_dict(data)
    else:
        return sanitize_value(data)


def contains_sensitive_info(text: str) -> bool:
    """
    检查文本是否包含敏感信息

    Args:
        text: 待检查文本

    Returns:
        是否包含敏感信息
    """
    for pattern in SENSITIVE_PATTERNS.values():
        if pattern.search(text):
            return True
    return False


def get_sensitive_info_types(text: str) -> List[str]:
    """
    获取文本中包含的敏感信息类型

    Args:
        text: 待检查文本

    Returns:
        敏感信息类型列表
    """
    types = []
    for name, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(text):
            types.append(name)
    return types
