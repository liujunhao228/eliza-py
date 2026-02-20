#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本/规则文件热重载模块

功能:
- 监控 YAML 文件变化
- 自动重新加载脚本和规则
- 支持手动触发重载
- 提供重载回调通知

使用示例:
    # 方式 1: 自动监控
    reloader = HotReloader(script_file="scripts/demo.yaml", rules_file="scripts/mapping.yaml")
    reloader.start()  # 启动后台监控线程
    
    # 方式 2: 手动重载
    reloader.reload_scripts()
    reloader.reload_rules()
    
    # 方式 3: 注册回调
    def on_reload(script_engine, rules_engine):
        print("配置已重载!")
    reloader.add_reload_callback(on_reload)
    
    # 停止监控
    reloader.stop()
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileMovedEvent, FileCreatedEvent

logger = logging.getLogger(__name__)


@dataclass
class ReloadResult:
    """重载结果"""
    success: bool
    script_reloaded: bool = False
    rules_reloaded: bool = False
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class YAMLFileChangeHandler(FileSystemEventHandler):
    """YAML 文件变化处理器"""

    def __init__(
        self,
        script_file: Optional[str],
        rules_file: Optional[str],
        on_script_change: Optional[Callable[[], None]] = None,
        on_rules_change: Optional[Callable[[], None]] = None,
    ):
        """
        初始化文件变化处理器

        Args:
            script_file: 脚本文件路径
            rules_file: 规则文件路径
            on_script_change: 脚本文件变化回调
            on_rules_change: 规则文件变化回调
        """
        super().__init__()
        self.script_path = Path(script_file) if script_file else None
        self.rules_path = Path(rules_file) if rules_file else None
        self.on_script_change = on_script_change
        self.on_rules_change = on_rules_change
        self._last_modified: Dict[Path, float] = {}
        self._debounce_seconds = 1.0  # 防抖时间（秒）

    def _should_process(self, path: Path) -> bool:
        """检查文件是否应该被处理（防抖）"""
        current_time = time.time()
        last_modified = self._last_modified.get(path, 0)

        if current_time - last_modified < self._debounce_seconds:
            return False

        self._last_modified[path] = current_time
        return True

    def _get_watch_paths(self) -> Set[Path]:
        """获取需要监控的路径"""
        paths = set()
        if self.script_path and self.script_path.exists():
            paths.add(self.script_path.parent)
        if self.rules_path and self.rules_path.exists():
            paths.add(self.rules_path.parent)
        return paths

    def _is_watched_file(self, path: Path) -> Optional[str]:
        """
        检查文件是否在监控范围内

        Returns:
            'script' 如果是脚本文件，'rules' 如果是规则文件，None 否则
        """
        if self.script_path and path == self.script_path:
            return 'script'
        if self.rules_path and path == self.rules_path:
            return 'rules'
        return None

    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return

        path = Path(event.src_path)
        file_type = self._is_watched_file(path)

        if file_type and self._should_process(path):
            logger.info(f"检测到 {file_type} 文件变化：{path}")
            if file_type == 'script' and self.on_script_change:
                self.on_script_change()
            elif file_type == 'rules' and self.on_rules_change:
                self.on_rules_change()

    def on_moved(self, event):
        """文件移动事件（保存时可能是移动操作）"""
        if event.is_directory:
            return

        # 检查目标路径
        dest_path = Path(event.dest_path)
        file_type = self._is_watched_file(dest_path)

        if file_type and self._should_process(dest_path):
            logger.info(f"检测到 {file_type} 文件更新（移动）：{dest_path}")
            if file_type == 'script' and self.on_script_change:
                self.on_script_change()
            elif file_type == 'rules' and self.on_rules_change:
                self.on_rules_change()


