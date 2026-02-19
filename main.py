#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 聊天机器人 - 主入口文件

提供两种运行模式:
1. 命令行交互模式
2. Web 服务器模式
"""

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def run_cli():
    """命令行交互模式"""
    from alice.alice_v2 import AliceBot
    from alice.exceptions import (
        InputValidationError,
        ScriptMatchingError,
        ResponseGenerationError,
        ConfigurationError,
        InitializationError,
    )

    try:
        alice = AliceBot()
    except (ConfigurationError, InitializationError) as e:
        print(f"启动失败：{e}")
        sys.exit(1)

    print("🤖 Alice - 好奇的朋友")
    print("=" * 50)
    print("Alice: 你好！我是 Alice。有什么想聊的吗？")
    print("Alice: 输入 'quit' 或 '再见' 结束对话。\n")

    while True:
        try:
            user_input = input("你：").strip()
            if user_input.lower() in ['再见', 'quit', 'exit', 'bye']:
                print("Alice: 再见！很高兴和你聊天！")
                break

            if not user_input:
                continue

            response = alice.respond(user_input)
            print(f"Alice: {response}")

        except (InputValidationError, ScriptMatchingError) as e:
            # 业务异常，显示友好提示
            print(f"Alice: {e}")
        except ResponseGenerationError as e:
            # 响应生成错误
            print(f"Alice: 系统出现故障，请稍后再试")
            logger.error(f"响应生成错误：{e}")
        except KeyboardInterrupt:
            print("\nAlice: 再见！")
            break
        except (ConfigurationError, InitializationError) as e:
            # 配置或初始化错误，终止程序
            print(f"系统错误：{e}")
            logger.critical(f"系统错误：{e}")
            sys.exit(1)
        except Exception as e:
            # 未预期的错误
            print("Alice: 系统出现未知错误，请稍后再试")
            logger.critical(f"未预期的错误：{e}", exc_info=True)
            sys.exit(1)


def run_web(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Web 服务器模式"""
    from alice.server import run_server

    run_server(host=host, port=port, debug=debug)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Alice - 好奇的朋友聊天机器人',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py              # 命令行交互模式
  python main.py --web        # Web 服务器模式 (默认端口 5000)
  python main.py --web --port 8080  # Web 服务器模式 (端口 8080)
        """
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

    args = parser.parse_args()

    if args.web:
        run_web(host=args.host, port=args.port, debug=args.debug)
    else:
        run_cli()


if __name__ == "__main__":
    main()
