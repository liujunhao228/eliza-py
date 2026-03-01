"""
普通 Bot 池

使用加权随机抽取，支持三种等级的 Bot:
- Lv.1 (新手 Bot): 回复慢，用词简单
- Lv.2 (典型 AI): 语气温和，逻辑严密
- Lv.3 (逻辑机器): 擅长数学/代码
"""

import random
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from .base import BotPoolBase, BotConfig


@dataclass
class BotPoolConfig:
    """
    Bot 池配置

    Attributes:
        bots: Bot 配置列表
    """
    bots: List[BotConfig]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotPoolConfig":
        """
        从字典创建配置

        Args:
            data: 配置字典

        Returns:
            BotPoolConfig 实例
        """
        bots_cfg = data.get("bots", [])
        bots = []

        for bot_cfg in bots_cfg:
            bot = BotConfig(
                id=bot_cfg.get("id", "unknown"),
                weight=float(bot_cfg.get("weight", 1.0)),
                description=bot_cfg.get("description", ""),
                name_prefix=bot_cfg.get("name_prefix"),
                response_delay_min_ms=bot_cfg.get("response_delay_min_ms", 500),
                response_delay_max_ms=bot_cfg.get("response_delay_max_ms", 2000),
                system_prompt=bot_cfg.get("system_prompt"),
            )
            bots.append(bot)

        return cls(bots=bots)

    @classmethod
    def default(cls) -> "BotPoolConfig":
        """创建默认配置"""
        return cls(
            bots=[
                BotConfig(id="lv1_newbie", weight=0.35, description="新手 Bot"),
                BotConfig(id="lv2_typical", weight=0.45, description="典型 AI"),
                BotConfig(id="lv3_logic", weight=0.20, description="逻辑机器"),
            ]
        )


class BotPool(BotPoolBase):
    """
    Bot 角色池 - 加权随机抽取

    使用 random.choices 配合权重列表，避免创建大量重复对象。

    线程安全:
    - 使用 threading.Lock 保护共享状态
    """

    def __init__(self, config: Optional[BotPoolConfig] = None):
        """
        初始化 Bot 池

        Args:
            config: Bot 池配置
        """
        # 存储唯一的 Bot 配置
        self._bot_configs: List[BotConfig] = []
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
            self._load_default_bots()

        logger.info(f"Bot 池初始化完成，共 {len(self._bot_configs)} 个唯一 Bot 配置")

    def _load_from_config(self, config: BotPoolConfig) -> None:
        """从配置加载 Bot 池"""
        if not config.bots:
            logger.warning("Bot 池配置为空，使用默认配置")
            self._load_default_bots()
            return

        with self._lock:
            self._bot_configs = config.bots.copy()
            self._weights = [bot.weight for bot in config.bots]

            for bot in config.bots:
                logger.debug(f"加载 Bot: {bot.id}, weight={bot.weight}")

    def _load_default_bots(self) -> None:
        """加载默认 Bot 配置"""
        default_config = BotPoolConfig.default()
        with self._lock:
            self._bot_configs = default_config.bots
            self._weights = [bot.weight for bot in default_config.bots]

    def draw(self) -> BotConfig:
        """
        随机抽取一个 Bot（加权）

        使用 random.choices 实现高效的加权随机抽取。

        Returns:
            BotConfig 实例
        """
        with self._lock:
            if not self._bot_configs:
                logger.warning("Bot 池为空，返回默认 Bot")
                return BotConfig(id="lv2_typical", weight=1.0, description="默认 Bot")

            # 使用 random.choices 进行加权随机抽取
            selected = random.choices(
                population=self._bot_configs,
                weights=self._weights,
                k=1
            )[0]

            self._draw_count += 1

            # 返回副本，避免外部修改
            return BotConfig(
                id=selected.id,
                weight=selected.weight,
                description=selected.description,
                name_prefix=selected.name_prefix,
                response_delay_min_ms=selected.response_delay_min_ms,
                response_delay_max_ms=selected.response_delay_max_ms,
                system_prompt=selected.system_prompt,
            )

    def get_bot_by_id(self, bot_id: str) -> Optional[BotConfig]:
        """
        根据 ID 获取 Bot 配置

        Args:
            bot_id: Bot ID

        Returns:
            BotConfig 实例或 None
        """
        with self._lock:
            for bot in self._bot_configs:
                if bot.id == bot_id:
                    return bot
        return None

    def get_all_bots(self) -> List[BotConfig]:
        """获取所有 Bot 配置（只读副本）"""
        with self._lock:
            return [
                BotConfig(
                    id=b.id,
                    weight=b.weight,
                    description=b.description,
                    name_prefix=b.name_prefix,
                    response_delay_min_ms=b.response_delay_min_ms,
                    response_delay_max_ms=b.response_delay_max_ms,
                    system_prompt=b.system_prompt,
                )
                for b in self._bot_configs
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取 Bot 池统计"""
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
        """清空 Bot 池"""
        with self._lock:
            self._bot_configs.clear()
            self._weights.clear()
            self._draw_count = 0
        logger.info("Bot 池已清空")
