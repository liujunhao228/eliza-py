#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eliza-Py 项目主入口

提供 CLI 命令和服务器启动功能。

使用方法:
    # 显示帮助
    python main.py --help

    # 启动 Alice 聊天机器人
    python main.py alice

    # 启动 Turing 测试后端
    python main.py turing

    # 运行测试
    python main.py test

    # 检查配置
    python main.py check-config
"""

import argparse
import sys
import os
import shutil
from pathlib import Path

# 第三方库导入
import uvicorn
import pytest

# 项目模块导入
from config import get_config_manager


def cmd_alice(args):
    """启动 Alice 聊天机器人服务器"""
    print("启动 Alice 聊天机器人...")
    from alice.server import app

    config = {
        "host": args.host or "0.0.0.0",
        "port": args.port or 5000,
        "reload": args.reload or False,
    }

    print(f"监听地址：http://{config['host']}:{config['port']}")
    print(f"Debug 模式：{config['reload']}")
    print()

    uvicorn.run(
        "alice.server:app",
        host=config["host"],
        port=config["port"],
        reload=config["reload"],
    )


def cmd_turing(args):
    """启动 Turing 测试后端"""
    print("启动 Turing 测试后端...")

    config_mgr = get_config_manager()
    host = args.host or config_mgr.get('turing.server.host', '0.0.0.0')
    port = args.port or config_mgr.get('turing.server.port', 8000)
    reload_mode = args.reload or config_mgr.get('debug', False)
    log_level = config_mgr.get('log_level', 'INFO')

    print(f"监听地址：http://{host}:{port}")
    print(f"API 文档：http://{host}:{port}/docs")
    print(f"Debug 模式：{reload_mode}")
    print()

    uvicorn.run(
        "turing_test.backend.main:app",
        host=host,
        port=port,
        reload=reload_mode,
        log_level=log_level.lower(),
    )


def cmd_test(args):
    """运行测试"""
    test_dir = args.test_dir or "tests"
    pytest_args = [test_dir, "-v"]

    if args.coverage:
        pytest_args.extend(["--cov=.", "--cov-report=term-missing"])

    if args.keyword:
        pytest_args.extend(["-k", args.keyword])

    sys.exit(pytest.main(pytest_args))


def is_strong_secret_key(key: str) -> tuple[bool, str]:
    """
    检查密钥强度

    Args:
        key: 待检查的密钥

    Returns:
        (是否强密钥，提示信息)
    """
    if not key:
        return False, "密钥不能为空"

    if len(key) < 32:
        return False, f"密钥长度不足 32 字符（当前：{len(key)}）"

    # 检查默认弱密钥
    weak_keys = [
        'your-secret-key-change-in-production',
        'CHANGE_ME_IN_PRODUCTION',
        'secret',
        'password',
        '123456',
    ]
    if key.lower() in [w.lower() for w in weak_keys]:
        return False, "使用了已知的弱密钥"

    # 检查字符多样性
    has_upper = any(c.isupper() for c in key)
    has_lower = any(c.islower() for c in key)
    has_digit = any(c.isdigit() for c in key)
    has_special = any(not c.isalnum() for c in key)

    char_types = sum([has_upper, has_lower, has_digit, has_special])
    if char_types < 3:
        return False, f"密钥复杂度不足，需包含至少 3 种字符类型（大小写、数字、特殊字符）"

    return True, "密钥强度合格"


def cmd_check_config(args):
    """检查配置"""
    print("检查配置...")
    print()

    config_mgr = get_config_manager()

    # 检查配置加载
    print("[OK] 配置管理器初始化成功")

    # 检查 Turing 配置
    try:
        turing_config = config_mgr.get('turing')
        if turing_config:
            print("[OK] Turing 模块配置已加载")

            # 检查密钥配置
            auth_config = turing_config.get('auth', {})
            secret_key = auth_config.get('secret_key', '')

            is_strong, message = is_strong_secret_key(secret_key)

            if not is_strong:
                print(f"[FAIL] Turing 认证密钥强度不足：{message}")
                print("   建议:")
                print("   1. 密钥长度至少 32 字符")
                print("   2. 包含大小写字母、数字、特殊字符中的至少 3 种")
                print("   3. 避免使用常见单词或短语")
                print("   4. 使用以下命令生成安全密钥:")
                print("      python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
                print(f"   当前密钥：{secret_key[:4]}...{'*' * (len(secret_key) - 8) if len(secret_key) > 8 else '***'}")
            else:
                print(f"[OK] Turing 认证密钥强度合格（长度：{len(secret_key)}）")
        else:
            print("[FAIL] Turing 模块配置未找到")
    except Exception as e:
        print(f"[FAIL] Turing 配置检查失败：{e}")

    # 检查 Alice 配置
    try:
        alice_config = config_mgr.get('alice')
        if alice_config:
            print("[OK] Alice 模块配置已加载")
        else:
            print("[WARN] Alice 模块配置未找到")
    except Exception as e:
        print(f"[FAIL] Alice 配置检查失败：{e}")

    # 检查数据库配置
    try:
        db_url = config_mgr.get('turing.database.url', '')
        if db_url:
            print(f"[OK] 数据库配置：{db_url}")
        else:
            print("[WARN] 数据库配置未找到")
    except Exception as e:
        print(f"[FAIL] 数据库配置检查失败：{e}")

    print()
    print("配置检查完成")


def cmd_init(args):
    """初始化项目配置"""
    print("初始化项目配置...")

    # 创建必要的目录
    dirs = ['data', 'logs', 'scripts/lua']
    for d in dirs:
        path = Path(d)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"[OK] 创建目录：{d}")

    # 检查 .env 文件
    env_file = Path('.env')
    env_example = Path('.env.example')

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("[OK] 已创建 .env 文件（从 .env.example 复制）")
        print("[WARN] 请编辑 .env 文件配置您的环境变量")
    elif env_file.exists():
        print("[OK] .env 文件已存在")
    else:
        print("[WARN] 未找到 .env.example 文件")

    # 检查配置文件
    config_files = ['config.yaml', 'config.turing.yaml', 'config.alice.yaml']
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"[OK] 配置文件存在：{config_file}")
        else:
            example_file = f"{config_file}.example"
            if Path(example_file).exists():
                print(f"[WARN] 配置文件不存在，可从 {example_file} 复制")
            else:
                print(f"[WARN] 配置文件不存在：{config_file}")

    print()
    print("初始化完成！")
    print()
    print("下一步:")
    print("1. 编辑 .env 文件配置环境变量")
    print("2. 运行 'python main.py check-config' 检查配置")
    print("3. 运行 'python main.py alice' 或 'python main.py turing' 启动服务")


def cmd_init_db(args):
    """初始化数据库并生成邀请码"""
    print("初始化数据库并生成邀请码...")
    print()

    # 导入并运行初始化脚本
    import asyncio
    from turing_test.backend.scripts.init_db import main as init_db_main

    # 构建命令行参数
    sys.argv = [
        'init_db',
        '--count', str(args.count),
        '--max-uses', str(args.max_uses),
    ]

    if args.length:
        sys.argv.extend(['--length', str(args.length)])
    if args.prefix:
        sys.argv.extend(['--prefix', args.prefix])
    if args.suffix:
        sys.argv.extend(['--suffix', args.suffix])
    if args.expire_days:
        sys.argv.extend(['--expire-days', str(args.expire_days)])
    if args.output:
        sys.argv.extend(['--output', args.output])
    if args.no_invite_codes:
        sys.argv.append('--no-invite-codes')
    if args.reset:
        sys.argv.append('--reset')
    if args.skip_check:
        sys.argv.append('--skip-check')

    try:
        asyncio.run(init_db_main())
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] 数据库初始化失败：{e}")
        sys.exit(1)


def _run_chat_tool(args):
    """运行 Bot 命令行对话测试工具"""
    import sys
    sys.argv = [
        'cli_chat.py',
        '--bot', args.bot,
    ]
    if args.config:
        sys.argv.extend(['--config', args.config])
    if args.watch:
        sys.argv.append('--watch')
    if args.no_ltp:
        sys.argv.append('--no-ltp')
    if args.log:
        sys.argv.append('--log')

    from cli_chat import main as cli_chat_main
    cli_chat_main()


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        prog="eliza-py",
        description="Eliza-Py 项目 CLI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py alice              启动 Alice 聊天机器人
  python main.py turing             启动 Turing 测试后端
  python main.py test               运行测试
  python main.py check-config       检查配置
  python main.py init               初始化项目
  python main.py init-db            初始化数据库并生成 100 个邀请码
  python main.py init-db --count 500 --expire-days 30  生成 500 个邀请码，30 天过期
  python main.py chat               Bot 命令行对话测试（默认 Bot）
  python main.py chat --bot fast    使用快速 Bot 进行对话测试
  python main.py chat --watch       开启自动重载（需要 watchdog）
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # Alice 命令
    alice_parser = subparsers.add_parser("alice", help="启动 Alice 聊天机器人")
    alice_parser.add_argument("--host", default=None, help="监听地址")
    alice_parser.add_argument("--port", type=int, default=None, help="端口号")
    alice_parser.add_argument("--reload", action="store_true", help="启用热重载")
    alice_parser.set_defaults(func=cmd_alice)

    # Turing 命令
    turing_parser = subparsers.add_parser("turing", help="启动 Turing 测试后端")
    turing_parser.add_argument("--host", default=None, help="监听地址")
    turing_parser.add_argument("--port", type=int, default=None, help="端口号")
    turing_parser.add_argument("--reload", action="store_true", help="启用热重载")
    turing_parser.set_defaults(func=cmd_turing)

    # Test 命令
    test_parser = subparsers.add_parser("test", help="运行测试")
    test_parser.add_argument("test_dir", nargs="?", default=None, help="测试目录")
    test_parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    test_parser.add_argument("-k", "--keyword", help="运行匹配关键字的测试")
    test_parser.set_defaults(func=cmd_test)

    # Check-config 命令
    check_parser = subparsers.add_parser("check-config", help="检查配置")
    check_parser.set_defaults(func=cmd_check_config)

    # Init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目配置")
    init_parser.set_defaults(func=cmd_init)

    # Init-db 命令
    init_db_parser = subparsers.add_parser("init-db", help="初始化数据库并生成邀请码")
    init_db_parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="生成邀请码数量（默认：100）"
    )
    init_db_parser.add_argument(
        "--length",
        type=int,
        default=None,
        help="邀请码长度（默认：使用配置文件中的值）"
    )
    init_db_parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="邀请码前缀（默认：无）"
    )
    init_db_parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="邀请码后缀（默认：无）"
    )
    init_db_parser.add_argument(
        "--max-uses",
        type=int,
        default=1,
        help="最大使用次数，-1 表示无限（默认：1）"
    )
    init_db_parser.add_argument(
        "--expire-days",
        type=int,
        default=None,
        help="过期天数（默认：永不过期）"
    )
    init_db_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="邀请码导出文件路径（默认：自动生成）"
    )
    init_db_parser.add_argument(
        "--no-invite-codes",
        action="store_true",
        help="不生成邀请码，仅创建表结构"
    )
    init_db_parser.add_argument(
        "--reset",
        action="store_true",
        help="重置数据库（删除所有数据后重新初始化）⚠️  危险操作"
    )
    init_db_parser.add_argument(
        "--skip-check",
        action="store_true",
        help="跳过已有数据检查"
    )
    init_db_parser.set_defaults(func=cmd_init_db)

    # Chat 命令（Bot 命令行对话测试）
    chat_parser = subparsers.add_parser("chat", help="Bot 命令行对话测试工具")
    chat_parser.add_argument(
        "--bot",
        type=str,
        default="default",
        help="Bot ID（从 bots/ 目录加载，默认：default）"
    )
    chat_parser.add_argument(
        "--config",
        type=str,
        help="直接指定 Bot 配置文件路径（优先级高于 --bot）"
    )
    chat_parser.add_argument(
        "--watch",
        action="store_true",
        help="开启自动重载（需要 watchdog）"
    )
    chat_parser.add_argument(
        "--no-ltp",
        action="store_true",
        help="禁用 LTP（使用 jieba 分词，更快但效果较弱）"
    )
    chat_parser.add_argument(
        "--log",
        action="store_true",
        help="启用对话日志"
    )
    chat_parser.set_defaults(func=lambda args: _run_chat_tool(args))

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
