#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
降级恢复机制示例模块

演示如何实现降级的自动检测和恢复：
- 定期健康检查
- 自动恢复尝试
- 恢复成功时解决降级事件

使用示例:
    from alice.utils.degradation_recovery import RecoveryManager

    recovery_manager = RecoveryManager()

    # 注册可恢复的降级
    recovery_manager.register_recoverable_component(
        name='ltp_engine',
        check_func=check_ltp_available,
        recover_func=recover_ltp_engine,
    )

    # 启动恢复检查
    recovery_manager.start_recovery_checker()
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from alice.utils.degradation_monitor import degradation_monitor

logger = logging.getLogger(__name__)


class RecoverableComponent:
    """可恢复组件"""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], bool],
        recover_func: Optional[Callable[[], bool]] = None,
        check_interval: float = 30.0,
        max_recovery_attempts: int = 3,
    ):
        """
        初始化可恢复组件

        Args:
            name: 组件名称
            check_func: 健康检查函数（返回 True 表示正常）
            recover_func: 恢复函数（返回 True 表示成功）
            check_interval: 检查间隔（秒）
            max_recovery_attempts: 最大恢复尝试次数
        """
        self.name = name
        self.check_func = check_func
        self.recover_func = recover_func
        self.check_interval = check_interval
        self.max_recovery_attempts = max_recovery_attempts

        # 状态
        self.is_degraded = False
        self.recovery_attempts = 0
        self.degradation_id: Optional[str] = None
        self.last_check_time: float = 0
        self.is_healthy: bool = True


