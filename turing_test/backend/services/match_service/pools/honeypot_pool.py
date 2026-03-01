"""
钓鱼 Bot 池

使用加权随机抽取，支持两种类型的钓鱼 Bot:
- 攻击型 (aggressive): 容易激动，会骂人
- 可疑型 (sus): 说话像 AI，故意露破绽
"""

import random
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from .base import BotPoolBase, HoneypotBotConfig


@dataclass
class HoneypotPoolConfig:
    """
    钓鱼 Bot 池配置

    Attributes:
        bots: 钓鱼 Bot 配置列表
    """
    bots: List[HoneypotBotConfig]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HoneypotPoolConfig":
        """
        从字典创建配置

        Args:
            data: 配置字典

        Returns:
            HoneypotPoolConfig 实例
        """
        bots_cfg = data.get("bots", [])
        bots = []

        for bot_cfg in bots_cfg:
            bot = HoneypotBotConfig(
                id=bot_cfg.get("id", "unknown"),
                weight=float(bot_cfg.get("weight", 1.0)),
                description=bot_cfg.get("description", ""),
                response_delay_min_ms=bot_cfg.get("response_delay_min_ms", 2000),
                response_delay_max_ms=bot_cfg.get("response_delay_max_ms", 8000),
            )
            bots.append(bot)

        return cls(bots=bots)

    @classmethod
    def default(cls) -> "HoneypotPoolConfig":
        """创建默认配置"""
        return cls(
            bots=[
                HoneypotBotConfig(id="aggressive", weight=0.4, description="攻击型钓鱼"),
                HoneypotBotConfig(id="sus", weight=0.6, description="可疑型钓鱼"),
            ]
        )


class HoneypotPool(BotPoolBase):
    """
    钓鱼 Bot 池 - 加权随机抽取

    支持两种类型的钓鱼 Bot:
    - 攻击型 (aggressive): 容易激动，会骂人
    - 可疑型 (sus): 说话像 AI，故意露破绽

    线程安全:
    - 使用 threading.Lock 保护共享状态
    """

    def __init__(self, config: Optional[HoneypotPoolConfig] = None):
        """
        初始化钓鱼 Bot 池

        Args:
            config: 钓鱼 Bot 池配置
        """
        # 存储唯一的 Bot 配置
        self._bot_configs: List[HoneypotBotConfig] = []
        # 对应的权重列表
        self._weights: List[float] = []

        # 线程锁
        self._lock = threading.Lock()

        # 统计信息
        self._draw_count = 0

        if config:
            self._load_from_config(config)
        else:
            # 使用默认配置
            self._load_default_honeypots()

        logger.info(f"钓鱼 Bot 池初始化完成，共 {len(self._bot_configs)} 个唯一 Bot 配置")

    def _load_from_config(self, config: HoneypotPoolConfig) -> None:
        """从配置加载钓鱼 Bot 池"""
        if not config.bots:
            logger.warning("钓鱼 Bot 池配置为空，使用默认配置")
            self._load_default_honeypots()
            return

        with self._lock:
            self._bot_configs = config.bots.copy()
            self._weights = [bot.weight for bot in config.bots]

            for bot in config.bots:
                logger.debug(f"加载钓鱼 Bot: {bot.id}, weight={bot.weight}")

    def _load_default_honeypots(self) -> None:
        """加载默认钓鱼 Bot 配置"""
        default_config = HoneypotPoolConfig.default()
        with self._lock:
            self._bot_configs = default_config.bots
            self._weights = [bot.weight for bot in default_config.bots]

    def draw(self) -> HoneypotBotConfig:
        """
        随机抽取一个钓鱼 Bot（加权）

        使用 random.choices 实现高效的加权随机抽取。

        Returns:
            HoneypotBotConfig 实例
        """
        with self._lock:
            if not self._bot_configs:
                logger.warning("钓鱼 Bot 池为空，返回默认钓鱼 Bot")
                return HoneypotBotConfig(id="sus", weight=1.0, description="默认钓鱼 Bot")

            # 使用 random.choices 进行加权随机抽取
            selected = random.choices(
                population=self._bot_configs,
                weights=self._weights,
                k=1
            )[0]

            self._draw_count += 1

            # 返回副本，避免外部修改
            return HoneypotBotConfig(
                id=selected.id,
                weight=selected.weight,
                description=selected.description,
                response_delay_min_ms=selected.response_delay_min_ms,
                response_delay_max_ms=selected.response_delay_max_ms,
            )

    def get_bot_by_id(self, bot_id: str) -> Optional[HoneypotBotConfig]:
        """
        根据 ID 获取钓鱼 Bot 配置

        Args:
            bot_id: Bot ID

        Returns:
            HoneypotBotConfig 实例或 None
        """
        with self._lock:
            for bot in self._bot_configs:
                if bot.id == bot_id:
                    return bot
        return None

    def get_all_bots(self) -> List[HoneypotBotConfig]:
        """获取所有钓鱼 Bot 配置（只读副本）"""
        with self._lock:
            return [
                HoneypotBotConfig(
                    id=b.id,
                    weight=b.weight,
                    description=b.description,
                    response_delay_min_ms=b.response_delay_min_ms,
                    response_delay_max_ms=b.response_delay_max_ms,
                )
                for b in self._bot_configs
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取钓鱼 Bot 池统计"""
        with self._lock:
            distribution = {
                bot.id: bot.weight
                for bot in self._bot_configs
            }

            return {
                "total_unique": len(self._bot_configs),
                "total_draws": self._draw_count,
                "distribution": distribution,
                "weights": dict(zip(
                    [b.id for b in self._bot_configs],
                    self._weights
                )),
            }

    def clear(self) -> None:
        """清空钓鱼 Bot 池"""
        with self._lock:
            self._bot_configs.clear()
            self._weights.clear()
            self._draw_count = 0
        logger.info("钓鱼 Bot 池已清空")
