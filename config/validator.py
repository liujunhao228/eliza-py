#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证器模块
==============

提供配置验证功能，确保配置文件的完整性和正确性。

用法:
    validator = ConfigValidator()
    validator.add_rule('turing.server.port', lambda v: isinstance(v, int) and 0 < v < 65536)
    errors = validator.validate(config)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ValidationError:
    """配置验证错误"""
    path: str
    message: str
    severity: str = 'error'  # 'error' | 'warning'

    def __str__(self) -> str:
        level = "错误" if self.severity == 'error' else "警告"
        return f"[{level}] {self.path}: {self.message}"


class ConfigValidator:
    """
    配置验证器

    支持添加多个验证规则，对配置进行完整性校验。
    """

    def __init__(self):
        self._rules: List[tuple] = []  # (path, validator_fn, required, message)

    def add_rule(
        self,
        path: str,
        validator: Callable[[Any], bool],
        required: bool = True,
        message: str = ""
    ):
        """
        添加验证规则

        Args:
            path: 配置路径 (点分隔，如 "turing.server.port")
            validator: 验证函数，接收配置值返回布尔
            required: 是否必填
            message: 错误消息
        """
        self._rules.append((path, validator, required, message))

    def validate(self, config: Dict[str, Any]) -> List[ValidationError]:
        """
        验证配置

        Args:
            config: 配置字典

        Returns:
            验证错误列表
        """
        errors = []
        for path, validator, required, message in self._rules:
            value = self._get_nested(config, path)

            if value is None:
                if required:
                    errors.append(ValidationError(
                        path=path,
                        message=message or f"缺少必填配置：{path}",
                        severity='error'
                    ))
            elif not validator(value):
                errors.append(ValidationError(
                    path=path,
                    message=message or f"配置验证失败：{path}",
                    severity='error'
                ))

        return errors

    def validate_strict(self, config: Dict[str, Any]) -> bool:
        """
        严格验证配置 (有错误则抛出异常)

        Args:
            config: 配置字典

        Returns:
            是否验证通过

        Raises:
            ValueError: 验证失败时抛出
        """
        errors = self.validate(config)
        if errors:
            error_messages = "\n".join(str(e) for e in errors)
            raise ValueError(f"配置验证失败:\n{error_messages}")
        return True

    def has_errors(self, config: Dict[str, Any]) -> bool:
        """检查配置是否有错误"""
        return any(e.severity == 'error' for e in self.validate(config))

    def clear_rules(self):
        """清空所有验证规则"""
        self._rules.clear()

    @staticmethod
    def _get_nested(d: Dict[str, Any], path: str) -> Any:
        """获取嵌套字典的值"""
        keys = path.split('.')
        current = d
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


