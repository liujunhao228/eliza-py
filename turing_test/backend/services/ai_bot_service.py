"""
AI Bot 服务

集成 AliceBot 池，提供 AI 响应生成服务。
支持打字延迟模拟和负载均衡。
"""

import asyncio
import random
from typing import Tuple, Optional, Any
from loguru import logger

from config import settings


class AIBotService:
    """
    AI Bot 服务

    提供 AI 响应生成服务，集成 Bot 池管理和打字延迟模拟。

    使用示例:
        service = AIBotService()
        response, delay = await service.get_response("你好")
    """

    def __init__(self):
        """初始化 AI Bot 服务"""
        self._initialized = False
        self._nlp_service = None
        self._bot_pool = None
        
        # 延迟配置
        self._delay_config = None

    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return

        try:
            # 导入共享 NLP 服务
            from alice.services.shared_nlp_service import SharedNLPService
            self._nlp_service = SharedNLPService()

            # 加载延迟配置
            self._load_delay_config()

            # 初始化 Bot 池
            from turing_test.backend.services.bot_pool import init_bot_pool

            # 使用 getattr 提供默认值以兼容不同配置
            # 注意：script_file 和 rules_file 在 settings.alice.scripting 下
            script_file = None
            rules_file = None

            if hasattr(settings, 'alice') and settings.alice:
                alice_cfg = settings.alice
                # 从 scripting.yaml.script_file 获取
                if hasattr(alice_cfg, 'scripting') and alice_cfg.scripting:
                    scripting_cfg = alice_cfg.scripting
                    if hasattr(scripting_cfg, 'yaml') and scripting_cfg.yaml:
                        script_file = str(scripting_cfg.yaml.script_file) if scripting_cfg.yaml.script_file else None
                    rules_file = str(scripting_cfg.rules_file) if hasattr(scripting_cfg, 'rules_file') and scripting_cfg.rules_file else None

            self._bot_pool = init_bot_pool(
                nlp_service=self._nlp_service,
                min_instances=getattr(settings, 'BOT_POOL_MIN_INSTANCES', 2),
                max_instances=getattr(settings, 'BOT_POOL_MAX_INSTANCES', 10),
                idle_timeout=getattr(settings, 'BOT_POOL_IDLE_TIMEOUT', 300),
                script_file=script_file,
                rules_file=rules_file,
            )

            self._initialized = True
            logger.info(f"✅ AI Bot 服务初始化成功 (script_file={script_file}, rules_file={rules_file})")

        except Exception as e:
            logger.error(f"AI Bot 服务初始化失败：{e}", exc_info=True)
            raise

    def _load_delay_config(self):
        """加载延迟配置"""
        # 从 ConfigManager 获取原始配置字典
        from config.manager import get_config_manager
        
        try:
            config_mgr = get_config_manager()
            # 获取原始 turing 配置字典
            turing_cfg = config_mgr._config.get('turing', {})
            ai_bot_cfg = turing_cfg.get('ai_bot', {})
        except Exception:
            # 如果无法获取原始配置，使用默认值
            ai_bot_cfg = {}
        
        self._delay_config = {
            # 回复延迟
            'reply_delay_min': ai_bot_cfg.get('reply_delay_min', 1.0),
            'reply_delay_max': ai_bot_cfg.get('reply_delay_max', 3.0),
            # 开场白延迟
            'opening_delay_min': ai_bot_cfg.get('opening_delay_min', 2.0),
            'opening_delay_max': ai_bot_cfg.get('opening_delay_max', 5.0),
            # 每字符延迟
            'typing_delay_per_char': ai_bot_cfg.get('typing_delay_per_char', 0.05),
            # 钓鱼机器人延迟
            'honeypot': {
                'reply_delay_min': ai_bot_cfg.get('honeypot', {}).get('reply_delay_min', 2.0),
                'reply_delay_max': ai_bot_cfg.get('honeypot', {}).get('reply_delay_max', 8.0),
                'opening_delay_min': ai_bot_cfg.get('honeypot', {}).get('opening_delay_min', 5.0),
                'opening_delay_max': ai_bot_cfg.get('honeypot', {}).get('opening_delay_max', 15.0),
                'occasional_long_delay_probability': ai_bot_cfg.get('honeypot', {}).get('occasional_long_delay_probability', 0.1),
                'occasional_long_delay_min': ai_bot_cfg.get('honeypot', {}).get('occasional_long_delay_min', 15.0),
                'occasional_long_delay_max': ai_bot_cfg.get('honeypot', {}).get('occasional_long_delay_max', 60.0),
                'meta_delay_multiplier': ai_bot_cfg.get('honeypot', {}).get('meta_delay_multiplier', 1.5),
                'early_session_delay_multiplier': ai_bot_cfg.get('honeypot', {}).get('early_session_delay_multiplier', 1.3),
            }
        }
        logger.debug(f"延迟配置已加载：{self._delay_config}")

    async def shutdown(self):
        """关闭服务"""
        if not self._initialized:
            return

        try:
            # 先关闭 Bot 池
            from turing_test.backend.services.bot_pool import shutdown_bot_pool
            shutdown_bot_pool()
            
            # 再关闭 NLP 服务
            if self._nlp_service:
                try:
                    self._nlp_service.shutdown()
                except Exception as e:
                    logger.error(f"关闭 NLP 服务失败：{e}")
            
            self._initialized = False
            logger.info("✅ AI Bot 服务已关闭")
        except Exception as e:
            logger.error(f"AI Bot 服务关闭失败：{e}")

    async def get_response(
        self,
        user_input: str,
        simulate_typing: bool = True,
        is_opening: bool = False,
        is_honeypot: bool = False,
        session_turn_count: int = 0,
        is_meta: bool = False,
    ) -> Tuple[str, float, Optional[Any]]:
        """
        获取 AI 响应

        Args:
            user_input: 用户输入
            simulate_typing: 是否模拟打字延迟
            is_opening: 是否为开场白
            is_honeypot: 是否为钓鱼机器人
            session_turn_count: 会话轮数
            is_meta: 是否为元对话

        Returns:
            (响应内容，打字延迟秒数，结束动作)
            结束动作为 dict 格式：{"action": "...", "reason": "..."}
        """
        if not self._initialized:
            logger.warning("AI Bot 服务未初始化")
            return "系统未初始化，请稍后再试。", 1.0, None

        # 从 Bot 池获取 Bot
        bot = self._bot_pool.acquire(timeout=5.0)
        if not bot:
            logger.warning("无法获取 Bot 实例")
            return "抱歉，我现在比较忙，请稍后再试。", 1.0, None

        try:
            # 生成响应（获取完整响应对象）
            response_text, end_action = bot.respond_with_end_action(user_input)

            # 计算打字延迟
            delay = self._calculate_typing_delay(
                response_text,
                is_opening=is_opening,
                is_honeypot=is_honeypot,
                session_turn_count=session_turn_count,
                is_meta=is_meta,
            ) if simulate_typing else 0.0

            # 模拟打字延迟
            if simulate_typing and delay > 0:
                await asyncio.sleep(delay)

            logger.debug(f"AI 响应生成：输入长度={len(user_input)}, 响应长度={len(response_text)}, 延迟={delay:.2f}秒，end_action={end_action}")

            return response_text, delay, end_action

        except Exception as e:
            logger.error(f"生成 AI 响应失败：{e}", exc_info=True)
            return "系统出现故障，请稍后再试。", 1.0, None

        finally:
            # 释放 Bot 回池中
            self._bot_pool.release(bot)

    def _calculate_typing_delay(
        self,
        response: str,
        is_opening: bool = False,
        is_honeypot: bool = False,
        session_turn_count: int = 0,
        is_meta: bool = False,
    ) -> float:
        """
        计算打字延迟，模拟人类打字行为

        考虑因素:
        - 基础延迟（随机均匀分布）
        - 响应长度
        - 钓鱼机器人拟真行为
        - 元对话延迟加成
        - 会话早期延迟加成

        Args:
            response: AI 响应内容
            is_opening: 是否为开场白
            is_honeypot: 是否为钓鱼机器人
            session_turn_count: 会话轮数
            is_meta: 是否为元对话

        Returns:
            打字延迟（秒）
        """
        if not self._delay_config:
            self._load_delay_config()

        # 根据类型选择延迟范围
        if is_honeypot:
            honeypot_cfg = self._delay_config['honeypot']
            if is_opening:
                delay_min = honeypot_cfg['opening_delay_min']
                delay_max = honeypot_cfg['opening_delay_max']
            else:
                delay_min = honeypot_cfg['reply_delay_min']
                delay_max = honeypot_cfg['reply_delay_max']
        else:
            if is_opening:
                delay_min = self._delay_config['opening_delay_min']
                delay_max = self._delay_config['opening_delay_max']
            else:
                delay_min = self._delay_config['reply_delay_min']
                delay_max = self._delay_config['reply_delay_max']

        # 基础延迟（随机均匀分布）
        base_delay = random.uniform(delay_min, delay_max)

        # 根据响应长度增加延迟
        length_delay = len(response) * self._delay_config['typing_delay_per_char']

        # 钓鱼机器人拟真行为
        if is_honeypot:
            honeypot_cfg = self._delay_config['honeypot']

            # 偶尔超长延迟（模拟人类分心）
            if random.random() < honeypot_cfg['occasional_long_delay_probability']:
                long_delay = random.uniform(
                    honeypot_cfg['occasional_long_delay_min'],
                    honeypot_cfg['occasional_long_delay_max']
                )
                base_delay += long_delay

            # 元对话时延迟乘数（模拟思考）
            if is_meta:
                base_delay *= honeypot_cfg['meta_delay_multiplier']

            # 会话早期延迟乘数（建立人设）
            if session_turn_count < 5:
                base_delay *= honeypot_cfg['early_session_delay_multiplier']

        # 总延迟
        total_delay = base_delay + length_delay

        # 添加随机波动（±20%）
        jitter = random.uniform(-0.2, 0.2) * total_delay
        total_delay += jitter

        # 确保最小延迟
        return max(0.5, total_delay)

    def get_pool_stats(self) -> dict:
        """
        获取 Bot 池统计信息

        Returns:
            统计信息字典
        """
        if not self._initialized or not self._bot_pool:
            return {"error": "服务未初始化"}

        return self._bot_pool.get_stats()


