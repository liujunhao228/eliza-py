#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bots 包

提供多 Bot 实例管理功能
"""

from alice.bots.config import BotConfig
from alice.bots.instance import BotInstance
from alice.bots.registry import BotRegistry, get_registry, create_bot

__all__ = [
    'BotConfig',
    'BotInstance',
    'BotRegistry',
    'get_registry',
    'create_bot',
]