def build_default_validator() -> ConfigValidator:
    """
    构建默认验证器

    包含项目所需的基础验证规则。

    Returns:
        ConfigValidator 实例
    """
    validator = ConfigValidator()

    # ----- 通用配置验证 -----
    validator.add_rule(
        'debug',
        lambda v: isinstance(v, bool),
        required=False,
        message="debug 必须是布尔值"
    )
    validator.add_rule(
        'log_level',
        lambda v: isinstance(v, str) and v in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
        required=False,
        message="log_level 必须是有效的日志级别"
    )

    # ----- 路径配置验证 -----
    validator.add_rule(
        'paths.project_root',
        lambda v: isinstance(v, str),
        message="paths.project_root 必须是字符串路径"
    )
    validator.add_rule(
        'paths.bots_dir',
        lambda v: isinstance(v, str),
        required=False,
        message="paths.bots_dir 必须是字符串路径"
    )

    # ----- 模块配置验证 -----
    validator.add_rule(
        'modules.alice.config_file',
        lambda v: isinstance(v, str),
        message="modules.alice.config_file 必须是字符串路径"
    )
    validator.add_rule(
        'modules.turing.config_file',
        lambda v: isinstance(v, str),
        message="modules.turing.config_file 必须是字符串路径"
    )

    # ----- Alice 配置验证 -----
    validator.add_rule(
        'alice.enable_ltp',
        lambda v: isinstance(v, bool),
        message="alice.enable_ltp 必须是布尔值"
    )
    validator.add_rule(
        'alice.enable_ner',
        lambda v: isinstance(v, bool),
        message="alice.enable_ner 必须是布尔值"
    )
    validator.add_rule(
        'alice.enable_log',
        lambda v: isinstance(v, bool),
        message="alice.enable_log 必须是布尔值"
    )
    validator.add_rule(
        'alice.hot_reload',
        lambda v: isinstance(v, bool),
        message="alice.hot_reload 必须是布尔值"
    )
    validator.add_rule(
        'alice.script_file',
        lambda v: isinstance(v, str),
        message="alice.script_file 必须是字符串路径"
    )
    validator.add_rule(
        'alice.rules_file',
        lambda v: isinstance(v, str),
        message="alice.rules_file 必须是字符串路径"
    )
    validator.add_rule(
        'alice.context_max_items',
        lambda v: isinstance(v, int) and v > 0,
        message="alice.context_max_items 必须是正整数"
    )
    validator.add_rule(
        'alice.conversation_history_max_turns',
        lambda v: isinstance(v, int) and v > 0,
        message="alice.conversation_history_max_turns 必须是正整数"
    )

    # ----- LTP 配置验证 -----
    validator.add_rule(
        'alice.ltp.enable_cws',
        lambda v: isinstance(v, bool),
        message="alice.ltp.enable_cws 必须是布尔值"
    )
    validator.add_rule(
        'alice.ltp.cache_size',
        lambda v: isinstance(v, int) and v > 0,
        message="alice.ltp.cache_size 必须是正整数"
    )

    # ----- Turing 配置验证 -----
    validator.add_rule(
        'turing.database.url',
        lambda v: isinstance(v, str) and len(v) > 0,
        message="turing.database.url 必须是有效的数据库连接字符串"
    )
    validator.add_rule(
        'turing.server.host',
        lambda v: isinstance(v, str) and len(v) > 0,
        message="turing.server.host 必须是有效的主机地址"
    )
    validator.add_rule(
        'turing.server.port',
        lambda v: isinstance(v, int) and 0 < v < 65536,
        message="turing.server.port 必须是有效端口号 (1-65535)"
    )
    validator.add_rule(
        'turing.auth.invite_code_length',
        lambda v: isinstance(v, int) and 4 <= v <= 16,
        message="turing.auth.invite_code_length 必须在 4-16 之间"
    )
    validator.add_rule(
        'turing.auth.secret_key',
        lambda v: isinstance(v, str) and len(v) >= 16,
        message="turing.auth.secret_key 长度必须至少 16 字符 (生产环境请修改)"
    )

    # ----- 匹配配置验证 -----
    validator.add_rule(
        'turing.match.timeout',
        lambda v: isinstance(v, int) and v > 0,
        message="turing.match.timeout 必须是正整数"
    )

    # ----- Bot 池配置验证 -----
    validator.add_rule(
        'turing.bot_pool.min_instances',
        lambda v: isinstance(v, int) and v >= 0,
        message="turing.bot_pool.min_instances 必须是非负整数"
    )
    validator.add_rule(
        'turing.bot_pool.max_instances',
        lambda v: isinstance(v, int) and v > 0,
        message="turing.bot_pool.max_instances 必须是正整数"
    )
    validator.add_rule(
        'turing.bot_pool.default_template',
        lambda v: isinstance(v, str) and len(v) > 0,
        message="turing.bot_pool.default_template 必须是非空字符串"
    )

    # ----- 会话配置验证 -----
    validator.add_rule(
        'turing.session.min_chat_turns',
        lambda v: isinstance(v, int) and v >= 1,
        message="turing.session.min_chat_turns 必须至少为 1"
    )

    # ----- AI Bot 配置验证 -----
    validator.add_rule(
        'turing.ai_bot.name',
        lambda v: isinstance(v, str) and len(v) > 0,
        message="turing.ai_bot.name 必须是非空字符串"
    )
    validator.add_rule(
        'turing.ai_bot.typing_delay_base',
        lambda v: isinstance(v, (int, float)) and v >= 0,
        message="turing.ai_bot.typing_delay_base 必须是非负数"
    )
    validator.add_rule(
        'turing.ai_bot.typing_delay_per_char',
        lambda v: isinstance(v, (int, float)) and v >= 0,
        message="turing.ai_bot.typing_delay_per_char 必须是非负数"
    )

    # ----- NLP 服务配置验证 -----
    validator.add_rule(
        'turing.nlp_service.enable_ltp',
        lambda v: isinstance(v, bool),
        message="turing.nlp_service.enable_ltp 必须是布尔值"
    )
    validator.add_rule(
        'turing.nlp_service.cache_size',
        lambda v: isinstance(v, int) and v > 0,
        message="turing.nlp_service.cache_size 必须是正整数"
    )

    # ----- WebSocket 配置验证 -----
    validator.add_rule(
        'turing.websocket.ping_interval',
        lambda v: isinstance(v, int) and v > 0,
        required=False,
        message="turing.websocket.ping_interval 必须是正整数"
    )

    # ----- 积分配置验证 (可选) -----
    validator.add_rule(
        'turing.score.entry_fee',
        lambda v: isinstance(v, int) and v >= 0,
        required=False,
        message="turing.score.entry_fee 必须是非负整数"
    )
    validator.add_rule(
        'turing.score.min_free_turns',
        lambda v: isinstance(v, int) and v >= 0,
        required=False,
        message="turing.score.min_free_turns 必须是非负整数"
    )

    return validator


