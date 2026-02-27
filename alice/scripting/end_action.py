#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结束对话动作模块

定义 Bot 主动结束对话的数据结构和相关类型。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class EndReason(str, Enum):
    """
    标准化结束原因枚举
    
    命名规范：{触发主体}_{具体原因}
    前缀约定：
      - bot_: Bot 主动触发
      - user_: 用户主动触发  
      - sys_: 系统自动触发
    """
    # ========== Bot 主动结束 ==========
    BOT_MAX_TURNS = "bot_max_turns"        # 达到最大轮数 (15 轮)
    BOT_MEDIUM_TURNS = "bot_medium_turns"  # 达到中等轮数 (10 轮)
    BOT_DEFENSE = "bot_defense"            # Bot 被用户识破/怀疑（自我防卫）
    BOT_TIMEOUT = "bot_timeout"            # 用户敷衍/无实质内容
    BOT_FAREWELL = "bot_farewell"          # 用户告别后 Bot 离开
    BOT_TIME_LIMIT = "bot_time_limit"      # 时间过晚/过早
    
    # ========== 用户主动结束 ==========
    USER_GAVE_UP = "user_gave_up"          # 用户未判断主动放弃
    USER_NORMAL_END = "user_normal_end"    # 用户完成判断后正常结束
    
    # ========== 系统自动结束 ==========
    SYS_TIMEOUT = "sys_timeout"            # 会话超时自动结束
    SYS_ERROR = "sys_error"                # 系统错误强制结束


@dataclass
class EndAction:
    """
    结束对话动作

    Attributes:
        action: 结束动作类型
            - "none": 不结束对话（默认）
            - "direct": 直接结束，不发送响应
            - "farewell": 先发送告别语，再结束
        reason: 结束原因 (使用 EndReason 枚举值)
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
END_DIRECT_MAX_TURNS = EndAction(action="direct", reason=EndReason.BOT_MAX_TURNS.value)
END_DIRECT_DEFENSE = EndAction(action="direct", reason=EndReason.BOT_DEFENSE.value)
END_DIRECT_TIMEOUT = EndAction(action="direct", reason=EndReason.BOT_TIMEOUT.value)
END_FAREWELL = EndAction(action="farewell", reason=EndReason.BOT_FAREWELL.value)


# =============================================================================
# 向后兼容：旧枚举值映射
# =============================================================================

END_REASON_ALIAS = {
    # Bot 侧旧值 -> 新标准值
    "max_turns": EndReason.BOT_MAX_TURNS.value,
    "suspicion": EndReason.BOT_DEFENSE.value,
    "timeout": EndReason.BOT_TIMEOUT.value,         # 默认映射到 Bot 侧（用户敷衍场景）
    "user_farewell": EndReason.BOT_FAREWELL.value,
    "custom": EndReason.BOT_FAREWELL.value,
    
    # 用户侧旧值 -> 新标准值
    "normal_end": EndReason.USER_NORMAL_END.value,
    # 注意："mid_game_judgment" 不映射，因为它不触发结束
    
    # 系统侧旧值 -> 新标准值
    # "timeout" 默认映射到 BOT_TIMEOUT，如果是系统超时场景需手动处理
}


def normalize_end_reason(reason: str) -> str:
    """
    标准化旧枚举值
    
    用于向后兼容，将旧的 end_reason 值映射到新的标准枚举值。
    
    Args:
        reason: 原始结束原因值
        
    Returns:
        标准化后的结束原因值（EndReason 枚举值或原值）
    """
    if not reason:
        return reason
    return END_REASON_ALIAS.get(reason, reason)


def is_valid_end_reason(reason: str) -> bool:
    """
    验证是否为有效的结束原因
    
    Args:
        reason: 结束原因值
        
    Returns:
        是否有效
    """
    if not reason:
        return False
    # 先尝试标准化
    normalized = normalize_end_reason(reason)
    # 检查是否是有效的枚举值
    try:
        EndReason(normalized)
        return True
    except ValueError:
        return False
