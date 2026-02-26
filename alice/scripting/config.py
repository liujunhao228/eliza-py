#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本配置加载器

负责从各种来源加载脚本配置：
- YAML 配置文件
- Lua 元数据文件
- 运行时动态配置
- JSON 文件

本模块仅依赖标准库和 PyYAML，确保 scripting 包的独立性。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from alice.scripting.base import ScriptConfig

logger = logging.getLogger(__name__)


class ScriptConfigLoader:
    """
    脚本配置加载器
    
    使用示例:
        loader = ScriptConfigLoader()
        
        # 从 YAML 文件加载
        configs = loader.load_from_yaml("scripts/config.yaml")
        
        # 从 Lua 元数据加载
        configs = loader.load_lua_metadata("scripts/lua/metadata.yaml")
        
        # 从目录扫描
        configs = loader.scan_directory("scripts/lua", script_type="lua")
    """
    
    def __init__(self, default_priority: int = 50):
        """
        初始化配置加载器
        
        Args:
            default_priority: 默认优先级
        """
        self.default_priority = default_priority
    
    def load_from_yaml(self, yaml_path: Union[str, Path]) -> List[ScriptConfig]:
        """
        从 YAML 配置文件加载
        
        YAML 格式:
            scripts:
              - id: greeting
                name: 问候脚本
                type: lua
                priority: 90
                path: scripts/lua/greeting.lua
                variables:
                  threshold: 0.8
              
              - id: demo
                name: Demo 脚本
                type: yaml
                priority: 50
                path: scripts/demo.yaml
        
        Args:
            yaml_path: YAML 文件路径
            
        Returns:
            脚本配置列表
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML 未安装，无法加载 YAML 配置")
            return []
        
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"配置文件不存在：{path}")
            return []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"配置文件内容为空：{path}")
                return []

            # 支持两种格式：
            # 格式 1: {'scripts': [...]} - 脚本配置列表
            # 格式 2: [{'intent': ...}, ...] - 直接的定义列表（YAML 脚本引擎格式）
            if isinstance(data, dict):
                if 'scripts' not in data:
                    logger.warning(f"配置文件缺少 'scripts' 键：{path}")
                    return []
                scripts_list = data['scripts']
            elif isinstance(data, list):
                # 直接列表格式，包装为单个脚本配置
                scripts_list = [{
                    'id': path.stem,  # 使用文件名作为脚本 ID
                    'name': path.stem,
                    'type': 'yaml',
                    'path': str(path),
                    'priority': self.default_priority,
                }]
            else:
                logger.warning(f"配置文件格式无效：{path}")
                return []

            configs = []
            for script_data in scripts_list:
                config = self._parse_script_config(script_data, path.parent)
                if config:
                    configs.append(config)

            return configs
            
        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 [{path}]: {e}")
            return []
        except Exception as e:
            logger.error(f"加载配置文件失败 [{path}]: {e}")
            return []
    
    def load_lua_metadata(self, metadata_path: Union[str, Path]) -> List[ScriptConfig]:
        """
        从 Lua 元数据文件加载
        
        YAML 格式:
            scripts:
              - name: greeting
                priority: 90
                description: 问候脚本
                variables:
                  threshold: 0.8
        
        Args:
            metadata_path: 元数据文件路径
            
        Returns:
            脚本配置列表
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML 未安装，无法加载元数据")
            return []
        
        path = Path(metadata_path)
        if not path.exists():
            logger.warning(f"元数据文件不存在：{path}")
            return []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or 'scripts' not in data:
                return []
            
            configs = []
            for script_data in data['scripts']:
                script_name = script_data.get('name', '')
                if not script_name:
                    continue
                
                # Lua 脚本路径从名称推断
                script_path = path.parent / f"{script_name}.lua"
                
                config = ScriptConfig(
                    script_id=script_name,
                    name=script_data.get('name', script_name),
                    script_type='lua',
                    priority=script_data.get('priority', self.default_priority),
                    description=script_data.get('description', ''),
                    variables=script_data.get('variables', {}),
                    max_execution_time=script_data.get('max_execution_time', 1.0),
                    sandbox_mode=script_data.get('sandbox_mode', True),
                    script_path=script_path if script_path.exists() else None,
                    metadata=script_data,
                )
                configs.append(config)
            
            return configs
            
        except Exception as e:
            logger.error(f"加载元数据失败 [{path}]: {e}")
            return []
    
    def scan_directory(
        self,
        directory: Union[str, Path],
        script_type: str = "lua",
        recursive: bool = False,
    ) -> List[ScriptConfig]:
        """
        扫描目录自动发现脚本
        
        Args:
            directory: 脚本目录
            script_type: 脚本类型 ("lua" | "yaml")
            recursive: 是否递归子目录
            
        Returns:
            脚本配置列表
        """
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            logger.warning(f"脚本目录不存在：{directory}")
            return []
        
        extension = "lua" if script_type == "lua" else "yaml"
        pattern = f"**/*.{extension}" if recursive else f"*.{extension}"
        
        configs = []
        for script_file in path.glob(pattern):
            script_id = script_file.stem
            
            # 跳过元数据文件
            if script_id == "metadata":
                continue
            
            config = ScriptConfig(
                script_id=script_id,
                name=script_id,
                script_type=script_type,
                priority=self.default_priority,
                script_path=script_file,
                description=f"{script_type.upper()} 脚本：{script_id}",
            )
            configs.append(config)
        
        return configs
    
    def from_dict(self, data: Dict[str, Any], base_path: Optional[Path] = None) -> Optional[ScriptConfig]:
        """
        从字典创建配置
        
        Args:
            data: 配置字典
            base_path: 基础路径（用于解析相对路径）
            
        Returns:
            脚本配置，失败时返回 None
        """
        return self._parse_script_config(data, base_path)
    
    def from_json(self, json_path: Union[str, Path]) -> List[ScriptConfig]:
        """
        从 JSON 文件加载
        
        Args:
            json_path: JSON 文件路径
            
        Returns:
            脚本配置列表
        """
        path = Path(json_path)
        if not path.exists():
            logger.warning(f"JSON 配置文件不存在：{path}")
            return []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return [
                    self._parse_script_config(item, path.parent) 
                    for item in data if item
                ]
            elif isinstance(data, dict) and 'scripts' in data:
                return [
                    self._parse_script_config(item, path.parent) 
                    for item in data['scripts'] if item
                ]
            return []
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误 [{path}]: {e}")
            return []
        except Exception as e:
            logger.error(f"加载 JSON 配置失败 [{path}]: {e}")
            return []
    
    def _parse_script_config(
        self, 
        data: Dict[str, Any], 
        base_path: Optional[Path] = None
    ) -> Optional[ScriptConfig]:
        """
        解析单个脚本配置
        
        Args:
            data: 配置数据
            base_path: 基础路径（用于解析相对路径）
            
        Returns:
            脚本配置，失败时返回 None
        """
        if not data:
            return None
        
        # 获取脚本 ID
        script_id = data.get('id') or data.get('name') or data.get('script_id')
        if not script_id:
            return None
        
        # 解析脚本路径
        script_path = data.get('path')
        if script_path:
            script_path = Path(script_path)
            if not script_path.is_absolute() and base_path:
                script_path = base_path / script_path
        
        return ScriptConfig(
            script_id=script_id,
            name=data.get('name', script_id),
            script_type=data.get('type', data.get('script_type', 'lua')),
            priority=data.get('priority', self.default_priority),
            enabled=data.get('enabled', True),
            description=data.get('description', ''),
            variables=data.get('variables', {}),
            max_execution_time=data.get('max_execution_time', 1.0),
            sandbox_mode=data.get('sandbox_mode', True),
            script_path=script_path,
            metadata=data,
        )