def build_strict_validator() -> ConfigValidator:
    """
    构建严格验证器

    在默认验证器基础上增加更多验证规则。

    Returns:
        ConfigValidator 实例
    """
    validator = build_default_validator()

    # 额外的严格验证规则
    validator.add_rule(
        'alice.ner_use_ltp',
        lambda v: isinstance(v, bool),
        message="alice.ner_use_ltp 必须是布尔值"
    )
    validator.add_rule(
        'alice.hot_reload_mode',
        lambda v: isinstance(v, str) and v in ('auto', 'manual'),
        message="alice.hot_reload_mode 必须是 'auto' 或 'manual'"
    )
    validator.add_rule(
        'turing.auth.algorithm',
        lambda v: isinstance(v, str) and v in ('HS256', 'HS384', 'HS512', 'RS256'),
        message="turing.auth.algorithm 必须是有效的 JWT 算法"
    )
    validator.add_rule(
        'turing.performance.response_timeout',
        lambda v: isinstance(v, (int, float)) and v > 0,
        message="turing.performance.response_timeout 必须是正数"
    )
    validator.add_rule(
        'turing.performance.max_input_length',
        lambda v: isinstance(v, int) and v > 0,
        message="turing.performance.max_input_length 必须是正整数"
    )

    # Bot 池配置一致性验证
    validator.add_rule(
        'turing.bot_pool',
        lambda v: not (isinstance(v, dict)) or \
                  v.get('max_instances', 0) >= v.get('min_instances', 0),
        message="turing.bot_pool.max_instances 必须 >= min_instances"
    )

    return validator


def validate_bot_configs(bot_configs: List[Dict[str, Any]]) -> List[ValidationError]:
    """
    验证 Bot 配置文件

    Args:
        bot_configs: Bot 配置列表

    Returns:
        验证错误列表
    """
    errors = []

    for i, cfg in enumerate(bot_configs):
        prefix = f"bots[{i}]"

        # 检查必填字段
        if not cfg.get('id'):
            errors.append(ValidationError(
                path=f"{prefix}.id",
                message="Bot 配置必须包含 id 字段",
                severity='error'
            ))

        if not cfg.get('name'):
            errors.append(ValidationError(
                path=f"{prefix}.name",
                message="Bot 配置必须包含 name 字段",
                severity='error'
            ))

        # 检查路径字段
        for field in ['script_file', 'rules_file']:
            if field in cfg:
                path_value = cfg[field]
                if not isinstance(path_value, str):
                    errors.append(ValidationError(
                        path=f"{prefix}.{field}",
                        message=f"{field} 必须是字符串路径",
                        severity='error'
                    ))

        # 检查数值字段
        if 'cache_size' in cfg:
            cache_size = cfg['cache_size']
            if not isinstance(cache_size, int) or cache_size <= 0:
                errors.append(ValidationError(
                    path=f"{prefix}.cache_size",
                    message="cache_size 必须是正整数",
                    severity='error'
                ))

        if 'typing_delay_base' in cfg:
            delay = cfg['typing_delay_base']
            if not isinstance(delay, (int, float)) or delay < 0:
                errors.append(ValidationError(
                    path=f"{prefix}.typing_delay_base",
                    message="typing_delay_base 必须是非负数",
                    severity='error'
                ))

        if 'typing_delay_per_char' in cfg:
            delay = cfg['typing_delay_per_char']
            if not isinstance(delay, (int, float)) or delay < 0:
                errors.append(ValidationError(
                    path=f"{prefix}.typing_delay_per_char",
                    message="typing_delay_per_char 必须是非负数",
                    severity='error'
                ))

    return errors


__all__ = [
    "ValidationError",
    "ConfigValidator",
    "build_default_validator",
    "build_strict_validator",
    "validate_bot_configs",
]
