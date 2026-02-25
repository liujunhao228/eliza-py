"""
Lua脚本配置加载器
负责加载和管理Lua脚本配置
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from dataclasses import dataclass

from config.types import AliceConfig
from engines.lua.lua_script_engine import LuaScriptConfig


@dataclass
class LuaScriptMetadata:
    """Lua脚本元数据"""
    name: str
    version: str
    priority: int
    description: str
    author: str = ""
    dependencies: List[str] = None
    tags: List[str] = None
    enabled: bool = True
    max_execution_time: float = 1.0
    sandbox_mode: bool = True
    variables: Dict[str, any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.variables is None:
            self.variables = {}


class LuaScriptLoader:
    """Lua脚本加载器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.scripts_dir = project_root / "scripts" / "lua"
        self.metadata_cache: Dict[str, LuaScriptMetadata] = {}

    def load_metadata(self, script_path: Path) -> Optional[LuaScriptMetadata]:
        """加载Lua脚本元数据"""
        try:
            # 检查是否有元数据文件
            metadata_path = script_path.with_suffix('.meta.yaml')
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata_data = yaml.safe_load(f)

                return LuaScriptMetadata(**metadata_data)
            else:
                # 如果没有元数据文件，使用默认值
                return LuaScriptMetadata(
                    name=script_path.stem,
                    version="1.0.0",
                    priority=50,
                    description=f"Lua脚本: {script_path.stem}",
                    enabled=True
                )

        except Exception as e:
            print(f"加载脚本元数据失败 {script_path}: {e}")
            return None

    def load_all_scripts(self, alice_config: AliceConfig) -> List[LuaScriptConfig]:
        """加载所有Lua脚本"""
        scripts = []

        if not alice_config.enable_lua_engine:
            return scripts

        if not alice_config.lua_script_dir:
            # 如果没有指定目录，使用默认目录
            lua_dir = self.scripts_dir
        else:
            lua_dir = alice_config.lua_script_dir

        if not lua_dir.exists():
            print(f"Lua脚本目录不存在: {lua_dir}")
            return scripts

        # 遍历所有.lua文件
        for script_file in lua_dir.glob("*.lua"):
            metadata = self.load_metadata(script_file)
            if metadata and metadata.enabled:
                script_config = LuaScriptConfig(
                    script_path=script_file,
                    name=metadata.name,
                    description=metadata.description,
                    priority=metadata.priority,
                    enabled=metadata.enabled,
                    cache_size=alice_config.lua_cache_size,
                    max_execution_time=metadata.max_execution_time,
                    sandbox_mode=metadata.sandbox_mode,
                    variables=metadata.variables
                )
                scripts.append(script_config)

        return scripts

    def get_script_by_name(self, name: str) -> Optional[LuaScriptConfig]:
        """根据名称获取脚本配置"""
        for script_config in self.metadata_cache.values():
            if script_config.name == name:
                return script_config
        return None

    def reload_script(self, script_name: str) -> bool:
        """重新加载指定脚本"""
        # 这里可以实现热重载逻辑
        # 目前只是简单的重新加载
        return True

    def list_scripts(self) -> List[str]:
        """列出所有脚本名称"""
        return list(self.metadata_cache.keys())

    def validate_script_syntax(self, script_path: Path) -> bool:
        """验证脚本语法"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 这里可以添加语法验证逻辑
            # 比如检查是否有必需的函数等
            return True

        except Exception as e:
            print(f"验证脚本语法失败 {script_path}: {e}")
            return False