def load_scripts(
    config_path: Optional[Union[str, Path]] = None,
    script_dir: Optional[Union[str, Path]] = None,
    script_type: str = "lua",
    metadata_file: Optional[str] = "metadata.yaml",
) -> List[ScriptConfig]:
    """
    便捷函数：从配置和目录加载脚本
    
    Args:
        config_path: 配置文件路径
        script_dir: 脚本目录
        script_type: 脚本类型
        metadata_file: 元数据文件名
        
    Returns:
        脚本配置列表
    """
    loader = ScriptConfigLoader()
    configs = []
    seen_ids = set()
    
    # 从配置文件加载
    if config_path:
        for config in loader.load_from_yaml(config_path):
            if config.script_id not in seen_ids:
                configs.append(config)
                seen_ids.add(config.script_id)
    
    # 从目录扫描
    if script_dir:
        # 先加载元数据
        metadata_path = Path(script_dir) / metadata_file if metadata_file else None
        if metadata_path and metadata_path.exists():
            for config in loader.load_lua_metadata(metadata_path):
                if config.script_id not in seen_ids:
                    configs.append(config)
                    seen_ids.add(config.script_id)
        
        # 扫描目录
        for config in loader.scan_directory(script_dir, script_type):
            if config.script_id not in seen_ids:
                configs.append(config)
                seen_ids.add(config.script_id)
    
    return configs
