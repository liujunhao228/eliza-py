#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 项目自定义异常类模块

根据编码规范定义分层异常体系：
- 系统级异常：配置错误、初始化错误、依赖错误
- 业务级异常：对话处理错误、数据处理错误
- 外部依赖异常：第三方库调用错误
"""


# =============================================================================
# 系统级异常
# =============================================================================

class ConfigurationError(Exception):
    """配置相关的异常基类"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """无效配置"""
    pass


class MissingConfigurationError(ConfigurationError):
    """缺少必要配置"""
    pass


class InitializationError(Exception):
    """系统初始化异常基类"""
    pass


class DependencyError(InitializationError):
    """依赖项错误"""
    pass


class ResourceError(InitializationError):
    """资源相关错误"""
    pass


# =============================================================================
# 业务级异常
# =============================================================================

class DialogueError(Exception):
    """对话处理相关异常基类"""
    pass


class InputValidationError(DialogueError):
    """输入验证失败"""
    pass


class ScriptMatchingError(DialogueError):
    """脚本匹配失败"""
    pass


class ResponseGenerationError(DialogueError):
    """响应生成失败"""
    pass


class DataProcessingError(Exception):
    """数据处理异常基类"""
    pass


class TextProcessingError(DataProcessingError):
    """文本处理错误"""
    pass


class FormatError(DataProcessingError):
    """格式错误"""
    pass


# =============================================================================
# 外部依赖异常
# =============================================================================

class ExternalLibraryError(Exception):
    """外部库调用异常基类"""
    pass


class LTPError(ExternalLibraryError):
    """LTP 相关错误"""
    pass


class JiebaError(ExternalLibraryError):
    """jieba 分词错误"""
    pass


# =============================================================================
# 降级相关异常
# =============================================================================

class DegradationError(Exception):
    """降级相关异常"""
    pass


class UnacceptableDegradationError(DegradationError):
    """不可接受的降级（核心功能不能降级）"""
    pass
