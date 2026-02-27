#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 命令行对话测试工具

支持从 Bot 池中选取特定 Bot 配置进行交互式对话测试，
支持手动热重载和可选的 watchdog 自动重载。

使用方法:
    # 使用默认 Bot
    python cli_chat.py

    # 指定 Bot 配置
    python cli_chat.py --bot default
    python cli_chat.py --bot fast
    python cli_chat.py --bot honeypot

    # 使用自定义 Bot 配置文件
    python cli_chat.py --config bots/my_bot.yaml

    # 开启自动重载（需要 watchdog）
    python cli_chat.py --bot default --watch

    # 禁用 LTP（更快，但效果较弱）
    python cli_chat.py --bot default --no-ltp

内置命令:
    :help     显示帮助信息
    :reload   手动重载脚本（修改 Bot 脚本后使用）
    :stats    查看统计信息
    :reset    重置对话上下文
    :quit     退出程序
"""

import argparse
import sys
import signal
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 第三方库
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

WATCHDOG_AVAILABLE = False
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    # 定义占位类，避免 NameError
    class FileSystemEventHandler:
        pass
    class FileModifiedEvent:
        def __init__(self, src_path):
            self.src_path = src_path
    class Observer:
        def __init__(self):
            pass
        def schedule(self, handler, path, recursive=False):
            pass
        def start(self):
            pass
        def stop(self):
            pass
        def join(self):
            pass

# 项目模块
from alice.alice_v2 import AliceBot
from config import settings


# =============================================================================
# 样式配置
# =============================================================================

if RICH_AVAILABLE:
    console = Console()
    STYLE_BOT = "bold cyan"
    STYLE_USER = "bold green"
    STYLE_COMMAND = "bold yellow"
    STYLE_ERROR = "bold red"
    STYLE_INFO = "dim"
else:
    # 降级到普通输出
    class Console:
        def print(self, *args, **kwargs):
            print(*args)

        def rule(self, *args, **kwargs):
            print("-" * 50)

    console = Console()


# =============================================================================
# Watchdog 自动重载处理器
# =============================================================================

class ScriptChangeHandler(FileSystemEventHandler):
    """
    脚本文件变更处理器

    监控 YAML/Lua 脚本文件变化，触发自动重载。
    """

    def __init__(self, callback):
        """
        初始化处理器

        Args:
            callback: 文件变更回调函数，接收文件路径参数
        """
        super().__init__()
        self.callback = callback
        self._changed_files = set()

    def on_modified(self, event):
        """文件修改事件"""
        if isinstance(event, FileModifiedEvent):
            path = Path(event.src_path)
            if path.suffix.lower() in ['.yaml', '.yml', '.lua']:
                # 避免重复触发（某些编辑器会触发多次）
                if str(path) not in self._changed_files:
                    self._changed_files.add(str(path))
                    self.callback(path)

    def file_reset(self, path: str):
        """重置文件跟踪状态（用于手动重载后）"""
        self._changed_files.discard(path)


# =============================================================================
# Bot 配置加载器
# =============================================================================

def load_bot_config(bot_id: Optional[str] = None, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 Bot 配置

    Args:
        bot_id: Bot ID（从 bots/ 目录加载）
        config_path: 直接指定配置文件路径

    Returns:
        Bot 配置字典

    Raises:
        ValueError: 配置无效时
        FileNotFoundError: 配置文件不存在
    """
    import yaml

    if config_path:
        # 直接指定配置文件
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在：{path}")
    elif bot_id:
        # 从 bots/ 目录加载
        path = Path("bots") / f"{bot_id}.yaml"
        if not path.exists():
            # 尝试不带扩展名
            path = Path("bots") / bot_id
            if not path.exists():
                raise FileNotFoundError(f"Bot 配置不存在：bots/{bot_id}.yaml")
    else:
        # 默认使用 default
        path = Path("bots") / "default.yaml"
        if not path.exists():
            raise FileNotFoundError(f"默认 Bot 配置不存在：{path}")

    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def create_bot_from_config(
    bot_config: Dict[str, Any],
    use_ltp: bool = True,
    enable_logging: bool = False,
) -> AliceBot:
    """
    从 Bot 配置创建 AliceBot 实例

    Args:
        bot_config: Bot 配置字典
        use_ltp: 是否使用 LTP
        enable_logging: 是否启用日志

    Returns:
        AliceBot 实例
    """
    # 从配置提取脚本路径
    script_file = bot_config.get('script_file')
    rules_file = bot_config.get('rules_file')

    # 转换为绝对路径（如果路径存在）
    if script_file:
        script_path = Path(script_file)
        if not script_path.is_absolute():
            script_path = Path.cwd() / script_path
        if script_path.exists():
            script_file = str(script_path)

    if rules_file:
        rules_path = Path(rules_file)
        if not rules_path.is_absolute():
            rules_path = Path.cwd() / rules_path
        if rules_path.exists():
            rules_file = str(rules_path)

    # 创建 Bot 实例
    bot = AliceBot(
        script_file=script_file,
        rules_file=rules_file,
        use_ltp=use_ltp,
        enable_logging=enable_logging,
        cache_size=bot_config.get('cache_size', 50),
    )

    # 加载 Bot 配置中的开场白脚本
    opening_config = bot_config.get('opening')
    if opening_config and isinstance(opening_config, dict):
        opening_script = opening_config.get('script')
        if opening_script:
            opening_path = Path(opening_script)
            if not opening_path.is_absolute():
                opening_path = Path.cwd() / opening_script
            if opening_path.exists():
                try:
                    dialogue_engine = bot.dialogue_engine
                    if dialogue_engine.yaml_engine:
                        dialogue_engine.yaml_engine.load_opening_script(
                            bot_config.get('id', 'default'),
                            opening_path
                        )
                        logger.info(f"Bot 开场白脚本已加载：{opening_path}")
                except Exception as e:
                    logger.warning(f"加载 Bot 开场白脚本失败：{e}")

    return bot


