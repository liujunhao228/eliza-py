"""
AliceBot池管理器
管理多个轻量级AliceBot实例，支持负载均衡
"""

import threading
import time
from typing import Dict, List, Optional
from alice.bots.lightweight_alice_bot import LightweightAliceBot
from alice.services.shared_nlp_service import SharedNLPService


class AliceBotPool:
    """
    AliceBot池管理器
    管理多个轻量级AliceBot实例，支持负载均衡
    """
    
    def __init__(
        self,
        nlp_service: SharedNLPService,
        min_instances: int = 2,
        max_instances: int = 10,
        idle_timeout: int = 300,
        script_file: Optional[str] = None,
        rules_file: Optional[str] = None,
    ):
        self.nlp_service = nlp_service
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.idle_timeout = idle_timeout
        self.script_file = script_file
        self.rules_file = rules_file
        
        # 实例池
        self._bots: List[LightweightAliceBot] = []
        self._available_bots: List[LightweightAliceBot] = []
        self._busy_bots: Dict[int, dict] = {}  # bot_id -> {'bot': bot, 'assigned_at': timestamp}
        self._pool_lock = threading.RLock()
        
        # 初始化池
        self._initialize_pool()
        
        # 启动维护线程
        self._maintenance_thread = threading.Thread(target=self._maintain_pool, daemon=True)
        self._maintenance_thread.start()
    
    def _initialize_pool(self):
        """初始化Bot池"""
        with self._pool_lock:
            for i in range(self.min_instances):
                bot = self._create_bot()
                if bot:
                    self._bots.append(bot)
                    self._available_bots.append(bot)
    
    def _create_bot(self) -> Optional[LightweightAliceBot]:
        """创建一个新的Bot实例"""
        try:
            bot = LightweightAliceBot(
                nlp_service=self.nlp_service,
                script_file=self.script_file,
                rules_file=self.rules_file,
                enable_logging=False,  # 减少日志开销
                enable_plugins=True,
                cache_size=50,
                use_ltp=False,  # 禁用LTP以避免重复加载
            )
            return bot
        except Exception:
            return None
    
    def acquire_bot(self) -> Optional[LightweightAliceBot]:
        """获取一个可用的Bot实例"""
        with self._pool_lock:
            # 首先尝试从可用池中获取
            if self._available_bots:
                bot = self._available_bots.pop()
                bot_id = id(bot)
                self._busy_bots[bot_id] = {
                    'bot': bot,
                    'assigned_at': time.time()
                }
                return bot
            
            # 如果可用池为空且未达到最大实例数，创建新实例
            if len(self._bots) < self.max_instances:
                new_bot = self._create_bot()
                if new_bot:
                    self._bots.append(new_bot)
                    bot_id = id(new_bot)
                    self._busy_bots[bot_id] = {
                        'bot': new_bot,
                        'assigned_at': time.time()
                    }
                    return new_bot
            
            # 如果达到最大实例数，返回None或阻塞等待
            return None
    
    def release_bot(self, bot: LightweightAliceBot):
        """释放Bot实例"""
        with self._pool_lock:
            bot_id = id(bot)
            if bot_id in self._busy_bots:
                del self._busy_bots[bot_id]
                self._available_bots.append(bot)
    
    def _maintain_pool(self):
        """维护池：清理空闲时间过长的实例"""
        while True:
            time.sleep(60)  # 每分钟检查一次
            self._cleanup_idle_instances()
    
    def _cleanup_idle_instances(self):
        """清理空闲实例，但保持最少实例数"""
        with self._pool_lock:
            current_time = time.time()
            to_remove = []
            
            # 找出空闲时间过长的实例
            for bot_id, info in self._busy_bots.items():
                if current_time - info['assigned_at'] > self.idle_timeout:
                    to_remove.append(bot_id)
            
            # 清理不在使用中的实例
            available_to_remove = []
            for bot in self._available_bots:
                if len(self._available_bots) <= self.min_instances:
                    break  # 保持最少实例数
                if current_time - getattr(bot, '_last_used', current_time) > self.idle_timeout:
                    available_to_remove.append(bot)
            
            # 释放资源
            for bot in available_to_remove:
                bot.cleanup()
                self._bots.remove(bot)
                self._available_bots.remove(bot)
    
    def get_stats(self) -> Dict[str, int]:
        """获取池统计信息"""
        with self._pool_lock:
            return {
                'total_bots': len(self._bots),
                'available_bots': len(self._available_bots),
                'busy_bots': len(self._busy_bots),
                'max_bots': self.max_instances,
            }
    
    def shutdown(self):
        """关闭池，清理所有实例"""
        with self._pool_lock:
            for bot in self._bots:
                bot.cleanup()
            self._bots.clear()
            self._available_bots.clear()
            self._busy_bots.clear()