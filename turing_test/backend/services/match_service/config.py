"""
匹配服务配置管理

集中管理匹配相关配置，支持从全局配置加载。
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class MatchConfig:
    """
    匹配服务配置

    Attributes:
        human_probability: 真人匹配概率 (默认 70%)
        bot_probability: Bot 匹配概率 (默认 30%)
        honeypot_in_bot_rate: 钓鱼 Bot 在 Bot 局中的比例 (默认 15%)
        timeout_seconds: 真人匹配超时时间 (秒)
        fake_delay_min_ms: 假装延迟最小值 (毫秒)
        fake_delay_max_ms: 假装延迟最大值 (毫秒)
        cleanup_interval_seconds: 清理任务间隔 (秒)
    """
    human_probability: float = 0.70
    bot_probability: float = 0.30
    honeypot_in_bot_rate: float = 0.15
    timeout_seconds: int = 8  # 真人匹配超时时间（秒）- 缩短至 8 秒，确保前端能收到响应
    fake_delay_min_ms: int = 1000
    fake_delay_max_ms: int = 3000
    cleanup_interval_seconds: int = 5

    @classmethod
    def from_settings(cls, settings: Any) -> "MatchConfig":
        """
        从全局配置加载

        Args:
            settings: 全局配置对象

        Returns:
            MatchConfig 实例
        """
        try:
            honeypot_cfg = settings.turing.match.honeypot
            if hasattr(honeypot_cfg, 'probability_in_bot_matches'):
                honeypot_rate = honeypot_cfg.probability_in_bot_matches
            elif isinstance(honeypot_cfg, dict):
                honeypot_rate = honeypot_cfg.get('probability_in_bot_matches', 0.15)
            else:
                honeypot_rate = 0.15
        except (AttributeError, KeyError):
            honeypot_rate = 0.15

        return cls(
            human_probability=getattr(settings.turing.match, 'human_probability', 0.70),
            bot_probability=getattr(settings.turing.match, 'bot_probability', 0.30),
            honeypot_in_bot_rate=honeypot_rate,
            timeout_seconds=getattr(settings.turing.match, 'timeout_seconds', 10),
            fake_delay_min_ms=getattr(settings.turing.match, 'fake_delay_min_ms', 1000),
            fake_delay_max_ms=getattr(settings.turing.match, 'fake_delay_max_ms', 3000),
        )

    def validate(self) -> None:
        """
        验证配置有效性

        Raises:
            ValueError: 配置无效时
        """
        if not 0 <= self.human_probability <= 1:
            raise ValueError(f"human_probability 必须在 0-1 之间：{self.human_probability}")

        if not 0 <= self.bot_probability <= 1:
            raise ValueError(f"bot_probability 必须在 0-1 之间：{self.bot_probability}")

        if not 0 <= self.honeypot_in_bot_rate <= 1:
            raise ValueError(f"honeypot_in_bot_rate 必须在 0-1 之间：{self.honeypot_in_bot_rate}")

        if self.human_probability + self.bot_probability > 1:
            raise ValueError(
                f"human_probability + bot_probability 不能大于 1: "
                f"{self.human_probability} + {self.bot_probability}"
            )

        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds 必须大于 0: {self.timeout_seconds}")

        if self.fake_delay_min_ms < 0:
            raise ValueError(f"fake_delay_min_ms 不能为负：{self.fake_delay_min_ms}")

        if self.fake_delay_max_ms < self.fake_delay_min_ms:
            raise ValueError(
                f"fake_delay_max_ms 必须大于等于 fake_delay_min_ms: "
                f"{self.fake_delay_max_ms} >= {self.fake_delay_min_ms}"
            )

    def get_bot_thresholds(self) -> tuple[float, float]:
        """
        计算 Bot 匹配的概率阈值

        Returns:
            (honeypot_threshold, human_threshold) 元组
        """
        honeypot_threshold = self.honeypot_in_bot_rate * self.bot_probability
        human_threshold = honeypot_threshold + self.human_probability
        return honeypot_threshold, human_threshold