# =============================================================================
# CLI 对话器
# =============================================================================

class ChatCLI:
    """
    命令行对话器

    提供 REPL 风格的交互式对话界面。
    """

    # 内置命令
    COMMANDS = {
        ':help': '显示帮助信息',
        ':reload': '手动重载脚本（修改 Bot 脚本后使用）',
        ':stats': '查看统计信息',
        ':reset': '重置对话上下文',
        ':quit': '退出程序',
    }

    def __init__(
        self,
        bot: AliceBot,
        bot_config: Dict[str, Any],
        watch_mode: bool = False,
    ):
        """
        初始化 CLI

        Args:
            bot: AliceBot 实例
            bot_config: Bot 配置字典
            watch_mode: 是否开启自动重载
        """
        self.bot = bot
        self.bot_config = bot_config
        self.watch_mode = watch_mode
        self.running = False
        self.turn_count = 0

        # Watchdog 相关
        self.observer: Optional[Observer] = None
        self.watch_handler: Optional[ScriptChangeHandler] = None

        # Bot 信息
        self.bot_name = bot_config.get('name', 'Alice')
        self.bot_id = bot_config.get('id', 'default')
        self.script_file = bot_config.get('script_file', 'unknown')

    def start(self):
        """启动 CLI"""
        self.running = True

        # 设置信号处理
        signal.signal(signal.SIGINT, self._handle_signal)

        # 启动 watchdog（如果启用）
        if self.watch_mode:
            self._start_watchdog()

        # 显示欢迎信息
        self._show_welcome()

        # 显示开场白
        self._show_opening()

        # 主循环
        self._main_loop()

    def stop(self):
        """停止 CLI"""
        self.running = False

        # 停止 watchdog
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def _handle_signal(self, signum, frame):
        """信号处理"""
        console.print("\n[yellow]收到中断信号，正在退出...[/]")
        self.stop()

    def _start_watchdog(self):
        """启动 watchdog 自动重载"""
        if not WATCHDOG_AVAILABLE:
            console.print("[yellow]⚠  watchdog 未安装，自动重载功能不可用[/]")
            console.print("[dim]安装：pip install watchdog[/]")
            return

        try:
            # 确定监控目录
            watch_dirs = set()

            # 脚本文件所在目录
            if self.script_file:
                script_dir = Path(self.script_file).parent
                if script_dir.exists():
                    watch_dirs.add(str(script_dir))

            # rules 文件所在目录
            rules_file = self.bot_config.get('rules_file')
            if rules_file:
                rules_dir = Path(rules_file).parent
                if rules_dir.exists():
                    watch_dirs.add(str(rules_dir))

            # bots 目录（如果使用 bots/ 下的配置）
            bots_dir = Path("bots")
            if bots_dir.exists():
                watch_dirs.add(str(bots_dir))

            if not watch_dirs:
                console.print("[yellow]⚠  无法确定监控目录，自动重载功能已禁用[/]")
                return

            # 创建处理器
            self.watch_handler = ScriptChangeHandler(self._on_file_changed)

            # 启动观察者
            self.observer = Observer()
            for dir_path in watch_dirs:
                self.observer.schedule(self.watch_handler, dir_path, recursive=False)
            self.observer.start()

            console.print(f"[green]✓ 自动重载已启用，监控目录：{', '.join(watch_dirs)}[/]")

        except Exception as e:
            console.print(f"[yellow]⚠  启动 watchdog 失败：{e}[/]")

    def _on_file_changed(self, path: Path):
        """文件变更回调"""
        console.print(f"\n[cyan]🔄 检测到文件变更：{path.name}[/]")
        console.print("[dim]输入 :reload 手动重载，或继续对话自动应用更改[/]")

    def _show_welcome(self):
        """显示欢迎信息"""
        if RICH_AVAILABLE:
            # 使用 rich 美化输出
            welcome_text = Text()
            welcome_text.append(f"Bot: ", style=STYLE_INFO)
            welcome_text.append(f"{self.bot_name}", style=STYLE_BOT)
            welcome_text.append(f" (ID: {self.bot_id})\n", style=STYLE_INFO)

            if self.watch_mode and WATCHDOG_AVAILABLE:
                welcome_text.append("自动重载：已启用 🔄\n", style="green")
            else:
                welcome_text.append("自动重载：未启用\n", style="dim")

            welcome_text.append("\n输入 :help 查看可用命令", style=STYLE_INFO)

            console.print(Panel(
                welcome_text,
                title="[bold]Bot 命令行测试工具[/]",
                border_style="blue",
            ))
        else:
            # 降级输出
            print(f"\n{'='*50}")
            print(f"Bot: {self.bot_name} (ID: {self.bot_id})")
            print(f"脚本：{self.script_file}")
            if self.watch_mode and WATCHDOG_AVAILABLE:
                print("自动重载：已启用")
            else:
                print("自动重载：未启用")
            print("\n输入 :help 查看可用命令")
            print(f"{'='*50}\n")

    def _show_opening(self):
        """显示开场白"""
        # 尝试获取开场白（使用 Bot ID）
        try:
            dialogue_engine = self.bot.dialogue_engine
            if dialogue_engine.yaml_engine:
                # 首先尝试使用 Bot ID 获取
                opening = dialogue_engine.yaml_engine.get_opening_message(self.bot_id)
                if not opening:
                    # 如果 Bot ID 没有开场白，尝试使用 "default"
                    opening = dialogue_engine.yaml_engine.get_opening_message("default")
                if opening:
                    self._print_bot_message(opening)
                    return
        except Exception as e:
            logger.debug(f"获取开场白失败：{e}")

        # 默认开场白
        self._print_bot_message(f"你好！我是 {self.bot_name}，有什么想聊的吗？")

    def _main_loop(self):
        """主对话循环"""
        while self.running:
            try:
                # 获取用户输入
                user_input = self._get_user_input()

                if user_input is None:
                    # EOF (Ctrl+D)
                    break

                user_input = user_input.strip()

                if not user_input:
                    continue

                # 处理内置命令
                if user_input.startswith(':'):
                    if not self._handle_command(user_input):
                        break
                    continue

                # 生成响应
                response = self.bot.respond(user_input)
                self.turn_count += 1

                # 显示响应
                self._print_bot_message(response)

            except KeyboardInterrupt:
                break
            except EOFError:
                break

        # 退出
        console.print("\n[dim]再见！很高兴和你聊天！[/]")
        self.bot.cleanup()

    def _get_user_input(self) -> Optional[str]:
        """获取用户输入"""
        try:
            # Windows 管道输入修复：设置 stdin 编码
            if sys.platform == 'win32':
                import io
                if not isinstance(sys.stdin, io.TextIOWrapper):
                    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

            if RICH_AVAILABLE:
                # 使用 rich 的输入提示
                return console.input(f"[{STYLE_USER}]你:[/] ")
            else:
                return input("你：")
        except EOFError:
            return None
        except UnicodeDecodeError:
            # Windows 管道编码问题，尝试降级处理
            try:
                sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='gbk')
                if RICH_AVAILABLE:
                    return console.input(f"[{STYLE_USER}]你:[/] ")
                else:
                    return input("你：")
            except (EOFError, UnicodeDecodeError):
                return None

    def _handle_command(self, command: str) -> bool:
        """
        处理内置命令

        Args:
            command: 命令字符串

        Returns:
            是否继续运行
        """
        cmd = command.lower().split()[0]

        if cmd == ':help':
            self._cmd_help()
        elif cmd == ':reload':
            self._cmd_reload()
        elif cmd == ':stats':
            self._cmd_stats()
        elif cmd == ':reset':
            self._cmd_reset()
        elif cmd in [':quit', ':exit', ':q']:
            return False
        else:
            console.print(f"[{STYLE_ERROR}]未知命令：{cmd}[/]")
            console.print("[dim]输入 :help 查看可用命令[/]")

        return True

    def _cmd_help(self):
        """显示帮助"""
        if RICH_AVAILABLE:
            table = Table(title="可用命令")
            table.add_column("命令", style=STYLE_COMMAND, width=15)
            table.add_column("说明", style="")

            for cmd, desc in self.COMMANDS.items():
                table.add_row(cmd, desc)

            console.print(table)
        else:
            print("\n可用命令:")
            for cmd, desc in self.COMMANDS.items():
                print(f"  {cmd:15} {desc}")
            print()

    def _cmd_reload(self):
        """重载脚本"""
        console.print("[cyan]正在重载脚本...[/]")

        try:
            dialogue_engine = self.bot.dialogue_engine
            success = dialogue_engine.reload_all_scripts()

            if success:
                console.print("[green]✓ 脚本重载成功[/]")

                # 重置 watchdog 的文件跟踪
                if self.watch_handler:
                    self.watch_handler._changed_files.clear()
            else:
                console.print("[yellow]⚠  脚本重载失败，请检查日志[/]")

        except Exception as e:
            console.print(f"[{STYLE_ERROR}]重载失败：{e}[/]")

    def _cmd_stats(self):
        """显示统计信息"""
        stats = self.bot.get_stats()

        if RICH_AVAILABLE:
            table = Table(title="统计信息")
            table.add_column("项目", style=STYLE_INFO)
            table.add_column("值", style="")

            # Bot 状态
            table.add_row("初始化", "✓" if stats.get('initialized') else "✗")
            table.add_row("对话轮数", str(self.turn_count))

            # 缓存统计
            if 'cache' in stats:
                cache_stats = stats['cache']
                table.add_row("缓存命中率", f"{cache_stats.get('hit_rate', '0%')}")

            # 性能统计
            if 'dialogue_engine' in stats:
                engine_stats = stats['dialogue_engine']
                if 'performance' in engine_stats:
                    perf = engine_stats['performance']
                    table.add_row("平均响应时间", f"{perf.get('avg_response_time_ms', 0):.2f}ms")
                    table.add_row("缓存命中率", perf.get('cache_hit_rate', '0%'))

            console.print(table)
        else:
            print("\n统计信息:")
            print(f"  初始化：{'✓' if stats.get('initialized') else '✗'}")
            print(f"  对话轮数：{self.turn_count}")
            print()

    def _cmd_reset(self):
        """重置对话"""
        self.bot.reset()
        self.turn_count = 0
        console.print("[green]✓ 对话已重置[/]")

        # 显示新的开场白
        self._show_opening()

    def _print_bot_message(self, message: str):
        """打印 Bot 消息"""
        if RICH_AVAILABLE:
            console.print(f"[{STYLE_BOT}]{self.bot_name}:[/] {message}")
        else:
            print(f"{self.bot_name}: {message}")


