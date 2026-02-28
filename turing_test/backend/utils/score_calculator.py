"""
积分计算工具

实现图灵测试博弈中的积分计算逻辑，包括：
- 积分预测
- 场中判断积分计算
- 元对话乘数计算
- 积分结算

所有计算逻辑与前端保持一致。
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional


# =============================================================================
# 常量定义（与前端保持一致）
# =============================================================================

ENTRY_FEE = 2  # 入场券
TURN_PENALTY_RATE = 0.5  # 轮数惩罚率
MIN_FREE_TURNS = 3  # 免费轮数

# 基础分
BASE_REWARD_IDENTIFY_AI = 10  # 识别 AI 基础分
BASE_REWARD_IDENTIFY_HUMAN = 10  # 识别人类基础分
BASE_PENALTY_MISIDENTIFY_AI = -15  # 误判 AI 基础分
BASE_PENALTY_MISIDENTIFY_HUMAN = -10  # 误判人类基础分

# 信心等级乘数
CONFIDENCE_MULTIPLIERS = {
    "low": 1.0,
    "mid": 2.5,
    "high": 5.0,
}

# 场中判断乘数（双倍）
MID_GAME_MULTIPLIER = 2.0


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class ScorePrediction:
    """积分预测结果"""
    low_confidence: Dict[str, float]  # {correct: 正确得分，wrong: 错误扣分}
    mid_confidence: Dict[str, float]
    high_confidence: Dict[str, float]
    meta_multiplier: float  # 元对话乘数
    penalty_multiplier: float  # 惩罚乘数
    turn_penalty: float  # 轮数惩罚
    entry_fee: float  # 入场券


@dataclass
class ScoreBreakdown:
    """积分明细"""
    base_score: float  # 基础分
    confidence_multiplier: float  # 信心乘数
    meta_multiplier: float  # 元对话乘数
    turn_penalty: float  # 轮数惩罚
    entry_fee: float  # 入场券
    final_score: float  # 最终得分
    is_correct: bool  # 判断是否正确
    opponent_type: str  # 对手类型
    user_guess: str  # 用户判断
    # 对方猜错奖励字段
    opponent_guess: Optional[str] = None  # 对方对用户的判断 ('human' | 'ai')
    opponent_confidence: Optional[str] = None  # 对方的信心等级
    opponent_is_correct: bool = False  # 对方是否猜对
    opponent_score_if_correct: float = 0.0  # 对方若猜对应得的分
    bonus_from_opponent_wrong: float = 0.0  # 从对方猜错获得的 bonus


# =============================================================================
# 核心计算函数
# =============================================================================

def calculate_turn_penalty(turn: int) -> float:
    """
    计算轮数惩罚

    Args:
        turn: 当前轮数

    Returns:
        轮数惩罚值（非负数）
    """
    return max(0, (turn - MIN_FREE_TURNS) * TURN_PENALTY_RATE)


def calculate_meta_multiplier(meta_count: int) -> float:
    """
    计算元对话乘数（用于奖励）

    Args:
        meta_count: 元对话次数

    Returns:
        乘数（>= 1.0）
    """
    return 1.0 + (meta_count * 0.2)


def calculate_penalty_multiplier(meta_count: int) -> float:
    """
    计算惩罚乘数（用于扣分）

    Args:
        meta_count: 元对话次数

    Returns:
        乘数（>= 1.0）
    """
    return 1.0 + (meta_count * 0.3)


def calculate_score_prediction(
    turn: int,
    meta_count: int,
    is_mid_game: bool = False,
) -> ScorePrediction:
    """
    计算积分预测

    Args:
        turn: 当前轮数
        meta_count: 元对话次数
        is_mid_game: 是否为场中判断

    Returns:
        积分预测结果
    """
    turn_penalty = calculate_turn_penalty(turn)
    meta_multiplier = calculate_meta_multiplier(meta_count)
    penalty_multiplier = calculate_penalty_multiplier(meta_count)

    # 如果是场中判断，应用双倍乘数
    game_multiplier = MID_GAME_MULTIPLIER if is_mid_game else 1.0

    def calc_score(base_reward: float, base_penalty: float, confidence: str) -> Dict[str, float]:
        """计算单个信心等级的得分"""
        mult = CONFIDENCE_MULTIPLIERS[confidence] * game_multiplier
        return {
            "correct": (base_reward * mult * meta_multiplier) - ENTRY_FEE - turn_penalty,
            "wrong": (base_penalty * mult * penalty_multiplier) - ENTRY_FEE - turn_penalty,
        }

    return ScorePrediction(
        low_confidence=calc_score(BASE_REWARD_IDENTIFY_AI, BASE_PENALTY_MISIDENTIFY_AI, "low"),
        mid_confidence=calc_score(BASE_REWARD_IDENTIFY_AI, BASE_PENALTY_MISIDENTIFY_AI, "mid"),
        high_confidence=calc_score(BASE_REWARD_IDENTIFY_AI, BASE_PENALTY_MISIDENTIFY_AI, "high"),
        meta_multiplier=meta_multiplier,
        penalty_multiplier=penalty_multiplier,
        turn_penalty=turn_penalty,
        entry_fee=ENTRY_FEE,
    )


def calculate_final_score(
    user_guess: str,
    opponent_type: str,
    confidence_level: str,
    turn: int,
    meta_count: int,
    is_mid_game: bool = False,
    # 新增参数：对方猜错奖励相关
    opponent_guess: Optional[str] = None,      # 对方对用户的判断 ('human' | 'ai')
    opponent_confidence: Optional[str] = None, # 对方的信心等级
    user_actual_type: str = "ai",              # 用户的真实类型（用于计算对方是否猜对）
) -> Tuple[float, ScoreBreakdown]:
    """
    计算最终积分

    Args:
        user_guess: 用户判断 ('human' | 'ai')
        opponent_type: 对手类型 ('human' | 'ai' | 'honeypot' | 'opponent')
        confidence_level: 信心等级 ('low' | 'mid' | 'high')
        turn: 总轮数
        meta_count: 元对话次数
        is_mid_game: 是否为场中判断
        opponent_guess: 对方对用户的判断 ('human' | 'ai')
        opponent_confidence: 对方的信心等级 ('low' | 'mid' | 'high')
        user_actual_type: 用户的真实类型 ('human' | 'ai')

    Returns:
        (最终得分，积分明细)
    """
    # 处理 opponent_type="opponent" 的情况（需要根据 user_actual_type 推断）
    # 如果 user_actual_type 是 "human"，说明对手是真人；否则对手是 AI
    effective_opponent_type = opponent_type
    if opponent_type == "opponent":
        # 根据用户真实类型推断对手类型（真人对战时双方互为对手）
        effective_opponent_type = "human" if user_actual_type == "human" else "ai"

    # 判断用户是否正确
    is_correct = (user_guess == effective_opponent_type) or (
        user_guess == "human" and effective_opponent_type == "honeypot"
    )

    # 基础分
    if effective_opponent_type in ["ai", "honeypot"]:
        base_reward = BASE_REWARD_IDENTIFY_AI
        base_penalty = BASE_PENALTY_MISIDENTIFY_AI
    else:
        base_reward = BASE_REWARD_IDENTIFY_HUMAN
        base_penalty = BASE_PENALTY_MISIDENTIFY_HUMAN

    # 乘数
    confidence_mult = CONFIDENCE_MULTIPLIERS.get(confidence_level, 1.0)
    if is_mid_game:
        confidence_mult *= MID_GAME_MULTIPLIER

    meta_mult = calculate_meta_multiplier(meta_count)
    penalty_mult = calculate_penalty_multiplier(meta_count)
    turn_penalty = calculate_turn_penalty(turn)

    # 计算用户判断的最终得分
    if is_correct:
        base_score = base_reward
        user_final_score = (base_score * confidence_mult * meta_mult) - ENTRY_FEE - turn_penalty
    else:
        base_score = base_penalty
        user_final_score = (base_score * confidence_mult * penalty_mult) - ENTRY_FEE - turn_penalty

    # === 新增逻辑：计算对方猜错奖励 ===
    bonus_from_opponent = 0.0
    opponent_score_if_correct = 0.0
    opponent_is_correct = False

    if opponent_guess and opponent_confidence:
        # 判断对方是否正确
        opponent_is_correct = (opponent_guess == user_actual_type)
        
        # 计算对方若猜对应得的分（使用对方的信心等级）
        opp_confidence_mult = CONFIDENCE_MULTIPLIERS.get(opponent_confidence, 1.0)
        # 对方的元对话乘数和轮数惩罚与用户相同
        opp_meta_mult = meta_mult
        opp_penalty_mult = penalty_mult
        opp_turn_penalty = turn_penalty
        
        # 对方猜的是用户，所以基础分使用识别 AI/人类的分数
        if user_actual_type == "ai":
            opp_base_reward = BASE_REWARD_IDENTIFY_AI
            opp_base_penalty = BASE_PENALTY_MISIDENTIFY_AI
        else:
            opp_base_reward = BASE_REWARD_IDENTIFY_HUMAN
            opp_base_penalty = BASE_PENALTY_MISIDENTIFY_HUMAN
        
        if opponent_is_correct:
            # 对方猜对了，计算对方应得的分
            opponent_score_if_correct = (opp_base_reward * opp_confidence_mult * opp_meta_mult) - ENTRY_FEE - opp_turn_penalty
        else:
            # 对方猜错了，用户获得等同于对方若猜对应得收益的分
            opponent_score_if_correct = (opp_base_reward * opp_confidence_mult * opp_meta_mult) - ENTRY_FEE - opp_turn_penalty
            bonus_from_opponent = abs(opponent_score_if_correct)

    # 用户最终得分 = 用户自己判断的得分 + 对方猜错 bonus
    total_final_score = user_final_score + bonus_from_opponent

    breakdown = ScoreBreakdown(
        base_score=base_score,
        confidence_multiplier=confidence_mult,
        meta_multiplier=meta_mult,
        turn_penalty=turn_penalty,
        entry_fee=ENTRY_FEE,
        final_score=total_final_score,
        is_correct=is_correct,
        opponent_type=effective_opponent_type,  # 使用有效类型，而非 "opponent"
        user_guess=user_guess,
        opponent_guess=opponent_guess,
        opponent_confidence=opponent_confidence,
        opponent_is_correct=opponent_is_correct,
        opponent_score_if_correct=opponent_score_if_correct,
        bonus_from_opponent_wrong=bonus_from_opponent,
    )

    return total_final_score, breakdown


def get_score_breakdown_dict(breakdown: ScoreBreakdown) -> Dict:
    """
    将积分明细转换为字典（用于 JSON 序列化）

    注意：仅返回必要字段，不暴露计算细节
    """
    result = {
        "final_score": int(breakdown.final_score),
        "is_correct": breakdown.is_correct,
    }
    
    # 添加对方猜错奖励字段
    if breakdown.opponent_guess:
        result["opponent_guess"] = breakdown.opponent_guess
    if breakdown.opponent_confidence:
        result["opponent_confidence"] = breakdown.opponent_confidence
    if breakdown.opponent_is_correct is not None:
        result["opponent_is_correct"] = breakdown.opponent_is_correct
    if breakdown.opponent_score_if_correct:
        result["opponent_score_if_correct"] = breakdown.opponent_score_if_correct
    if breakdown.bonus_from_opponent_wrong:
        result["bonus_from_opponent_wrong"] = breakdown.bonus_from_opponent_wrong
    
    return result


# =============================================================================
# 辅助函数
# =============================================================================

def get_recommended_confidence(
    turn: int,
    meta_count: int,
    is_mid_game: bool = False,
) -> str:
    """
    推荐最优信心等级

    Args:
        turn: 当前轮数
        meta_count: 元对话次数
        is_mid_game: 是否为场中判断

    Returns:
        推荐的信心等级 ('low' | 'mid' | 'high')
    """
    prediction = calculate_score_prediction(turn, meta_count, is_mid_game)

    # 比较正确时的收益
    rewards = {
        "low": prediction.low_confidence["correct"],
        "mid": prediction.mid_confidence["correct"],
        "high": prediction.high_confidence["correct"],
    }

    # 返回收益最高的
    return max(rewards, key=rewards.get)


def is_high_frequency_meta(meta_count: int, threshold: int = 5) -> bool:
    """
    判断是否为高频元对话

    Args:
        meta_count: 元对话次数
        threshold: 阈值

    Returns:
        是否为高频
    """
    return meta_count > threshold


def format_score_change(score: float) -> str:
    """
    格式化积分变化显示

    Args:
        score: 积分变化值

    Returns:
        格式化字符串（如 "+15.5" 或 "-8.0"）
    """
    if score >= 0:
        return f"+{score:.1f}"
    else:
        return f"{score:.1f}"


# =============================================================================
# 测试
# =============================================================================

if __name__ == "__main__":
    # 测试积分计算
    print("=" * 60)
    print("积分计算测试")
    print("=" * 60)

    # 测试 1：普通情况
    print("\n测试 1: 普通情况（turn=5, meta=2）")
    pred = calculate_score_prediction(turn=5, meta_count=2)
    print(f"  低信心：正确={pred.low_confidence['correct']:.1f}, 错误={pred.low_confidence['wrong']:.1f}")
    print(f"  中信心：正确={pred.mid_confidence['correct']:.1f}, 错误={pred.mid_confidence['wrong']:.1f}")
    print(f"  高信心：正确={pred.high_confidence['correct']:.1f}, 错误={pred.high_confidence['wrong']:.1f}")
    print(f"  元对话乘数：{pred.meta_multiplier:.2f}x")
    print(f"  轮数惩罚：{pred.turn_penalty:.1f}")

    # 测试 2：场中判断
    print("\n测试 2: 场中判断（turn=4, meta=1）")
    pred_mid = calculate_score_prediction(turn=4, meta_count=1, is_mid_game=True)
    print(f"  低信心：正确={pred_mid.low_confidence['correct']:.1f}, 错误={pred_mid.low_confidence['wrong']:.1f}")
    print(f"  中信心：正确={pred_mid.mid_confidence['correct']:.1f}, 错误={pred_mid.mid_confidence['wrong']:.1f}")
    print(f"  高信心：正确={pred_mid.high_confidence['correct']:.1f}, 错误={pred_mid.high_confidence['wrong']:.1f}")

    # 测试 3：最终积分计算
    print("\n测试 3: 最终积分计算")
    final_score, breakdown = calculate_final_score(
        user_guess="ai",
        opponent_type="ai",
        confidence_level="high",
        turn=6,
        meta_count=3,
    )
    print(f"  最终得分：{final_score:.1f}")
    print(f"  判断正确：{breakdown.is_correct}")
    print(f"  积分明细：{get_score_breakdown_dict(breakdown)}")

    # 测试 4：推荐信心
    print("\n测试 4: 推荐信心")
    recommended = get_recommended_confidence(turn=5, meta_count=2)
    print(f"  推荐信心等级：{recommended}")
