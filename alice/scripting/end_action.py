#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结束对话动作模块

定义 Bot 主动结束对话的数据结构和相关类型。
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class EndAction:
    """
    结束对话动作

    Attributes:
        action: 结束动作类型
            - "none": 不结束对话（默认）
            - "direct": 直接结束，不发送响应
            - "farewell": 先发送告别语，再结束
        reason: 结束原因
            - "max_turns": 达到最大轮数
            - "suspicion": 检测到用户怀疑
            - "timeout": 超时/用户无响应
            - "user_farewell": 用户先说再见
            - "custom": 自定义原因
        script_id: 触发结束的脚本 ID
        metadata: 附加元数据
    """
    action: Literal["none", "direct", "farewell"] = "none"
    reason: str = ""
    script_id: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_ending(self) -> bool:
        """是否需要结束对话"""
        return self.action in ("direct", "farewell")

    def should_send_farewell(self) -> bool:
        """是否应该先发送告别语再结束"""
        return self.action == "farewell"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "action": self.action,
            "reason": self.reason,
            "script_id": self.script_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_response(cls, script_response: 'ScriptResponse') -> 'EndAction':
        """
        从 ScriptResponse 创建 EndAction

        Args:
            script_response: 脚本响应

        Returns:
            EndAction 实例
        """
        return cls(
            action=script_response.end_action,
            reason=script_response.end_reason,
            script_id=script_response.script_id,
        )


# 预定义的结束动作实例
END_NONE = EndAction(action="none")
END_DIRECT_MAX_TURNS = EndAction(action="direct", reason="max_turns")
END_DIRECT_SUSPICION = EndAction(action="direct", reason="suspicion")
END_DIRECT_TIMEOUT = EndAction(action="direct", reason="timeout")
END_FAREWELL = EndAction(action="farewell", reason="user_farewell")