class HotReloader:
    """
    YAML 脚本/规则热重载器

    功能:
    - 后台线程监控文件变化
    - 自动重新加载脚本和规则
    - 支持多个重载回调
    - 优雅停止机制
    """

    def __init__(
        self,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        script_engine: Optional[Any] = None,
        reassembly_engine: Optional[Any] = None,
        auto_reload: bool = True,
        poll_interval: float = 2.0,
    ):
        """
        初始化热重载器

        Args:
            script_file: 脚本文件路径
            rules_file: 规则文件路径
            script_engine: YAML 脚本引擎实例（用于重载）
            reassembly_engine: 句法重组引擎实例（用于重载规则）
            auto_reload: 是否自动重载
            poll_interval: 文件轮询间隔（秒）
        """
        self.script_file = script_file
        self.rules_file = rules_file
        self.script_engine = script_engine
        self.reassembly_engine = reassembly_engine
        self.auto_reload = auto_reload
        self.poll_interval = poll_interval

        self._reload_callbacks: List[Callable[[ReloadResult], None]] = []
        self._observer: Optional[Observer] = None
        self._event_handler: Optional[YAMLFileChangeHandler] = None
        self._running = False
        self._lock = threading.Lock()

        # 设置文件变化回调
        self._setup_handlers()

    def _setup_handlers(self):
        """设置文件变化处理器"""
        self._event_handler = YAMLFileChangeHandler(
            script_file=self.script_file,
            rules_file=self.rules_file,
            on_script_change=self._on_script_change,
            on_rules_change=self._on_rules_change,
        )

    def _on_script_change(self):
        """脚本文件变化回调"""
        if self.auto_reload:
            logger.info("自动重载脚本文件...")
            self.reload_scripts()

    def _on_rules_change(self):
        """规则文件变化回调"""
        if self.auto_reload:
            logger.info("自动重载规则文件...")
            self.reload_rules()

    def add_reload_callback(self, callback: Callable[[ReloadResult], None]) -> None:
        """
        添加重载回调函数

        Args:
            callback: 回调函数，接收 ReloadResult 参数
        """
        self._reload_callbacks.append(callback)
        logger.debug(f"添加重载回调：{callback.__name__}")

    def remove_reload_callback(self, callback: Callable[[ReloadResult], None]) -> None:
        """移除重载回调"""
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    def _notify_callbacks(self, result: ReloadResult) -> None:
        """通知所有回调"""
        for callback in self._reload_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"重载回调执行失败 [{callback.__name__}]: {e}", exc_info=True)

    def set_script_engine(self, script_engine: Any) -> None:
        """设置脚本引擎"""
        self.script_engine = script_engine
        logger.debug("热重载器已绑定脚本引擎")

    def set_reassembly_engine(self, reassembly_engine: Any) -> None:
        """设置重组引擎"""
        self.reassembly_engine = reassembly_engine
        logger.debug("热重载器已绑定重组引擎")

    def start(self) -> None:
        """启动文件监控"""
        with self._lock:
            if self._running:
                logger.warning("热重载器已在运行中")
                return

            # 收集需要监控的目录
            watch_paths = set()
            if self.script_file:
                script_path = Path(self.script_file)
                if script_path.exists():
                    watch_paths.add(str(script_path.parent))
                else:
                    logger.warning(f"脚本文件不存在，无法监控：{script_path}")

            if self.rules_file:
                rules_path = Path(self.rules_file)
                if rules_path.exists():
                    watch_paths.add(str(rules_path.parent))
                else:
                    logger.warning(f"规则文件不存在，无法监控：{rules_path}")

            if not watch_paths:
                logger.warning("没有可监控的文件路径，热重载器无法启动")
                return

            # 创建观察者
            self._observer = Observer()
            self._setup_handlers()  # 重新创建处理器确保回调正确

            for path in watch_paths:
                self._observer.schedule(self._event_handler, path, recursive=False)
                logger.info(f"开始监控目录：{path}")

            self._observer.start()
            self._running = True
            logger.info(f"热重载器已启动，监控 {len(watch_paths)} 个目录")

    def stop(self) -> None:
        """停止文件监控"""
        with self._lock:
            if not self._running:
                return

            if self._observer:
                self._observer.stop()
                self._observer.join(timeout=5)
                self._observer = None

            self._running = False
            logger.info("热重载器已停止")

    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running

    def reload_scripts(self) -> ReloadResult:
        """
        手动重载脚本文件

        Returns:
            重载结果
        """
        if not self.script_engine:
            return ReloadResult(
                success=False,
                error="脚本引擎未设置"
            )

        if not self.script_file:
            return ReloadResult(
                success=False,
                error="脚本文件路径未设置"
            )

        script_path = Path(self.script_file)
        if not script_path.exists():
            return ReloadResult(
                success=False,
                error=f"脚本文件不存在：{script_path}"
            )

        try:
            logger.info(f"重载脚本文件：{script_path}")
            old_intents_count = len(self.script_engine.intents)

            # 重新加载脚本
            self.script_engine._load_scripts()

            new_intents_count = len(self.script_engine.intents)
            logger.info(
                f"脚本重载成功：{old_intents_count} -> {new_intents_count} 个意图"
            )

            result = ReloadResult(
                success=True,
                script_reloaded=True,
            )

        except Exception as e:
            logger.error(f"脚本重载失败：{e}", exc_info=True)
            result = ReloadResult(
                success=False,
                error=f"脚本重载失败：{type(e).__name__}: {e}"
            )

        self._notify_callbacks(result)
        return result

    def reload_rules(self) -> ReloadResult:
        """
        手动重载规则文件

        Returns:
            重载结果
        """
        if not self.reassembly_engine:
            return ReloadResult(
                success=False,
                error="重组引擎未设置"
            )

        if not self.rules_file:
            return ReloadResult(
                success=False,
                error="规则文件路径未设置"
            )

        rules_path = Path(self.rules_file)
        if not rules_path.exists():
            return ReloadResult(
                success=False,
                error=f"规则文件不存在：{rules_path}"
            )

        try:
            logger.info(f"重载规则文件：{rules_path}")

            # 重新加载规则
            self.reassembly_engine.load_rules(self.rules_file)

            logger.info("规则重载成功")
            result = ReloadResult(
                success=True,
                rules_reloaded=True,
            )

        except Exception as e:
            logger.error(f"规则重载失败：{e}", exc_info=True)
            result = ReloadResult(
                success=False,
                error=f"规则重载失败：{type(e).__name__}: {e}"
            )

        self._notify_callbacks(result)
        return result

    def reload_all(self) -> ReloadResult:
        """
        同时重载脚本和规则

        Returns:
            重载结果
        """
        script_result = self.reload_scripts()
        rules_result = self.reload_rules()

        return ReloadResult(
            success=script_result.success and rules_result.success,
            script_reloaded=script_result.script_reloaded,
            rules_reloaded=rules_result.rules_reloaded,
            error=script_result.error or rules_result.error,
        )

    def get_status(self) -> Dict[str, Any]:
        """获取热重载器状态"""
        return {
            "running": self._running,
            "auto_reload": self.auto_reload,
            "script_file": self.script_file,
            "rules_file": self.rules_file,
            "script_engine_attached": self.script_engine is not None,
            "reassembly_engine_attached": self.reassembly_engine is not None,
            "callbacks_count": len(self._reload_callbacks),
            "poll_interval": self.poll_interval,
        }