class RecoveryManager:
    """
    降级恢复管理器

    功能:
    - 注册可恢复组件
    - 定期健康检查
    - 自动恢复尝试
    - 恢复成功时解决降级事件
    """

    def __init__(self, auto_start: bool = False):
        """
        初始化恢复管理器

        Args:
            auto_start: 是否自动启动检查线程
        """
        self.components: Dict[str, RecoverableComponent] = {}
        self._running = False
        self._check_thread: Optional[threading.Thread] = None

        if auto_start:
            self.start_recovery_checker()

    def register_recoverable_component(
        self,
        name: str,
        check_func: Callable[[], bool],
        recover_func: Optional[Callable[[], bool]] = None,
        check_interval: float = 30.0,
        max_recovery_attempts: int = 3,
    ) -> None:
        """
        注册可恢复组件

        Args:
            name: 组件名称
            check_func: 健康检查函数
            recover_func: 恢复函数
            check_interval: 检查间隔（秒）
            max_recovery_attempts: 最大恢复尝试次数
        """
        self.components[name] = RecoverableComponent(
            name=name,
            check_func=check_func,
            recover_func=recover_func,
            check_interval=check_interval,
            max_recovery_attempts=max_recovery_attempts,
        )
        logger.info(f"已注册可恢复组件：{name}")

    def start_recovery_checker(self) -> None:
        """启动恢复检查线程"""
        if self._running:
            logger.warning("恢复检查已在运行")
            return

        self._running = True
        self._check_thread = threading.Thread(
            target=self._check_and_recover_loop,
            daemon=True,
            name="RecoveryChecker"
        )
        self._check_thread.start()
        logger.info("恢复检查线程已启动")

    def stop_recovery_checker(self) -> None:
        """停止恢复检查线程"""
        self._running = False
        if self._check_thread:
            self._check_thread.join(timeout=5.0)
        logger.info("恢复检查线程已停止")

    def _check_and_recover_loop(self) -> None:
        """检查和恢复循环（在后台线程中运行）"""
        while self._running:
            try:
                self._check_all_components()
            except Exception as e:
                logger.error(f"恢复检查失败：{e}", exc_info=True)

            # 睡眠最短检查间隔
            min_interval = min(
                (c.check_interval for c in self.components.values()),
                default=30.0
            )
            time.sleep(min(min_interval, 5.0))

    def _check_all_components(self) -> None:
        """检查所有组件"""
        current_time = time.time()

        for component in self.components.values():
            # 检查是否到达检查时间
            if current_time - component.last_check_time < component.check_interval:
                continue

            component.last_check_time = current_time

            try:
                is_healthy = component.check_func()
            except Exception as e:
                logger.warning(
                    f"组件 {component.name} 健康检查失败：{e}"
                )
                is_healthy = False

            # 状态变化检测
            if is_healthy and component.is_degraded:
                # 组件已恢复
                self._on_component_recovered(component)
            elif not is_healthy and not component.is_degraded:
                # 组件降级
                self._on_component_degraded(component)

    def _on_component_degraded(self, component: RecoverableComponent) -> None:
        """
        组件降级处理

        Args:
            component: 降级的组件
        """
        component.is_degraded = True
        component.is_healthy = False

        logger.warning(
            f"组件降级：{component.name}",
            extra={
                'component': 'recovery_manager',
                'degraded_component': component.name,
                'action': 'degradation_detected',
            }
        )

        # 注册降级事件
        component.degradation_id = degradation_monitor.register_degradation(
            component=component.name,
            reason='健康检查失败',
            severity=2,
            recovery_plan='自动恢复检查中',
            original_functionality=f'{component.name} 完整功能',
            degraded_functionality=f'{component.name} 功能受限',
            user_notification='系统正在使用简化模式',
        )

    def _on_component_recovered(self, component: RecoverableComponent) -> None:
        """
        组件恢复处理

        Args:
            component: 恢复的组件
        """
        # 尝试恢复（如果有恢复函数）
        if component.recover_func:
            try:
                success = component.recover_func()
                if not success:
                    logger.warning(
                        f"组件 {component.name} 恢复函数执行失败"
                    )
                    component.is_degraded = True
                    component.is_healthy = False
                    return
            except Exception as e:
                logger.error(
                    f"组件 {component.name} 恢复失败：{e}",
                    extra={
                        'component': 'recovery_manager',
                        'degraded_component': component.name,
                        'action': 'recovery_failed',
                    },
                    exc_info=True,
                )
                component.is_degraded = True
                component.is_healthy = False
                return

        # 解决降级事件
        if component.degradation_id:
            success = degradation_monitor.resolve_degradation(component.degradation_id)
            if success:
                logger.info(
                    f"组件已恢复：{component.name}",
                    extra={
                        'component': 'recovery_manager',
                        'recovered_component': component.name,
                        'action': 'recovery_success',
                    }
                )
            component.degradation_id = None

        # 重置状态
        component.is_degraded = False
        component.is_healthy = True
        component.recovery_attempts = 0

    def check_component_now(self, name: str) -> bool:
        """
        立即检查指定组件

        Args:
            name: 组件名称

        Returns:
            组件是否健康
        """
        if name not in self.components:
            logger.warning(f"组件不存在：{name}")
            return False

        component = self.components[name]

        try:
            is_healthy = component.check_func()
        except Exception as e:
            logger.warning(f"组件 {name} 健康检查失败：{e}")
            is_healthy = False

        # 更新状态
        if is_healthy and component.is_degraded:
            self._on_component_recovered(component)
        elif not is_healthy and not component.is_degraded:
            self._on_component_degraded(component)

        return is_healthy

    def get_recovery_status(self) -> Dict[str, Any]:
        """
        获取恢复状态

        Returns:
            状态字典
        """
        return {
            'running': self._running,
            'components': {
                name: {
                    'is_degraded': comp.is_degraded,
                    'is_healthy': comp.is_healthy,
                    'recovery_attempts': comp.recovery_attempts,
                    'degradation_id': comp.degradation_id,
                }
                for name, comp in self.components.items()
            }
        }


# 全局恢复管理器实例
recovery_manager = RecoveryManager(auto_start=False)


# =============================================================================
# 使用示例
# =============================================================================

def example_usage():
    """使用示例"""

    # 示例：LTP 引擎恢复
    def check_ltp_available() -> bool:
        """检查 LTP 是否可用"""
        try:
            from alice.nlp.engines import LtpEngine
            engine = LtpEngine()
            return engine.is_available
        except Exception:
            return False

    def recover_ltp_engine() -> bool:
        """尝试恢复 LTP 引擎"""
        try:
            # 重新加载 LTP 模型
            from alice.nlp.engines import LtpEngine
            # 清除缓存
            LtpEngine.clear_cache()
            # 重新初始化（使用懒加载）
            engine = LtpEngine(lazy_load=True)
            engine.reset()  # 先重置
            return engine.is_available
        except Exception:
            return False

    # 注册组件
    recovery_manager.register_recoverable_component(
        name='ltp_engine',
        check_func=check_ltp_available,
        recover_func=recover_ltp_engine,
        check_interval=60.0,  # 每 60 秒检查一次
    )

    # 启动恢复检查
    recovery_manager.start_recovery_checker()

    # 手动检查
    # is_healthy = recovery_manager.check_component_now('ltp_engine')

    # 获取状态
    # status = recovery_manager.get_recovery_status()


if __name__ == '__main__':
    example_usage()
