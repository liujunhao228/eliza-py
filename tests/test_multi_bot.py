#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多 Bot 实例功能测试
"""

import sys

def test_bot_imports():
    """测试 1: 导入模块"""
    print("=" * 50)
    print("测试 1: 导入模块")
    print("=" * 50)
    try:
        from alice.bots import BotConfig, BotInstance, BotRegistry, get_registry, create_bot
        print("✅ Bot 模块导入成功")
        return True
    except Exception as e:
        print(f"❌ Bot 模块导入失败：{e}")
        return False


def test_bot_creation():
    """测试 2: 创建 Bot 实例"""
    print("\n" + "=" * 50)
    print("测试 2: 创建 Bot 实例")
    print("=" * 50)
    try:
        from alice.bots import create_bot
        
        bot = create_bot(
            name='test',
            script_file='alice/scripts/demo.yaml',
            rules_file='alice/scripts/rules/mapping.yaml',
        )
        print(f"✅ Bot 创建成功")
        print(f"   - 名称：{bot.name}")
        print(f"   - 显示名称：{bot.display_name}")
        print(f"   - 已初始化：{bot._initialized}")
        return True, bot
    except Exception as e:
        print(f"❌ Bot 创建失败：{e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_bot_respond(bot):
    """测试 3: Bot 响应"""
    print("\n" + "=" * 50)
    print("测试 3: Bot 响应")
    print("=" * 50)
    try:
        response = bot.respond('你好')
        print(f"✅ Bot 响应成功")
        print(f"   - 输入：你好")
        print(f"   - 响应：{response}")
        return True
    except Exception as e:
        print(f"❌ Bot 响应失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_bot():
    """测试 4: 多 Bot 实例"""
    print("\n" + "=" * 50)
    print("测试 4: 多 Bot 实例")
    print("=" * 50)
    try:
        from alice.bots import get_registry
        
        registry = get_registry()
        
        # 创建第二个 Bot
        bot2 = registry.register_bot(
            name='companion_test',
            script_file='config/scripts/companion_scripts.yaml',
            rules_file='config/rules/companion_rules.yaml',
        )
        
        bots = registry.list_bots()
        print(f"✅ 多 Bot 注册成功")
        print(f"   - 已注册 Bot: {bots}")
        
        # 测试两个 Bot 独立响应
        bot1 = registry.get_bot('test')
        response1 = bot1.respond('你好')
        response2 = bot2.respond('你好')
        
        print(f"   - Bot1 (test) 响应：{response1}")
        print(f"   - Bot2 (companion_test) 响应：{response2}")
        
        return True
    except Exception as e:
        print(f"❌ 多 Bot 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_nlp_sharing():
    """测试 5: NLP 服务共享"""
    print("\n" + "=" * 50)
    print("测试 5: NLP 服务共享")
    print("=" * 50)
    try:
        from alice.services.nlp_service import NlpService
        
        # 获取两个 NLP 服务实例
        service1 = NlpService.get_instance()
        service2 = NlpService.get_instance()
        
        is_same = service1 is service2
        print(f"✅ NLP 服务单例测试")
        print(f"   - 是否同一实例：{is_same}")
        
        if is_same:
            print("   ✅ NLP 服务正确实现单例模式")
            return True
        else:
            print("   ❌ NLP 服务未正确实现单例模式")
            return False
    except Exception as e:
        print(f"❌ NLP 服务测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_from_yaml():
    """测试 6: 从 YAML 配置加载 Bot"""
    print("\n" + "=" * 50)
    print("测试 6: 从 YAML 配置加载 Bot")
    print("=" * 50)
    try:
        from alice.bots import get_registry
        
        registry = get_registry()
        bot = registry.register_from_yaml('config/bots/alice.yaml')
        
        print(f"✅ 从 YAML 配置加载成功")
        print(f"   - Bot 名称：{bot.name}")
        print(f"   - 显示名称：{bot.display_name}")
        print(f"   - 描述：{bot.config.description}")
        
        return True
    except Exception as e:
        print(f"❌ YAML 配置加载失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("多 Bot 实例功能测试")
    print("=" * 50)
    
    # 测试 1: 导入模块
    if not test_bot_imports():
        sys.exit(1)
    
    # 测试 2: 创建 Bot 实例
    success, bot = test_bot_creation()
    if not success:
        sys.exit(1)
    
    # 测试 3: Bot 响应
    if not test_bot_respond(bot):
        sys.exit(1)
    
    # 测试 4: 多 Bot 实例
    if not test_multi_bot():
        sys.exit(1)
    
    # 测试 5: NLP 服务共享
    if not test_nlp_sharing():
        sys.exit(1)
    
    # 测试 6: 从 YAML 配置加载
    if not test_config_from_yaml():
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过!")
    print("=" * 50)
    
    # 清理资源
    from alice.bots import get_registry
    registry = get_registry()
    registry.cleanup_all()


if __name__ == '__main__':
    main()
