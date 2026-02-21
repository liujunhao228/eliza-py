"""
配置管理器
统一管理所有配置，支持热更新
"""

import json
import threading
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    配置管理器
    统一管理所有配置，支持热更新
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        if config_file:
            self.load_config(config_file)
        else:
            self._set_default_config()
    
    def _set_default_config(self):
        """设置默认配置"""
        self._config = {
            # NLP服务配置
            'nlp_service': {
                'enable_ltp': False,
                'cache_size': 1000,
                'cache_ttl': 3600,
            },
            
            # Bot池配置
            'bot_pool': {
                'min_instances': 2,
                'max_instances': 10,
                'idle_timeout': 300,
                'max_concurrent': 100,
            },
            
            # AliceBot配置
            'alice_bot': {
                'enable_plugins': True,
                'cache_size': 50,
                'context_max_turns': 20,
                'script_file': 'alice/scripts/demo.yaml',
                'rules_file': 'alice/scripts/rules/mapping.yaml',
            },
            
            # 性能配置
            'performance': {
                'response_timeout': 10.0,
                'max_input_length': 500,
                'base_typing_delay': 0.5,
                'chars_per_second': 5.0,
            },
        }
    
    def load_config(self, config_file: str):
        """从文件加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            with self._lock:
                self._config.update(loaded_config)
        except FileNotFoundError:
            print(f"配置文件 {config_file} 不存在，使用默认配置")
            self._set_default_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            self._set_default_config()
    
    def save_config(self, config_file: str):
        """保存配置到文件"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持嵌套键（用点分隔）"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值，支持嵌套键（用点分隔）"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        with self._lock:
            config[keys[-1]] = value
    
    def update(self, new_config: Dict[str, Any]):
        """批量更新配置"""
        with self._lock:
            self._update_recursive(self._config, new_config)
    
    def _update_recursive(self, target: Dict[str, Any], source: Dict[str, Any]):
        """递归更新配置"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_recursive(target[key], value)
            else:
                target[key] = value
    
    def reload(self):
        """重新加载配置文件"""
        if self.config_file:
            self.load_config(self.config_file)