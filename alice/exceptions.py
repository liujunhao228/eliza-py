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

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


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

    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """
        将异常转换为字典格式，用于 API 响应

        Args:
            include_details: 是否包含详细信息（生产环境应设为 False）

        Returns:
            异常信息字典
        """
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }

        if include_details:
            result["context"] = self.context
            if self.suggestion:
                result["suggestion"] = self.suggestion

        return result


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


# =============================================================================
# 统一异常处理器
# =============================================================================

def handle_exception(
    exc: Exception,
    include_details: bool = False,
    fallback_message: str = "系统出现未知错误，请稍后再试"
) -> Dict[str, Any]:
    """
    统一异常处理函数

    将任意异常转换为标准化的响应格式

    Args:
        exc: 异常实例
        include_details: 是否包含详细信息（生产环境应设为 False）
        fallback_message: 非 AliceException 时的默认消息

    Returns:
        标准化错误响应字典
    """
    if isinstance(exc, AliceException):
        return exc.to_dict(include_details=include_details)

    # 非 AliceException 的异常，记录日志并返回通用错误
    logger.error(f"未预期的异常：{exc}", exc_info=True)

    return {
        "error": exc.__class__.__name__,
        "message": fallback_message if not include_details else str(exc),
    }


__all__ = [
    # 基类
    "AliceException",
    # 系统级异常
    "ConfigurationError",
    "InvalidConfigurationError",
    "MissingConfigurationError",
    "InitializationError",
    "DependencyError",
    "ResourceError",
    # 业务级异常
    "DialogueError",
    "InputValidationError",
    "ScriptMatchingError",
    "ResponseGenerationError",
    "DataProcessingError",
    "TextProcessingError",
    "FormatError",
    # 外部依赖异常
    "ExternalLibraryError",
    "LTPError",
    "JiebaError",
    # 降级相关异常
    "DegradationError",
    "UnacceptableDegradationError",
    # 工具函数
    "handle_exception",
]
