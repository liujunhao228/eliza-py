#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎配置
============

定义 LTP 引擎的配置类。

配置说明:
- 任务启用开关默认值来自 alice.config 模块，支持统一配置管理
- 可在实例化时通过参数覆盖默认值
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# 从主配置模块导入默认值
from ....config import (
    LTP_ENABLE_CWS,
    LTP_ENABLE_POS,
    LTP_ENABLE_NER,
    LTP_ENABLE_DEP,
    LTP_ENABLE_SDP,
    LTP_ENABLE_SRL,
)


@dataclass
class LtpConfig:
    """LTP 引擎配置"""
    model_path: Optional[str] = None
    device: Optional[str] = None      # 'cpu', 'cuda', 'cuda:0' 等
    batch_size: int = 32
    max_length: int = 512
    cache_dir: Optional[str] = None

    # 任务启用开关（默认值来自 alice.config）
    enable_cws: bool = LTP_ENABLE_CWS
    enable_pos: bool = LTP_ENABLE_POS
    enable_ner: bool = LTP_ENABLE_NER
    enable_dep: bool = LTP_ENABLE_DEP
    enable_sdp: bool = LTP_ENABLE_SDP          # 语义依存分析，默认关闭
    enable_srl: bool = LTP_ENABLE_SRL          # 语义角色标注，默认关闭

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
