#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎配置
============

定义 LTP 引擎的配置类。

配置说明:
- 任务启用开关默认值来自 config.settings 模块
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LtpConfig:
    """LTP 引擎配置"""
    model_path: Optional[str] = None
    device: Optional[str] = None      # 'cpu', 'cuda', 'cuda:0' 等
    batch_size: int = 32
    max_length: int = 512
    cache_dir: Optional[str] = None

    # 任务启用开关
    enable_cws: bool = True
    enable_pos: bool = True
    enable_ner: bool = True
    enable_dep: bool = True
    enable_sdp: bool = True          # 语义依存分析
    enable_srl: bool = True          # 语义角色标注

    def get_enabled_tasks(self) -> List[str]:
        """获取启用的任务列表"""
        tasks = []
        if self.enable_cws:
            tasks.append('cws')
        if self.enable_pos:
            tasks.append('pos')
        if self.enable_ner:
            tasks.append('ner')
        if self.enable_dep:
            tasks.append('dep')
        if self.enable_sdp:
            tasks.append('sdp')
        if self.enable_srl:
            tasks.append('srl')
        return tasks


__all__ = ['LtpConfig']
