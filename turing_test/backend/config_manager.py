"""
配置管理器

基于统一配置系统的包装器，提供运行时配置热更新功能。

注意：
- 基础配置来自 config.yaml
- 运行时修改仅在当前会话有效
- 持久化修改需要更新 config.yaml 文件
"""

import threading
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from config import settings as base_settings


class ConfigManager:
    """
    配置管理器

    提供运行时配置热更新功能，基于统一配置系统。
    
    设计说明:
    - 基础配置来自 config.yaml (通过 config.settings)
    - 运行时覆盖存储在内存中
    - 支持 get/set 接口访问嵌套配置
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径 (仅用于向后兼容，实际不使用)
        """
        self.config_file = config_file
        self._overrides: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        logger.info("配置管理器已初始化 (基于统一配置系统)")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持嵌套键（用点分隔）

        优先级:
        1. 运行时覆盖值
        2. 统一配置 (config.settings)

        Args:
            key: 配置键，如 "turing.server.port" 或 "alice.enable_ltp"
            default: 默认值

        Returns:
            配置值
        """
        # 先检查运行时覆盖
        with self._lock:
            override_value = self._get_nested(self._overrides, key)
            if override_value is not None:
                return override_value
        
        # 从统一配置获取
        return self._get_from_settings(key, default)

    def _get_from_settings(self, key: str, default: Any = None) -> Any:
        """从统一配置获取值"""
        keys = key.split(".")
        
        # 处理 turing.* 和 alice.* 路径
        if keys[0] in ("turing", "alice", "paths", "shared_ltp"):
            try:
                value = getattr(base_settings, keys[0])
                for k in keys[1:]:
                    if isinstance(value, dict):
                        value = value.get(k)
                    else:
                        value = getattr(value, k, None)
                return value if value is not None else default
            except (AttributeError, KeyError):
                return default
        
        # 通用路径
        return default

    def _get_nested(self, d: Dict[str, Any], key: str) -> Any:
        """获取嵌套字典的值"""
        keys = key.split(".")
        value = d
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value

    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值（运行时覆盖）

        注意：此修改仅在当前会话有效

        Args:
            key: 配置键，如 "turing.server.port"
            value: 配置值

        Returns:
            是否设置成功
        """
        keys = key.split(".")
        try:
            with self._lock:
                config = self._overrides
                for k in keys[:-1]:
                    if k not in config or not isinstance(config[k], dict):
                        config[k] = {}
                    config = config[k]
                config[keys[-1]] = value
            logger.debug(f"配置已更新 (运行时): {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"设置配置失败：{e}")
            return False

    def update(self, new_config: Dict[str, Any]) -> bool:
        """
        批量更新配置（运行时覆盖）

        Args:
            new_config: 新配置字典

        Returns:
            是否更新成功
        """
        try:
            with self._lock:
                self._merge_recursive(self._overrides, new_config)
            logger.info(f"配置已批量更新 ({len(str(new_config))} 项)")
            return True
        except Exception as e:
            logger.error(f"批量更新配置失败：{e}")
            return False

    def _merge_recursive(self, target: Dict[str, Any], source: Dict[str, Any]):
        """递归合并配置"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_recursive(target[key], value)
            else:
                target[key] = value

    def reload(self) -> bool:
        """
        重新加载配置文件

        注意：此方法仅清除运行时覆盖，不会重新读取 config.yaml
        如需重新读取 config.yaml，需要重启应用

        Returns:
            是否重新加载成功
        """
        with self._lock:
            self._overrides.clear()
        logger.info("配置已重置 (清除运行时覆盖)")
        return True

    def get_all(self) -> Dict[str, Any]:
        """
        获取完整配置（包含运行时覆盖）

        Returns:
            配置字典
        """
        # 注意：这里返回的是简化版配置，不是完整的 config.settings
        with self._lock:
            return self._overrides.copy()

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节

        Args:
            section: 配置节名称，如 "turing" 或 "alice"

        Returns:
            配置节字典
        """
        # 优先返回运行时覆盖
        override = self._get_nested(self._overrides, section)
        if override and isinstance(override, dict):
            return override.copy()
        
        # 否则返回空字典（实际使用应直接访问 config.settings）
        logger.warning(
            f"get_section('{section}') 返回空字典，建议直接使用 config.settings.{section}"
        )
        return {}

    def save_config(self, config_file: str) -> bool:
        """
        保存配置到文件

        注意：此方法已废弃，因为配置应通过 config.yaml 管理

        Args:
            config_file: 配置文件路径

        Returns:
            是否保存成功
        """
        logger.warning(
            "save_config() 已废弃，配置应通过 config.yaml 文件管理"
        )
        return False

    def load_config(self, config_file: str) -> bool:
        """
        从文件加载配置

        注意：此方法已废弃，因为配置应通过 config.yaml 管理

        Args:
            config_file: 配置文件路径

        Returns:
            是否加载成功
        """
        logger.warning(
            "load_config() 已废弃，配置应通过 config.yaml 文件管理"
        )
        return False


# =============================================================================
# 全局配置实例
# =============================================================================

_config_manager: Optional[ConfigManager] = None
_config_lock = threading.Lock()


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    获取配置管理器实例

    Args:
        config_file: 配置文件路径 (仅用于向后兼容)

    Returns:
        ConfigManager 实例
    """
    global _config_manager

    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigManager(config_file)

    return _config_manager


def reset_config_manager():
    """重置配置管理器（用于测试）"""
    global _config_manager
    with _config_lock:
        _config_manager = None
