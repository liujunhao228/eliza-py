#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 项目自定义异常类模块

根据编码规范定义分层异常体系：
- 系统级异常：配置错误、初始化错误、依赖错误
- 业务级异常：对话处理错误、数据处理错误
- 外部依赖异常：第三方库调用错误

使用示例:
    # 带上下文的异常抛出
    raise TextProcessingError(
        "文本预处理失败",
        context={
            "input_length": len(text),
            "component": "text_preprocessor",
            "user_id": user_id
        }
    )
"""

from typing import Any, Dict, Optional


class AliceException(Exception):
    """
    Alice 项目异常基类

    所有自定义异常都应该继承此类，以便统一处理和追踪
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ):
        """
        初始化异常

        Args:
            message: 异常消息
            context: 上下文信息字典
            suggestion: 解决建议
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion

    def __str__(self) -> str:
        """返回格式化的异常信息"""
        parts = [self.message]
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"上下文：{context_str}")
        if self.suggestion:
            parts.append(f"建议：{self.suggestion}")
        return " | ".join(parts)


# =============================================================================
# 系统级异常
# =============================================================================

class ConfigurationError(AliceException):
    """配置相关的异常基类"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """无效配置"""
    pass


class MissingConfigurationError(ConfigurationError):
    """缺少必要配置"""
    pass


class InitializationError(AliceException):
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

class DialogueError(AliceException):
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


class DataProcessingError(AliceException):
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

class ExternalLibraryError(AliceException):
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

class DegradationError(AliceException):
    """降级相关异常"""
    pass


class UnacceptableDegradationError(DegradationError):
    """不可接受的降级（核心功能不能降级）"""
    pass
