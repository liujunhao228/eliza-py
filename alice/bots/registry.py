#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 注册中心

管理多个 Bot 实例的生命周期
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from alice.bots.config import BotConfig
from alice.bots.instance import BotInstance
from alice.services.nlp_service import NlpService
from alice.exceptions import ConfigurationError, InitializationError

logger = logging.getLogger(__name__)


class BotRegistry:
    """
    Bot 注册中心（单例模式）
    
    职责:
    - 注册和管理多个 Bot 实例
    - 提供 Bot 实例的查找和访问
    - 管理共享 NLP 服务
    """
    
    _instance: Optional['BotRegistry'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._bots: Dict[str, BotInstance] = {}
        self._nlp_service: Optional[NlpService] = None
        
        logger.info("Bot 注册中心已初始化")
    
    def _ensure_nlp_service(self, enable_ltp: bool = True):
        """确保 NLP 服务已创建"""
        if self._nlp_service is None:
            self._nlp_service = NlpService.get_instance(enable_ltp=enable_ltp)
    
    def register_bot(
        self,
        name: str,
        config: Optional[BotConfig] = None,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        **kwargs,
    ) -> BotInstance:
        """
        注册 Bot 实例
        
        Args:
            name: Bot 名称
            config: Bot 配置对象（可选）
            script_file: 脚本文件路径
            rules_file: 规则文件路径
            **kwargs: 其他配置参数
            
        Returns:
            Bot 实例
        """
        if name in self._bots:
            logger.warning(f"Bot[{name}] 已存在，将覆盖")
        
        # 创建配置
        if config is None:
            config = BotConfig(
                name=name,
                script_file=script_file,
                rules_file=rules_file,
                **kwargs,
            )
        
        # 确保 NLP 服务已创建
        self._ensure_nlp_service(enable_ltp=config.enable_ltp)
        
        # 创建 Bot 实例
        bot = BotInstance(
            config=config,
            nlp_service=self._nlp_service,
        )
        
        self._bots[name] = bot
        logger.info(f"Bot[{name}] 已注册")
        
        return bot
    
    def register_from_yaml(self, yaml_path: str) -> BotInstance:
        """
        从 YAML 配置文件注册 Bot
        
        Args:
            yaml_path: 配置文件路径
            
        Returns:
            Bot 实例
        """
        path = Path(yaml_path)
        if not path.exists():
            raise ConfigurationError(f"配置文件不存在：{yaml_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 解析配置
            config = BotConfig(
                name=data.get('name', 'unknown'),
                display_name=data.get('display_name'),
                description=data.get('description'),
                script_file=data.get('script_file'),
                rules_file=data.get('rules_file'),
                enable_ltp=data.get('enable_ltp', True),
                enable_ner=data.get('enable_ner', True),
                enable_plugins=data.get('enable_plugins', True),
                enable_logging=data.get('enable_logging', True),
                enable_hot_reload=data.get('enable_hot_reload', True),
                hot_reload_mode=data.get('hot_reload_mode', 'auto'),
                cache_size=data.get('cache_size', 100),
                custom_settings=data.get('custom_settings', {}),
            )
            
            return self.register_bot(config.name, config)
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML 配置解析失败：{e}") from e
    
    def get_bot(self, name: str) -> Optional[BotInstance]:
        """获取 Bot 实例"""
        return self._bots.get(name)
    
    def get_default_bot(self) -> Optional[BotInstance]:
        """获取默认 Bot（第一个注册的）"""
        if self._bots:
            return next(iter(self._bots.values()))
        return None
    
    def remove_bot(self, name: str) -> bool:
        """移除 Bot 实例"""
        if name not in self._bots:
            return False
        
        bot = self._bots[name]
        bot.cleanup()
        del self._bots[name]
        logger.info(f"Bot[{name}] 已移除")
        return True
    
    def list_bots(self) -> List[str]:
        """列出所有 Bot 名称"""
        return list(self._bots.keys())
    
    def get_all_bots(self) -> Dict[str, BotInstance]:
        """获取所有 Bot 实例"""
        return self._bots.copy()
    
    def get_nlp_service(self) -> Optional[NlpService]:
        """获取共享 NLP 服务"""
        return self._nlp_service
    
    def cleanup_all(self):
        """清理所有 Bot 实例"""
        for bot in self._bots.values():
            bot.cleanup()
        self._bots.clear()
        logger.info("所有 Bot 已清理")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_bots": len(self._bots),
            "bot_names": self.list_bots(),
            "nlp_service": self._nlp_service.get_stats() if self._nlp_service else None,
        }


# 便捷函数
def get_registry() -> BotRegistry:
    """获取 Bot 注册中心单例"""
    return BotRegistry()


def create_bot(
    name: str,
    script_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    **kwargs,
) -> BotInstance:
    """创建并注册 Bot 实例"""
    registry = get_registry()
    return registry.register_bot(
        name=name,
        script_file=script_file,
        rules_file=rules_file,
        **kwargs,
    )
