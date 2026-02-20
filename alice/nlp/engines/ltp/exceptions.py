#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎异常类
==============

定义 LTP 引擎使用的异常类。
"""


class LtpError(Exception):
    """LTP 引擎异常基类"""
    pass


class ModelLoadError(LtpError):
    """模型加载失败"""
    pass


class AnalysisError(LtpError):
    """分析过程错误"""
    pass


__all__ = ['LtpError', 'ModelLoadError', 'AnalysisError']
