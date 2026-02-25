"""
邀请码生成器模块

负责邀请码的生成算法、批量生成和唯一性校验。
"""

import random
import string
from typing import List, Optional

from loguru import logger

from config import settings


class InviteCodeGenerator:
    """邀请码生成器"""

    # 默认字符集（排除易混淆字符：0/O, 1/I/L）
    DEFAULT_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

    @classmethod
    def generate(
        cls,
        length: Optional[int] = None,
        prefix: str = "",
        suffix: str = "",
        charset: Optional[str] = None
    ) -> str:
        """
        生成单个邀请码

        Args:
            length: 邀请码总长度（包含前缀和后缀）
            prefix: 前缀
            suffix: 后缀
            charset: 字符集

        Returns:
            生成的邀请码
        """
        if length is None:
            length = settings.turing.auth.invite_code_length

        if charset is None:
            charset = cls.DEFAULT_CHARSET

        # 计算随机部分长度
        random_length = length - len(prefix) - len(suffix)
        if random_length <= 0:
            raise ValueError("邀请码长度不足以容纳前缀和后缀")

        # 生成随机部分
        random_part = ''.join(
            random.choice(charset) for _ in range(random_length)
        )

        return f"{prefix}{random_part}{suffix}"

    @classmethod
    def generate_batch(
        cls,
        count: int,
        length: Optional[int] = None,
        prefix: str = "",
        suffix: str = "",
        charset: Optional[str] = None,
        ensure_unique: bool = True,
        existing_codes: Optional[List[str]] = None
    ) -> List[str]:
        """
        批量生成邀请码

        Args:
            count: 生成数量
            length: 邀请码长度
            prefix: 前缀
            suffix: 后缀
            charset: 字符集
            ensure_unique: 确保唯一性
            existing_codes: 已存在的邀请码列表（用于去重）

        Returns:
            邀请码列表
        """
        codes = []
        max_attempts = count * 10  # 防止无限循环

        if ensure_unique:
            existing = set(existing_codes or [])
            attempts = 0

            while len(codes) < count and attempts < max_attempts:
                code = cls.generate(length, prefix, suffix, charset)
                if code not in existing:
                    codes.append(code)
                    existing.add(code)
                attempts += 1

            if len(codes) < count:
                logger.warning(
                    f"只生成了 {len(codes)}/{count} 个唯一邀请码，"
                    f"已达到最大尝试次数 {max_attempts}"
                )
        else:
            codes = [
                cls.generate(length, prefix, suffix, charset)
                for _ in range(count)
            ]

        return codes
