#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统测试脚本

测试统一配置系统是否正常工作。

使用方法:
    python test_config.py
"""

import sys


def test_unified_settings():
    """测试统一配置系统"""
    print("=" * 60)
    print("测试 1: 统一配置系统")
    print("=" * 60)
    
    from config import settings
    
    # 通用配置
    print("\n[通用配置]")
    print(f"  [OK] debug: {settings.debug}")
    print(f"  [OK] log_level: {settings.log_level}")
    
    # 路径配置
    print("\n[路径配置]")
    print(f"  [OK] project_root: {settings.paths.project_root}")
    print(f"  [OK] alice_dir: {settings.paths.alice_dir}")
    print(f"  [OK] turing_dir: {settings.paths.turing_dir}")
    print(f"  [OK] log_dir: {settings.paths.log_dir}")
    print(f"  [OK] data_dir: {settings.paths.data_dir}")
    
    # Alice 配置
    print("\n[Alice 配置]")
    print(f"  [OK] enable_ltp: {settings.alice.enable_ltp}")
    print(f"  [OK] enable_ner: {settings.alice.enable_ner}")
    print(f"  [OK] enable_log: {settings.alice.enable_log}")
    print(f"  [OK] hot_reload: {settings.alice.hot_reload}")
    print(f"  [OK] script_file: {settings.alice.script_file}")
    print(f"  [OK] rules_file: {settings.alice.rules_file}")
    
    # LTP 配置 (共享)
    print("\n[LTP 配置 (共享)]")
    print(f"  [OK] enable_cws: {settings.alice.ltp.enable_cws}")
    print(f"  [OK] enable_pos: {settings.alice.ltp.enable_pos}")
    print(f"  [OK] enable_ner: {settings.alice.ltp.enable_ner}")
    print(f"  [OK] enable_dep: {settings.alice.ltp.enable_dep}")
    print(f"  [OK] enable_sdp: {settings.alice.ltp.enable_sdp}")
    print(f"  [OK] enable_srl: {settings.alice.ltp.enable_srl}")
    print(f"  [OK] cache_size: {settings.alice.ltp.cache_size}")
    print(f"  [OK] max_length: {settings.alice.ltp.max_length}")
    print(f"  [OK] get_enabled_tasks: {settings.alice.ltp.get_enabled_tasks()}")
    
    # Turing 配置
    print("\n[Turing 配置]")
    print(f"  [OK] server.host: {settings.turing.server.host}")
    print(f"  [OK] server.port: {settings.turing.server.port}")
    print(f"  [OK] database.url: {settings.turing.database.url}")
    print(f"  [OK] auth.invite_code_length: {settings.turing.auth.invite_code_length}")
    print(f"  [OK] auth.initial_score: {settings.turing.auth.initial_score}")
    print(f"  [OK] match.timeout: {settings.turing.match.timeout}")
    print(f"  [OK] ai_bot.name: {settings.turing.ai_bot.name}")
    print(f"  [OK] session.min_chat_turns: {settings.turing.session.min_chat_turns}")
    print(f"  [OK] nlp_service.enable_ltp: {settings.turing.nlp_service.enable_ltp}")
    print(f"  [OK] nlp_service.cache_size: {settings.turing.nlp_service.cache_size}")
    print(f"  [OK] bot_pool.min_instances: {settings.turing.bot_pool.min_instances}")
    print(f"  [OK] bot_pool.max_instances: {settings.turing.bot_pool.max_instances}")
    print(f"  [OK] alice_bot.script_file: {settings.turing.alice_bot.script_file}")
    print(f"  [OK] performance.response_timeout: {settings.turing.performance.response_timeout}")
    print(f"  [OK] performance.max_input_length: {settings.turing.performance.max_input_length}")
    
    # 新增配置项
    print("\n[新增配置项]")
    print(f"  [OK] websocket.ping_interval: {settings.turing.websocket.ping_interval}")
    print(f"  [OK] websocket.ping_timeout: {settings.turing.websocket.ping_timeout}")
    print(f"  [OK] log.level: {settings.turing.log.level}")
    print(f"  [OK] log.file: {settings.turing.log.file}")
    
    print("\n[PASS] 统一配置系统测试通过")
    return True


def test_turing_compat():
    """测试 Turing 向后兼容配置"""
    print("\n" + "=" * 60)
    print("测试 2: Turing 向后兼容配置")
    print("=" * 60)
    
    from turing_test.backend.config import (
        settings,
        APP_NAME,
        HOST,
        PORT,
        DATABASE_URL,
        ENABLE_LTP,
        LOG_LEVEL,
    )
    
    print("\n[模块级常量]")
    print(f"  [OK] APP_NAME: {APP_NAME}")
    print(f"  [OK] HOST: {HOST}")
    print(f"  [OK] PORT: {PORT}")
    print(f"  [OK] DATABASE_URL: {DATABASE_URL}")
    print(f"  [OK] ENABLE_LTP: {ENABLE_LTP}")
    print(f"  [OK] LOG_LEVEL: {LOG_LEVEL}")
    
    print("\n[settings 对象属性]")
    print(f"  [OK] settings.APP_NAME: {settings.APP_NAME}")
    print(f"  [OK] settings.HOST: {settings.HOST}")
    print(f"  [OK] settings.PORT: {settings.PORT}")
    print(f"  [OK] settings.DEBUG: {settings.DEBUG}")
    print(f"  [OK] settings.LOG_LEVEL: {settings.LOG_LEVEL}")
    
    print("\n[PASS] Turing 向后兼容配置测试通过")
    return True


def test_config_manager():
    """测试配置管理器"""
    print("\n" + "=" * 60)
    print("测试 3: 配置管理器")
    print("=" * 60)
    
    from turing_test.backend.config_manager import get_config_manager, reset_config_manager
    
    # 重置以确保干净状态
    reset_config_manager()
    
    config = get_config_manager()
    
    print("\n[获取配置]")
    port = config.get('turing.server.port')
    print(f"  [OK] get('turing.server.port'): {port}")
    assert port == 8000, f"期望 8000, 实际 {port}"
    
    enable_ltp = config.get('alice.enable_ltp')
    print(f"  [OK] get('alice.enable_ltp'): {enable_ltp}")
    assert enable_ltp is True, f"期望 True, 实际 {enable_ltp}"
    
    print("\n[设置配置 (运行时)]")
    config.set('turing.server.port', 9000)
    new_port = config.get('turing.server.port')
    print(f"  [OK] set('turing.server.port', 9000) -> get(): {new_port}")
    assert new_port == 9000, f"期望 9000, 实际 {new_port}"
    
    # 重置
    config.reload()
    reset_port = config.get('turing.server.port')
    print(f"  [OK] reload() -> get('turing.server.port'): {reset_port}")
    assert reset_port == 8000, f"期望 8000, 实际 {reset_port}"
    
    print("\n[PASS] 配置管理器测试通过")
    return True


def test_alice_import():
    """测试 Alice 模块导入"""
    print("\n" + "=" * 60)
    print("测试 4: Alice 模块导入")
    print("=" * 60)
    
    from alice.alice_v2 import AliceBot
    from config import settings
    
    print(f"\n[AliceBot 初始化]")
    print(f"  [OK] AliceBot 类已导入")
    print(f"  [OK] settings.alice.enable_ltp: {settings.alice.enable_ltp}")
    print(f"  [OK] settings.alice.hot_reload: {settings.alice.hot_reload}")
    
    print("\n[PASS] Alice 模块导入测试通过")
    return True


def test_env_override():
    """测试环境变量覆盖"""
    print("\n" + "=" * 60)
    print("测试 5: 环境变量覆盖 (仅演示)")
    print("=" * 60)
    
    import os
    print("\n[环境变量覆盖示例]")
    print("  设置：CONFIG_TURING_SERVER_PORT=9999")
    
    # 注意：由于 settings 在模块导入时已加载，运行时设置环境变量不会影响已加载的配置
    # 这里仅演示配置系统支持环境变量覆盖
    print("  [INFO] 注意：环境变量必须在 Python 进程启动前设置才能生效")
    print("  [INFO] 示例：CONFIG_TURING_SERVER_PORT=9999 python test_config.py")
    
    print("\n[PASS] 环境变量覆盖测试通过 (文档演示)")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("配置系统测试套件")
    print("=" * 60)
    
    tests = [
        ("统一配置系统", test_unified_settings),
        ("Turing 向后兼容", test_turing_compat),
        ("配置管理器", test_config_manager),
        ("Alice 模块导入", test_alice_import),
        ("环境变量覆盖", test_env_override),
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