# =============================================================================
# 命令行参数解析
# =============================================================================

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="cli_chat",
        description="Bot 命令行对话测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli_chat.py                    使用默认 Bot (default)
  python cli_chat.py --bot fast         使用 fast Bot
  python cli_chat.py --bot honeypot     使用钓鱼机器人
  python cli_chat.py --config bots/my_bot.yaml  使用自定义配置
  python cli_chat.py --watch            开启自动重载
  python cli_chat.py --no-ltp           禁用 LTP（更快但效果较弱）

内置命令:
  :help     显示帮助信息
  :reload   手动重载脚本
  :stats    查看统计信息
  :reset    重置对话上下文
  :quit     退出程序
        """,
    )

    parser.add_argument(
        "--bot",
        type=str,
        default="default",
        help="Bot ID（从 bots/ 目录加载，默认：default）"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="直接指定 Bot 配置文件路径（优先级高于 --bot）"
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="开启自动重载（需要 watchdog）"
    )

    parser.add_argument(
        "--no-ltp",
        action="store_true",
        help="禁用 LTP（使用 jieba 分词，更快但效果较弱）"
    )

    parser.add_argument(
        "--log",
        action="store_true",
        help="启用对话日志"
    )

    return parser.parse_args()


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主入口"""
    args = parse_args()

    # 加载 Bot 配置
    try:
        if args.config:
            console.print(f"[dim]加载 Bot 配置：{args.config}[/]")
            bot_config = load_bot_config(config_path=args.config)
        else:
            console.print(f"[dim]加载 Bot 配置：bots/{args.bot}.yaml[/]")
            bot_config = load_bot_config(bot_id=args.bot)
    except FileNotFoundError as e:
        console.print(f"[{STYLE_ERROR}]{e}[/]")
        console.print("[dim]可用的 Bot: default, fast, slow, honeypot[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[{STYLE_ERROR}]加载配置失败：{e}[/]")
        sys.exit(1)

    # 创建 Bot 实例
    try:
        console.print("[dim]正在初始化 Bot...[/]")
        bot = create_bot_from_config(
            bot_config=bot_config,
            use_ltp=not args.no_ltp,
            enable_logging=args.log,
        )

        if not bot._initialized:
            raise RuntimeError("Bot 初始化失败")

        console.print(f"[green]✓ Bot 已初始化：{bot_config.get('name', 'Unknown')}[/]")

    except Exception as e:
        console.print(f"[{STYLE_ERROR}]创建 Bot 失败：{e}[/]")
        sys.exit(1)

    # 创建并启动 CLI
    cli = ChatCLI(
        bot=bot,
        bot_config=bot_config,
        watch_mode=args.watch,
    )

    cli.start()


if __name__ == "__main__":
    main()
