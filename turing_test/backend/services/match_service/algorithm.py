"""
匹配算法模块（简化版）

极简算法：仅保留基础打字延迟计算
"""

import random
from typing import Dict, Optional

from config import settings


class MatchAlgorithm:
    """
    简化匹配算法
    
    仅保留：
    - AI 打字延迟计算
    """

    def __init__(self):
        """初始化算法配置"""
        pass

    def calculate_typing_delay(self, message_length: int = 0) -> float:
        """
        计算 AI 打字延迟，模拟人类打字行为
        
        Args:
            message_length: 消息长度（字符数）
            
        Returns:
            延迟时间（秒）
        """
        # 基础延迟 + 按长度额外延迟
        base_delay = random.uniform(0.5, 2.0)
        per_char_delay = message_length * 0.05
        
        return base_delay + per_char_delay


# 全局算法实例
algorithm = MatchAlgorithm()
