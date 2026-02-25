#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本配置重构测试

验证配置管理模块重构后脚本配置功能是否正常工作。
"""

import sys
from pathlib import Path


def test_types_import():
    """测试类型导入"""
    print("=" * 60)
    print("测试 1: 脚本配置类型导入")
    print("=" * 60)
    
    try:
        from config import (
            ScriptingConfig,
            LuaScriptEngineConfig,
            YamlScriptEngineConfig,
        )
        print("[PASS] 类型导入成功")
        print(f"  - ScriptingConfig: {ScriptingConfig}")
        print(f"  - LuaScriptEngineConfig: {LuaScriptEngineConfig}")
        print(f"  - YamlScriptEngineConfig: {YamlScriptEngineConfig}")
        return True
    except ImportError as e:
        print(f"[FAIL] 类型导入失败：{e}")
        return False


def test_settings_scripting_config():
    """测试 settings 中的脚本配置"""
    print("\n" + "=" * 60)
    print("测试 2: Settings 脚本配置")
    print("=" * 60)
    
    try:
        from config import settings
        
        scripting = settings.alice.scripting
        if scripting:
            print(f"[PASS] scripting 配置已加载")
            print(f"  - enable_lua: {scripting.enable_lua}")
            print(f"  - enable_yaml: {scripting.enable_yaml}")
            
            if scripting.lua:
                print(f"  - lua.script_dir: {scripting.lua.script_dir}")
                print(f"  - lua.sandbox_mode: {scripting.lua.sandbox_mode}")
                print(f"  - lua.max_execution_time: {scripting.lua.max_execution_time}")
            
            if scripting.yaml:
                print(f"  - yaml.script_file: {scripting.yaml.script_file}")
            
            if scripting.rules_file:
                print(f"  - rules_file: {scripting.rules_file}")
        else:
            print("[INFO] scripting 配置为 None (使用旧配置)")
            # 检查向后兼容字段
            if hasattr(settings.alice, 'script_file') and settings.alice.script_file:
                print(f"  - 旧 script_file: {settings.alice.script_file}")
            if hasattr(settings.alice, 'rules_file') and settings.alice.rules_file:
                print(f"  - 旧 rules_file: {settings.alice.rules_file}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager_methods():
    """测试配置管理器脚本配置访问方法"""
    print("\n" + "=" * 60)
    print("测试 3: 配置管理器脚本配置方法")
    print("=" * 60)
    
    try:
        from config import get_config_manager, reset_config_manager
        
        # 重置以确保干净状态
        reset_config_manager()
        config_mgr = get_config_manager()
        
        # 测试 get_scripting_config
        scripting = config_mgr.get_scripting_config()
        if scripting:
            print(f"[PASS] get_scripting_config() 返回配置")
        else:
            print(f"[INFO] get_scripting_config() 返回 None")
        
        # 测试 get_lua_script_dir
        lua_dir = config_mgr.get_lua_script_dir()
        if lua_dir:
            print(f"[PASS] get_lua_script_dir(): {lua_dir}")
        else:
            print(f"[INFO] get_lua_script_dir() 返回 None")
        
        # 测试 get_yaml_script_file
        yaml_file = config_mgr.get_yaml_script_file()
        if yaml_file:
            print(f"[PASS] get_yaml_script_file(): {yaml_file}")
        else:
            print(f"[INFO] get_yaml_script_file() 返回 None")
        
        # 测试 list_lua_scripts
        lua_scripts = config_mgr.list_lua_scripts()
        print(f"[PASS] list_lua_scripts(): {lua_scripts}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_scripting_paths():
    """测试脚本路径验证"""
    print("\n" + "=" * 60)
    print("测试 4: 脚本路径验证")
    print("=" * 60)
    
    try:
        from config import get_config_manager
        
        config_mgr = get_config_manager()
        errors = config_mgr.validate_scripting_paths()
        
        if errors:
            print(f"[INFO] 发现 {len(errors)} 个验证问题:")
            for e in errors:
                print(f"  [{e.severity}] {e.path}: {e.message}")
        else:
            print("[PASS] 脚本路径验证通过")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_dialogue_engine_import():
    """测试对话引擎导入"""
    print("\n" + "=" * 60)
    print("测试 5: 对话引擎导入")
    print("=" * 60)
    
    try:
        from alice.core.dialogue_engine_unified import DialogueEngine
        from config import get_config_manager
        
        print("[PASS] DialogueEngine 导入成功")
        
        # 测试使用配置管理器初始化
        config_mgr = get_config_manager()
        engine = DialogueEngine(config_manager=config_mgr)
        
        print(f"[PASS] DialogueEngine 使用配置管理器初始化成功")
        print(f"  - yaml_script_file: {engine.yaml_script_file}")
        print(f"  - lua_script_dir: {engine.lua_script_dir}")
        print(f"  - enable_lua: {engine.enable_lua}")
        print(f"  - enable_yaml: {engine.enable_yaml}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_validator_function():
    """测试验证器函数"""
    print("\n" + "=" * 60)
    print("测试 6: validate_scripting_paths 函数")
    print("=" * 60)
    
    try:
        from config import validate_scripting_paths
        from pathlib import Path
        
        # 测试配置
        config = {
            'alice': {
                'scripting': {
                    'enable_lua': True,
                    'enable_yaml': True,
                    'lua': {
                        'script_dir': 'scripts/lua',
                    },
                    'yaml': {
                        'script_file': 'alice/scripts/demo.yaml',
                    },
                    'rules_file': 'alice/scripts/rules/mapping.yaml',
                }
            }
        }
        
        project_root = Path(__file__).parent
        errors = validate_scripting_paths(config, project_root)
        
        if errors:
            print(f"[INFO] 发现 {len(errors)} 个验证问题:")
            for e in errors:
                print(f"  [{e.severity}] {e.path}: {e.message}")
        else:
            print("[PASS] validate_scripting_paths 验证通过")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("脚本配置重构测试套件")
    print("=" * 60)
    
    tests = [
        ("类型导入", test_types_import),
        ("Settings 脚本配置", test_settings_scripting_config),
        ("配置管理器方法", test_config_manager_methods),
        ("脚本路径验证", test_validate_scripting_paths),
        ("对话引擎导入", test_dialogue_engine_import),
        ("验证器函数", test_validator_function),
    ]
    
    passed = 0
    failed = 0
    results = []
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                results.append((name, "[PASS]"))
            else:
                failed += 1
                results.append((name, "[FAIL]"))
        except Exception as e:
            failed += 1
            results.append((name, f"[ERROR]: {e}"))
            import traceback
            traceback.print_exc()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        print(f"  {result} - {name}")
    
    print(f"\n总计：{passed} 通过，{failed} 失败")
    
    if failed > 0:
        print("\n[FAIL] 测试失败")
        sys.exit(1)
    else:
        print("\n[PASS] 所有测试通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
