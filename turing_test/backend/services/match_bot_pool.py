"""
Bot 池服务 - 重构版

修复内容:
1. 使用 random.choices 替代低效的副本方式
2. 完善类型注解
3. 添加线程安全保护
4. 优化内存使用

功能:
1. Bot 池 (普通 Bot: Lv.1/2/3)
2. 钓鱼 Bot 池 (攻击型/可疑型)
3. 加权随机抽取（高效实现）
"""

import random
import threading
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from loguru import logger


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


class BotPool:
    """
    Bot 角色池 - 加权随机抽取（高效实现）
    
    使用 random.choices 配合权重列表，避免创建大量重复对象。
    
    支持三种等级的 Bot:
    - Lv.1 (新手 Bot): 回复慢，用词简单
    - Lv.2 (典型 AI): 语气温和，逻辑严密
    - Lv.3 (逻辑机器): 擅长数学/代码
    
    线程安全:
    - 使用 threading.Lock 保护共享状态
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Bot 池

        Args:
            config: Bot 池配置字典
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

    def _load_from_config(self, config: Dict[str, Any]) -> None:
        """从配置加载 Bot 池"""
        bots_cfg = config.get("bots", [])

        if not bots_cfg:
            logger.warning("Bot 池配置为空，使用默认配置")
            self._load_default_bots()
            return

        with self._lock:
            for bot_cfg in bots_cfg:
                try:
                    bot_id = bot_cfg.get("id", "unknown")
                    weight = float(bot_cfg.get("weight", 1.0))
                    description = bot_cfg.get("description", "")
                    name_prefix = bot_cfg.get("name_prefix")
                    delay_min = bot_cfg.get("response_delay_min_ms", 500)
                    delay_max = bot_cfg.get("response_delay_max_ms", 2000)
                    system_prompt = bot_cfg.get("system_prompt")

                    bot_config = BotConfig(
                        id=bot_id,
                        weight=weight,
                        description=description,
                        name_prefix=name_prefix,
                        response_delay_min_ms=delay_min,
                        response_delay_max_ms=delay_max,
                        system_prompt=system_prompt,
                    )
                    
                    self._bot_configs.append(bot_config)
                    self._weights.append(weight)

                    logger.debug(f"加载 Bot: {bot_id}, weight={weight}")
                    
                except Exception as e:
                    logger.error(f"加载 Bot 配置失败：{e}", exc_info=True)

    def _load_default_bots(self) -> None:
        """加载默认 Bot 配置"""
        default_bots = [
            BotConfig(id="lv1_newbie", weight=0.35, description="新手 Bot"),
            BotConfig(id="lv2_typical", weight=0.45, description="典型 AI"),
            BotConfig(id="lv3_logic", weight=0.20, description="逻辑机器"),
        ]
        
        with self._lock:
            self._bot_configs = default_bots
            self._weights = [bot.weight for bot in default_bots]

    def get_bot(self) -> BotConfig:
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


class HoneypotPool:
    """
    钓鱼 Bot 池 - 加权随机抽取（高效实现）
    
    支持两种类型的钓鱼 Bot:
    - 攻击型 (aggressive): 容易激动，会骂人
    - 可疑型 (sus): 说话像 AI，故意露破绽
    
    线程安全:
    - 使用 threading.Lock 保护共享状态
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化钓鱼 Bot 池

        Args:
            config: 钓鱼 Bot 池配置字典
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

    def _load_from_config(self, config: Dict[str, Any]) -> None:
        """从配置加载钓鱼 Bot 池"""
        bots_cfg = config.get("bots", [])

        if not bots_cfg:
            logger.warning("钓鱼 Bot 池配置为空，使用默认配置")
            self._load_default_honeypots()
            return

        with self._lock:
            for bot_cfg in bots_cfg:
                try:
                    bot_id = bot_cfg.get("id", "unknown")
                    weight = float(bot_cfg.get("weight", 1.0))
                    description = bot_cfg.get("description", "")
                    delay_min = bot_cfg.get("response_delay_min_ms", 2000)
                    delay_max = bot_cfg.get("response_delay_max_ms", 8000)

                    bot_config = HoneypotBotConfig(
                        id=bot_id,
                        weight=weight,
                        description=description,
                        response_delay_min_ms=delay_min,
                        response_delay_max_ms=delay_max,
                    )
                    
                    self._bot_configs.append(bot_config)
                    self._weights.append(weight)

                    logger.debug(f"加载钓鱼 Bot: {bot_id}, weight={weight}")
                    
                except Exception as e:
                    logger.error(f"加载钓鱼 Bot 配置失败：{e}", exc_info=True)

    def _load_default_honeypots(self) -> None:
        """加载默认钓鱼 Bot 配置"""
        default_honeypots = [
            HoneypotBotConfig(id="aggressive", weight=0.4, description="攻击型钓鱼"),
            HoneypotBotConfig(id="sus", weight=0.6, description="可疑型钓鱼"),
        ]
        
        with self._lock:
            self._bot_configs = default_honeypots
            self._weights = [bot.weight for bot in default_honeypots]

    def get_bot(self) -> HoneypotBotConfig:
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
        """根据 ID 获取钓鱼 Bot 配置"""
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


# =============================================================================
# 工厂函数（依赖注入）
# =============================================================================

# 全局单例（用于向后兼容）
_bot_pool_instance: Optional[BotPool] = None
_honeypot_pool_instance: Optional[HoneypotPool] = None


def create_bot_pool(config: Optional[Dict[str, Any]] = None) -> BotPool:
    """
    创建 Bot 池实例（推荐方式）
    
    Args:
        config: Bot 池配置
        
    Returns:
        BotPool 实例
    """
    return BotPool(config)


def create_honeypot_pool(config: Optional[Dict[str, Any]] = None) -> HoneypotPool:
    """
    创建钓鱼 Bot 池实例（推荐方式）
    
    Args:
        config: 钓鱼 Bot 池配置
        
    Returns:
        HoneypotPool 实例
    """
    return HoneypotPool(config)


def get_bot_pool(config: Optional[Dict[str, Any]] = None) -> BotPool:
    """获取全局 Bot 池实例（向后兼容）"""
    global _bot_pool_instance

    if _bot_pool_instance is None:
        _bot_pool_instance = BotPool(config)

    return _bot_pool_instance


def get_honeypot_pool(config: Optional[Dict[str, Any]] = None) -> HoneypotPool:
    """获取全局钓鱼 Bot 池实例（向后兼容）"""
    global _honeypot_pool_instance

    if _honeypot_pool_instance is None:
        _honeypot_pool_instance = HoneypotPool(config)

    return _honeypot_pool_instance


def reset_pools() -> None:
    """重置 Bot 池（用于测试）"""
    global _bot_pool_instance, _honeypot_pool_instance
    _bot_pool_instance = None
    _honeypot_pool_instance = None


__all__ = [
    # 类型
    "BotConfig",
    "HoneypotBotConfig",
    # 类
    "BotPool",
    "HoneypotPool",
    # 工厂函数
    "create_bot_pool",
    "create_honeypot_pool",
    "get_bot_pool",
    "get_honeypot_pool",
    "reset_pools",
]
