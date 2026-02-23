"""
游戏相关 API

包括：
- 场中判断
- 问卷提交
- 积分历史
- 积分预测
- 元对话乘数查询
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from turing_test.backend.database import get_db
from turing_test.backend.models import User, Session, Message, ScoreHistory, UserStats
from turing_test.backend.schemas import (
    MidGameJudgmentRequest,
    SurveyRequest,
    GameResultResponse,
    ScoreHistoryResponse,
    SuccessResponse,
    ErrorResponse,
)
from turing_test.backend.utils.score_calculator import (
    calculate_final_score,
    get_score_breakdown_dict,
    calculate_score_prediction,
    get_recommended_confidence,
    ScoreBreakdown,
)

router = APIRouter()


# =============================================================================
# 场中判断
# =============================================================================

@router.post(
    "/session/{session_id}/end-game",
    response_model=GameResultResponse,
    tags=["游戏"],
    summary="场中判断",
    description="提交场中判断，立即结束会话并结算积分",
)
async def submit_mid_game_judgment(
    session_id: int,
    request: MidGameJudgmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    场中判断 API

    用户在游戏中途做出判断，立即结束会话并结算积分。
    场中判断享受双倍乘数奖励/惩罚。
    """
    # 获取会话
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    # 检查会话是否已结束
    if session.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="会话已结束，无法重复提交",
        )

    # 获取用户
    result = await db.execute(
        select(User).where(User.id == session.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 获取元对话计数
    meta_count = session.meta_conversation_count
    turn = session.turn_count

    # 计算积分
    final_score, breakdown = calculate_final_score(
        user_guess=request.user_guess,
        opponent_type=session.opponent_type,
        confidence_level="mid",  # 场中判断默认为中等信心
        turn=turn,
        meta_count=meta_count,
        is_mid_game=True,  # 场中判断双倍乘数
    )

    # 更新会话
    session.triggered_mid_game = True
    session.confidence_level = "mid"
    session.is_correct = breakdown.is_correct
    session.final_score = int(final_score)
    session.score_breakdown = get_score_breakdown_dict(breakdown)
    session.ended_at = datetime.utcnow()

    # 更新用户积分
    score_before = user.score
    user.score += int(final_score)
    user.score_after = user.score

    if final_score > 0:
        user.total_score_earned += int(final_score)
    else:
        user.total_score_lost += abs(int(final_score))

    # 更新最高/最低分
    if user.score > user.highest_score:
        user.highest_score = user.score
    if user.score < user.lowest_score:
        user.lowest_score = user.score

    # 记录积分历史
    score_history = ScoreHistory(
        user_id=user.id,
        session_id=session.id,
        score_change=int(final_score),
        score_before=score_before,
        score_after=user.score,
        reason="mid_game_judgment",
    )
    db.add(score_history)

    # 更新用户统计
    await update_user_stats(db, user, session, breakdown.is_correct, meta_count)

    await db.commit()

    logger.info(
        f"场中判断：user_id={user.id}, session_id={session.id}, "
        f"guess={request.user_guess}, opponent={session.opponent_type}, "
        f"correct={breakdown.is_correct}, score={final_score}"
    )

    return GameResultResponse(
        session_id=session.id,
        opponent_type=session.opponent_type,
        user_guess=request.user_guess,
        is_correct=breakdown.is_correct,
        final_score=int(final_score),
        score_breakdown=get_score_breakdown_dict(breakdown),
    )


# =============================================================================
# 问卷提交
# =============================================================================

@router.post(
    "/survey",
    response_model=GameResultResponse,
    tags=["游戏"],
    summary="提交问卷",
    description="提交问卷和最终判断，结算积分",
)
async def submit_survey(
    request: SurveyRequest,
    session_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    问卷提交 API

    用户完成对话后填写问卷，包括身份判断、信心等级、流畅度评分等。
    """
    # 如果有 session_id，更新会话
    session = None
    user = None

    if session_id:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            # 获取用户
            result = await db.execute(
                select(User).where(User.id == session.user_id)
            )
            user = result.scalar_one_or_none()

    if session and user and session.ended_at is None:
        # 正常结束会话
        turn = session.turn_count
        meta_count = session.meta_conversation_count

        # 计算积分
        final_score, breakdown = calculate_final_score(
            user_guess=request.user_guess,
            opponent_type=session.opponent_type,
            confidence_level=request.confidence_level,
            turn=turn,
            meta_count=meta_count,
            is_mid_game=False,
        )

        # 更新会话
        session.confidence_level = request.confidence_level
        session.is_correct = breakdown.is_correct
        session.final_score = int(final_score)
        session.score_breakdown = get_score_breakdown_dict(breakdown)
        session.ended_at = datetime.utcnow()

        # 更新用户积分
        score_before = user.score
        user.score += int(final_score)

        if final_score > 0:
            user.total_score_earned += int(final_score)
        else:
            user.total_score_lost += abs(int(final_score))

        # 更新最高/最低分
        if user.score > user.highest_score:
            user.highest_score = user.score
        if user.score < user.lowest_score:
            user.lowest_score = user.score

        # 记录积分历史
        score_history = ScoreHistory(
            user_id=user.id,
            session_id=session.id,
            score_change=int(final_score),
            score_before=score_before,
            score_after=user.score,
            reason="session_end",
        )
        db.add(score_history)

        # 更新用户统计
        await update_user_stats(db, user, session, breakdown.is_correct, meta_count)

        await db.commit()

        logger.info(
            f"问卷提交：user_id={user.id}, session_id={session.id}, "
            f"guess={request.user_guess}, confidence={request.confidence_level}, "
            f"correct={breakdown.is_correct}, score={final_score}"
        )

        return GameResultResponse(
            session_id=session.id,
            opponent_type=session.opponent_type,
            user_guess=request.user_guess,
            is_correct=breakdown.is_correct,
            final_score=int(final_score),
            score_breakdown=get_score_breakdown_dict(breakdown),
        )
    else:
        # 没有会话或会话已结束，返回示例结果
        # 用于测试或特殊情况
        logger.warning(f"问卷提交：session_id={session_id} 不存在或已结束")

        # 创建一个虚拟结果
        breakdown = ScoreBreakdown(
            base_score=10,
            confidence_multiplier=1.0,
            meta_multiplier=1.0,
            turn_penalty=0,
            entry_fee=2,
            final_score=8,
            is_correct=True,
            opponent_type="ai",
            user_guess=request.user_guess,
        )

        return GameResultResponse(
            session_id=0,
            opponent_type="ai",
            user_guess=request.user_guess,
            is_correct=True,
            final_score=8,
            score_breakdown=get_score_breakdown_dict(breakdown),
        )


# =============================================================================
# 积分历史
# =============================================================================

@router.get(
    "/user/{user_id}/score-history",
    response_model=list[ScoreHistoryResponse],
    tags=["积分"],
    summary="积分历史",
    description="获取用户的积分变化历史记录",
)
async def get_score_history(
    user_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """获取用户积分历史"""
    result = await db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.user_id == user_id)
        .order_by(ScoreHistory.created_at.desc())
        .limit(limit)
    )
    histories = result.scalars().all()

    return [
        ScoreHistoryResponse(
            id=h.id,
            user_id=h.user_id,
            session_id=h.session_id,
            score_change=h.score_change,
            score_before=h.score_before,
            score_after=h.score_after,
            reason=h.reason,
            created_at=h.created_at,
        )
        for h in histories
    ]


# =============================================================================
# 积分预测
# =============================================================================

@router.get(
    "/game/prediction",
    tags=["游戏"],
    summary="积分预测",
    description="根据当前轮数和元对话次数，预测不同信心等级的收益/损失",
)
async def get_score_prediction(
    turn: int = 3,
    meta_count: int = 0,
    is_mid_game: bool = False,
):
    """获取积分预测"""
    prediction = calculate_score_prediction(turn, meta_count, is_mid_game)
    recommended = get_recommended_confidence(turn, meta_count, is_mid_game)

    return {
        "turn": turn,
        "meta_count": meta_count,
        "is_mid_game": is_mid_game,
        "prediction": {
            "low_confidence": prediction.low_confidence,
            "mid_confidence": prediction.mid_confidence,
            "high_confidence": prediction.high_confidence,
        },
        "multipliers": {
            "meta_multiplier": prediction.meta_multiplier,
            "penalty_multiplier": prediction.penalty_multiplier,
        },
        "penalties": {
            "turn_penalty": prediction.turn_penalty,
            "entry_fee": prediction.entry_fee,
        },
        "recommended_confidence": recommended,
    }


# =============================================================================
# 元对话乘数
# =============================================================================

@router.get(
    "/game/multipliers",
    tags=["游戏"],
    summary="元对话乘数",
    description="获取当前元对话次数对应的乘数",
)
async def get_multipliers(
    meta_count: int = 0,
):
    """获取元对话乘数"""
    from turing_test.backend.utils.score_calculator import (
        calculate_meta_multiplier,
        calculate_penalty_multiplier,
        is_high_frequency_meta,
    )

    meta_mult = calculate_meta_multiplier(meta_count)
    penalty_mult = calculate_penalty_multiplier(meta_count)
    is_high_freq = is_high_frequency_meta(meta_count)

    return {
        "meta_count": meta_count,
        "meta_multiplier": meta_mult,
        "penalty_multiplier": penalty_mult,
        "is_high_frequency": is_high_freq,
        "high_frequency_threshold": 5,
    }


# =============================================================================
# 辅助函数
# =============================================================================

async def update_user_stats(
    db: AsyncSession,
    user: User,
    session: Session,
    is_correct: bool,
    meta_count: int,
):
    """更新用户统计数据"""
    # 获取或创建用户统计
    result = await db.execute(
        select(UserStats).where(UserStats.user_id == user.id)
    )
    stats = result.scalar_one_or_none()

    if not stats:
        stats = UserStats(user_id=user.id)
        db.add(stats)

    # 更新会话统计
    stats.total_sessions += 1
    if session.opponent_type == "ai":
        stats.ai_sessions += 1
    elif session.opponent_type == "human":
        stats.human_sessions += 1
    elif session.opponent_type == "honeypot":
        stats.honeypot_sessions += 1

    # 更新判断统计
    if session.confidence_level:
        stats.total_guesses += 1
        if is_correct:
            stats.correct_guesses += 1
        stats.accuracy = stats.correct_guesses / stats.total_guesses if stats.total_guesses > 0 else 0

        # 信心等级统计
        if session.confidence_level == "low":
            stats.low_confidence_count += 1
        elif session.confidence_level == "mid":
            stats.mid_confidence_count += 1
        elif session.confidence_level == "high":
            stats.high_confidence_count += 1

    # 场中判断统计
    if session.triggered_mid_game:
        stats.mid_game_judgments += 1
        if is_correct:
            stats.mid_game_accuracy = (
                (stats.mid_game_judgments - 1) / stats.mid_game_judgments
                if stats.mid_game_judgments > 0 else 0
            )

    # 元对话统计
    stats.total_meta_conversations += meta_count
    if stats.total_sessions > 0:
        stats.avg_meta_per_session = stats.total_meta_conversations / stats.total_sessions
    if meta_count > stats.max_meta_in_one_session:
        stats.max_meta_in_one_session = meta_count

    # 轮数统计
    if stats.min_turns is None or session.turn_count < stats.min_turns:
        stats.min_turns = session.turn_count
    if stats.max_turns is None or session.turn_count > stats.max_turns:
        stats.max_turns = session.turn_count
    stats.avg_turns = (
        (stats.avg_turns * (stats.total_sessions - 1) + session.turn_count)
        / stats.total_sessions
        if stats.total_sessions > 0 else 0
    )

    # 时间统计（简化处理）
    if session.started_at and session.ended_at:
        duration = int((session.ended_at - session.started_at).total_seconds())
        stats.total_chat_time += duration
        stats.avg_session_duration = (
            (stats.avg_session_duration * (stats.total_sessions - 1) + duration)
            / stats.total_sessions
            if stats.total_sessions > 0 else 0
        )

    await db.flush()
