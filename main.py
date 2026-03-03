#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 聊天机器人 - 主入口文件

提供两种运行模式:
1. 命令行交互模式
2. Web 服务器模式

支持多 Bot 实例:
- 每个 Bot 实例有独立的脚本配置
- 所有 Bot 实例共享 NLP 服务
"""

import argparse
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def run_cli(bot_name: Optional[str] = None):
    """
    命令行交互模式
    
    Args:
        bot_name: 要使用的 Bot 名称，None 则使用默认 Alice Bot
    """
    from alice.bots import get_registry, create_bot
    from alice.exceptions import (
        InputValidationError,
        ScriptMatchingError,
        ResponseGenerationError,
        ConfigurationError,
        InitializationError,
    )
    
    registry = get_registry()
    
    # 创建或获取 Bot 实例
    if bot_name:
        try:
            # 尝试从配置文件加载
            config_path = f"config/bots/{bot_name}.yaml"
            bot = registry.register_from_yaml(config_path)
        except Exception as e:
            logger.warning(f"从配置文件加载 Bot[{bot_name}] 失败：{e}，使用默认配置创建")
            bot = create_bot(name=bot_name)
    else:
        # 使用默认 Alice Bot
        bot = create_bot(
            name="alice",
            script_file="alice/scripts/demo.yaml",
            rules_file="alice/scripts/rules/mapping.yaml",
            enable_ltp=True,
            enable_ner=True,
            enable_plugins=True,
            enable_logging=True,
            enable_hot_reload=True,
        )
    
    if not bot:
        print("启动失败：无法创建 Bot 实例")
        sys.exit(1)
    
    # 显示热重载状态
    hot_reload_status = bot.get_hot_reload_status()
    if hot_reload_status.get("enabled", False):
        print(f"🔄 热重载已启用 (模式：{hot_reload_status.get('mode', 'auto')})")
        print("   修改 YAML 文件后将自动重载，或输入 'reload' 手动重载")
    print()
    
    display_name = bot.display_name or bot.name.capitalize()
    print(f"🤖 {display_name} - {bot.config.description or '聊天机器人'}")
    print("=" * 50)
    greeting = bot.config.custom_settings.get("greeting", f"你好！我是{display_name}。有什么想聊的吗？")
    print(f"{display_name}: {greeting}")
    print(f"{display_name}: 输入 'quit' 或 '再见' 结束对话。\n")

    while True:
        try:
            user_input = input("你：").strip()

            # 热重载命令
            if user_input.lower() == 'reload':
                result = bot.reload_all()
                if result.success:
                    print(f"{display_name}: ✅ 重载成功！脚本：{result.script_reloaded}, 规则：{result.rules_reloaded}")
                else:
                    print(f"{display_name}: ❌ 重载失败：{result.error}")
                continue

            if user_input.lower() in ['再见', 'quit', 'exit', 'bye']:
                print(f"{display_name}: 再见！很高兴和你聊天！")
                break

            if not user_input:
                continue

            response = bot.respond(user_input)
            print(f"{display_name}: {response}")

        except (InputValidationError, ScriptMatchingError) as e:
            # 业务异常，显示友好提示
            print(f"{display_name}: {e}")
        except ResponseGenerationError as e:
            # 响应生成错误
            print(f"{display_name}: 系统出现故障，请稍后再试")
            logger.error(f"响应生成错误：{e}")
        except KeyboardInterrupt:
            print("\n{display_name}: 再见！")
            break
        except (ConfigurationError, InitializationError) as e:
            # 配置或初始化错误，终止程序
            print(f"系统错误：{e}")
            logger.critical(f"系统错误：{e}")
            sys.exit(1)
        except Exception as e:
            # 未预期的错误
            print(f"{display_name}: 系统出现未知错误，请稍后再试")
            logger.critical(f"未预期的错误：{e}", exc_info=True)
            sys.exit(1)
    
    # 清理资源
    bot.cleanup()


def run_web(host: str = '0.0.0.0', port: int = 5000, debug: bool = False, bot_names: Optional[list] = None):
    """
    Web 服务器模式
    
    Args:
        host: 监听地址
        port: 监听端口
        debug: 调试模式
        bot_names: 要加载的 Bot 名称列表
    """
    from alice.server import run_server
    run_server(host=host, port=port, debug=debug, bot_names=bot_names)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Alice - 好奇的朋友聊天机器人',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 命令行交互模式（默认 Alice Bot）
  python main.py --bot companion    # 命令行交互模式（使用 Companion Bot）
  python main.py --web              # Web 服务器模式 (默认端口 5000)
  python main.py --web --port 8080  # Web 服务器模式 (端口 8080)
  python main.py --web --bots alice,companion  # Web 服务器加载多个 Bot

可用的 Bot:
  alice       - 好奇的朋友（默认）
  companion   - 温暖的陪伴者
  therapist   - 温柔的倾听者
        """
    )

    parser.add_argument(
        '--bot',
        type=str,
        default=None,
        help='指定要使用的 Bot 名称（如：alice, companion, therapist）'
    )
    parser.add_argument(
        '--web',
        action='store_true',
        help='以 Web 服务器模式运行'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Web 服务器监听地址 (默认：0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Web 服务器监听端口 (默认：5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='开启调试模式'
    )
    parser.add_argument(
        '--bots',
        type=str,
        default=None,
        help='Web 模式下加载多个 Bot，逗号分隔（如：alice,companion,therapist）'
    )

    args = parser.parse_args()

    # 解析 --bots 参数
    bot_names = None
    if args.bots:
        bot_names = [name.strip() for name in args.bots.split(',')]

    if args.web:
        run_web(host=args.host, port=args.port, debug=args.debug, bot_names=bot_names)
    else:
        run_cli(bot_name=args.bot)


if __name__ == "__main__":
    main()
