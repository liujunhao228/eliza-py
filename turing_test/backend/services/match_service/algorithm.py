"""
匹配算法模块

负责实现匹配算法、优先级匹配和超时判断。
"""

import random
from typing import Dict, List, Optional

from loguru import logger

from config import settings


class MatchAlgorithm:
    """
    匹配算法

    实现：
    1. 寻找匹配对手（优先级 + FIFO 算法）
    2. 防作弊检查（重复匹配检测）
    3. 匹配延迟生成（统一时间分布，消除时间线索）
    4. AI 响应延迟计算
    5. 钓鱼机器人概率判断
    """

    def __init__(self):
        # 匹配时间分布配置（真人/AI 使用相同分布，消除时间线索）
        self.match_time_distribution = settings.turing.match.time_distribution
        # AI 响应时间分布配置（用于打字延迟）
        self.ai_time_distribution = settings.turing.match.time_distribution
        self.honeypot_probability = settings.turing.match.honeypot_probability
        self.honeypot_high_meta_probability = settings.turing.match.honeypot_high_meta_probability
        # 真人优先概率（80% 真人，20% 实验对照）
        self.human_first_probability = 0.8

    def find_match(
        self,
        user_id: int,
        waiting_queue: Dict[int, dict],
        user_match_history: Dict[int, List[dict]]
    ) -> Optional[int]:
        """
        寻找匹配的对手

        使用优先级 + FIFO 算法：
        1. 同优先级内按 FIFO 顺序匹配
        2. 不同优先级时，高优先级用户优先匹配
        3. 排除自己
        4. 排除重复匹配

        Args:
            user_id: 当前用户 ID
            waiting_queue: 等待队列
            user_match_history: 用户匹配历史

        Returns:
            匹配的用户 ID，如果没有匹配则返回 None
        """
        if user_id not in waiting_queue:
            return None

        if len(waiting_queue) < 2:
            return None

        # 获取排序后的用户列表
        sorted_users = self._sort_queue(waiting_queue, exclude_id=user_id)

        # 找到第一个匹配的用户
        for candidate_id, _ in sorted_users:
            if candidate_id in waiting_queue:
                # 检查是否为重复匹配（防作弊）
                if self._is_repeat_match(user_id, candidate_id, user_match_history):
                    logger.info(f"跳过重复匹配：用户 {user_id} 和 {candidate_id}")
                    continue
                return candidate_id

        return None

    def _sort_queue(
        self,
        waiting_queue: Dict[int, dict],
        exclude_id: Optional[int] = None
    ) -> List[tuple]:
        """
        对队列进行排序

        Args:
            waiting_queue: 等待队列
            exclude_id: 要排除的用户 ID

        Returns:
            排序后的用户列表
        """
        from .queue import MatchPriority

        # 优先级顺序：RETURNING > VIP > NORMAL
        priority_order = {
            MatchPriority.RETURNING: 0,
            MatchPriority.VIP: 1,
            MatchPriority.NORMAL: 2,
        }

        sorted_users = sorted(
            [
                (uid, data)
                for uid, data in waiting_queue.items()
                if uid != exclude_id
            ],
            key=lambda x: (
                priority_order[x[1]["priority"]],  # 优先级高的在前
                x[1]["timestamp"],  # 同优先级时，先加入的在前
            )
        )

        return sorted_users

    def _is_repeat_match(
        self,
        user_id: int,
        candidate_id: int,
        user_match_history: Dict[int, List[dict]]
    ) -> bool:
        """
        检查两个用户是否为重复匹配（防作弊）

        Args:
            user_id: 用户 ID
            candidate_id: 候选用户 ID
            user_match_history: 用户匹配历史

        Returns:
            是否为重复匹配
        """
        # 获取用户匹配历史
        user_history = user_match_history.get(user_id, [])

        # 检查最近 5 次匹配
        recent_matches = user_history[-5:]

        for match in recent_matches:
            if match.get("opponent_id") == candidate_id:
                return True

        return False

    def should_assign_honeypot(
        self,
        user_id: int,
        user_score: int,
        user_match_history: Dict[int, List[dict]]
    ) -> bool:
        """
        判断是否应该分配钓鱼机器人

        Args:
            user_id: 用户 ID
            user_score: 用户积分
            user_match_history: 用户匹配历史

        Returns:
            是否分配钓鱼机器人
        """
        # 基础概率
        base_probability = self.honeypot_probability

        # 获取用户元对话历史
        user_history = user_match_history.get(user_id, [])

        # 检查用户最近是否频繁使用元对话（识别 AI 的关键词）
        recent_meta_count = 0
        for match in user_history[-5:]:
            if match.get("meta_count", 0) > 3:
                recent_meta_count += 1

        # 如果用户频繁使用元对话，提高钓鱼机器人概率
        if recent_meta_count >= 3:
            return random.random() < self.honeypot_high_meta_probability

        # 检查用户积分
        if user_score < 50:
            # 低积分用户（回流用户）降低钓鱼机器人概率
            return random.random() < (base_probability * 0.5)
        elif user_score > 200:
            # 高积分用户（VIP）提高钓鱼机器人概率
            return random.random() < (base_probability * 1.5)

        # 普通概率
        return random.random() < base_probability

    def generate_match_delay(self) -> float:
        """
        生成匹配延迟（真人/AI 使用相同分布，消除时间线索）

        时间分布：
        - 50%: 0-3 秒（快速匹配）
        - 30%: 3-8 秒（正常匹配）
        - 15%: 8-15 秒（稍慢）
        - 5%: 15-30 秒（较慢）

        Returns:
            延迟时间（秒）
        """
        rand = random.random()

        cumulative = 0.0
        for period_name, period_config in self.match_time_distribution.items():
            cumulative += period_config["probability"]
            if rand <= cumulative:
                # 在此时间段内随机选择
                delay = random.uniform(
                    period_config["min"],
                    period_config["max"]
                )
                logger.debug(f"生成匹配延迟：{delay:.2f}秒 ({period_name})")
                return delay

        # 默认返回正常时间段
        normal_config = self.match_time_distribution.get("normal", {"min": 3, "max": 8})
        delay = random.uniform(normal_config["min"], normal_config["max"])
        logger.debug(f"生成默认匹配延迟：{delay:.2f}秒 (normal)")
        return delay

    def should_match_human(self) -> bool:
        """
        判断是否应该匹配真人（80% 概率）

        Returns:
            是否匹配真人
        """
        return random.random() < self.human_first_probability

    def calculate_typing_delay(self) -> float:
        """
        计算 AI 打字延迟，模拟人类打字行为

        Returns:
            延迟时间（秒）
        """
        # 根据配置的时间分布随机选择
        rand = random.random()

        cumulative = 0.0
        for period_name, period_config in self.ai_time_distribution.items():
            cumulative += period_config["probability"]
            if rand <= cumulative:
                # 在此时间段内随机选择
                delay = random.uniform(
                    period_config["min"],
                    period_config["max"]
                )
                return delay

        # 默认返回正常时间段
        normal_config = self.ai_time_distribution["normal"]
        return random.uniform(normal_config["min"], normal_config["max"])
