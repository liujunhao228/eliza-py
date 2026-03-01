"""
Bot 池抽象基类

定义 Bot 池的标准接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class BotConfig:
    """
    Bot 配置

    Attributes:
        id: Bot 唯一标识
        weight: 权重 (用于加权随机)
        description: 描述信息
        name_prefix: 名称前缀 (可选)
        response_delay_min_ms: 最小响应延迟 (毫秒)
        response_delay_max_ms: 最大响应延迟 (毫秒)
        system_prompt: 系统提示词 (可选)
    """
    id: str
    weight: float = 1.0
    description: str = ""
    name_prefix: Optional[str] = None
    response_delay_min_ms: int = 500
    response_delay_max_ms: int = 2000
    system_prompt: Optional[str] = None


@dataclass
class HoneypotBotConfig:
    """
    钓鱼 Bot 配置

    Attributes:
        id: Bot 唯一标识
        weight: 权重
        description: 描述信息
        response_delay_min_ms: 最小响应延迟 (毫秒)
        response_delay_max_ms: 最大响应延迟 (毫秒)
    """
    id: str
    weight: float = 1.0
    description: str = ""
    response_delay_min_ms: int = 2000
    response_delay_max_ms: int = 8000


class BotPoolBase(ABC):
    """
    Bot 池抽象基类

    定义 Bot 池的标准接口，支持：
    - 抽取 Bot
    - 获取统计信息
    - 线程安全
    """

    @abstractmethod
    def draw(self) -> Any:
        """
        抽取一个 Bot

        Returns:
            Bot 配置对象
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取 Bot 池统计信息

        Returns:
            统计信息字典
        """
        pass

    @abstractmethod
    def get_all_bots(self) -> List[Any]:
        """
        获取所有 Bot 配置（只读副本）

        Returns:
            Bot 配置列表
        """
        pass
