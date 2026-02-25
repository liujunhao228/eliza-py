"""
匹配统计数据模块

负责收集和查询匹配统计数据。
"""

from datetime import datetime
from typing import Dict, List


class MatchStatistics:
    """匹配统计数据"""

    def __init__(self):
        self.total_matches = 0  # 总匹配次数
        self.human_matches = 0  # 真人匹配次数
        self.ai_matches = 0  # AI 匹配次数
        self.honeypot_matches = 0  # 钓鱼机器人匹配次数
        self.timeout_matches = 0  # 超时匹配次数

        # 等待时间统计（秒）
        self.wait_times: List[float] = []

        # 按时间段统计
        self.matches_by_hour: Dict[int, int] = {i: 0 for i in range(24)}

    def record_match(self, wait_time: float, match_type: str):
        """记录一次匹配"""
        self.total_matches += 1
        self.wait_times.append(wait_time)

        if match_type == "human":
            self.human_matches += 1
        elif match_type == "ai":
            self.ai_matches += 1
        elif match_type == "honeypot":
            self.honeypot_matches += 1

        # 按小时统计
        hour = datetime.now().hour
        self.matches_by_hour[hour] += 1

    def get_avg_wait_time(self) -> float:
        """获取平均等待时间"""
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times) / len(self.wait_times)

    def get_success_rate(self) -> float:
        """获取真人匹配成功率"""
        if self.total_matches == 0:
            return 0.0
        return self.human_matches / self.total_matches

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_matches": self.total_matches,
            "human_matches": self.human_matches,
            "ai_matches": self.ai_matches,
            "honeypot_matches": self.honeypot_matches,
            "timeout_matches": self.timeout_matches,
            "human_success_rate": f"{self.get_success_rate():.2%}",
            "avg_wait_time": f"{self.get_avg_wait_time():.1f}秒",
            "current_queue_size": len(self.wait_times) - len([t for t in self.wait_times if t > 0]),
        }