class ManualHotReloader(HotReloader):
    """
    手动触发的热重载器（不使用后台监控线程）

    适用于不想使用文件监控的场景，通过 API 手动触发重载
    """

    def __init__(
        self,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
        script_engine: Optional[Any] = None,
        reassembly_engine: Optional[Any] = None,
    ):
        """
        初始化手动热重载器

        Args:
            script_file: 脚本文件路径
            rules_file: 规则文件路径
            script_engine: YAML 脚本引擎实例
            reassembly_engine: 句法重组引擎实例
        """
        super().__init__(
            script_file=script_file,
            rules_file=rules_file,
            script_engine=script_engine,
            reassembly_engine=reassembly_engine,
            auto_reload=False,  # 不自动重载
            poll_interval=0,
        )

    def start(self) -> None:
        """手动重载器不需要启动监控"""
        logger.info("手动热重载器已初始化，调用 reload_* 方法触发重载")

    def stop(self) -> None:
        """手动重载器不需要停止"""
        pass

    def is_running(self) -> bool:
        """手动重载器始终不在运行状态"""
        return False


def create_hot_reloader(
    script_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    script_engine: Optional[Any] = None,
    reassembly_engine: Optional[Any] = None,
    auto_reload: bool = True,
    mode: str = "auto",
) -> HotReloader:
    """
    创建热重载器的工厂函数

    Args:
        script_file: 脚本文件路径
        rules_file: 规则文件路径
        script_engine: YAML 脚本引擎实例
        reassembly_engine: 句法重组引擎实例
        auto_reload: 是否自动重载
        mode: 模式 ("auto" 或 "manual")

    Returns:
        热重载器实例
    """
    if mode == "manual":
        reloader = ManualHotReloader(
            script_file=script_file,
            rules_file=rules_file,
            script_engine=script_engine,
            reassembly_engine=reassembly_engine,
        )
    else:
        reloader = HotReloader(
            script_file=script_file,
            rules_file=rules_file,
            script_engine=script_engine,
            reassembly_engine=reassembly_engine,
            auto_reload=auto_reload,
        )

    return reloader