# =============================================================================
# 全局服务实例
# =============================================================================

_ai_bot_service: Optional[AIBotService] = None
_ai_bot_service_lock = asyncio.Lock()


async def get_ai_bot_service() -> AIBotService:
    """
    获取全局 AI Bot 服务实例（懒加载）

    Returns:
        AIBotService 实例
    """
    global _ai_bot_service

    if _ai_bot_service is None:
        async with _ai_bot_service_lock:
            if _ai_bot_service is None:
                _ai_bot_service = AIBotService()
                await _ai_bot_service.initialize()

    return _ai_bot_service


async def shutdown_ai_bot_service():
    """关闭全局 AI Bot 服务"""
    global _ai_bot_service

    if _ai_bot_service:
        await _ai_bot_service.shutdown()
        _ai_bot_service = None


# =============================================================================
# 便捷函数
# =============================================================================

async def get_bot_response(
    user_input: str,
    is_opening: bool = False,
    is_honeypot: bool = False,
    session_turn_count: int = 0,
) -> Tuple[str, float, Optional[Any]]:
    """
    获取 AI 响应（便捷函数）

    Args:
        user_input: 用户输入
        is_opening: 是否为开场白
        is_honeypot: 是否为钓鱼机器人
        session_turn_count: 会话轮数

    Returns:
        (响应内容，打字延迟秒数，结束动作)
        结束动作为 dict 格式：{"action": "...", "reason": "..."}
    """
    service = await get_ai_bot_service()
    return await service.get_response(
        user_input,
        is_opening=is_opening,
        is_honeypot=is_honeypot,
        session_turn_count=session_turn_count,
    )


async def reset_bot_pool():
    """重置 Bot 池（主要用于测试）"""
    await shutdown_ai_bot_service()
    await get_ai_bot_service()
