"""
游戏相关 API

包括：
- 问卷提交
- 积分历史
- 积分预测
- 元对话乘数查询
- 会话历史消息查询
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from loguru import logger
from pydantic import BaseModel, ConfigDict

from turing_test.backend.database import get_db
from turing_test.backend.models import User, Session, Message, ScoreHistory, UserStats, Survey
from turing_test.backend.schemas import (
    SurveyRequest,
    SurveyResponse,
    GameResultResponse,
    ScoreBreakdownResponse,
    ScoreHistoryResponse,
    SuccessResponse,
    ErrorResponse,
)
from turing_test.backend.utils.score_calculator import (
    calculate_final_score,
    get_score_breakdown_dict,
    calculate_score_prediction,
    get_recommended_confidence,
    apply_score_change,
    ScoreBreakdown,
)


def _normalize_opponent_type(opponent_type: str) -> str:
    """
    规范化对手类型，将 honeypot 隐藏为 ai，将 opponent 转换为实际类型

    这是为了向用户隐藏钓鱼机器人的存在，用户只需知道对手是"AI"或"真人"即可

    Args:
        opponent_type: 原始对手类型

    Returns:
        脱敏后的类型：'human' 或 'ai'
    """
    if opponent_type == "honeypot":
        return "ai"
    if opponent_type == "opponent":
        # "opponent" 是匹配时的临时掩码，需要根据其他字段还原真实类型
        # 这个情况不应该发生，因为调用此函数时应该传入真实类型
        # 这里做防御性处理，默认返回 "ai"
        return "ai"
    return opponent_type


# =============================================================================
# 消息响应 Schema
# =============================================================================

class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    session_id: int
    sender: str
    content: str
    is_meta_conversation: bool
    meta_keyword: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionMessagesResponse(BaseModel):
    """会话消息列表响应"""
    session_id: int
    opponent_type: str
    is_honeypot: bool
    turn_count: int
    meta_conversation_count: int
    messages: List[MessageResponse]

router = APIRouter()


# =============================================================================
# 结束会话
# =============================================================================

@router.post(
    "/session/{session_id}/end",
    response_model=SuccessResponse,
    tags=["游戏"],
    summary="结束会话",
    description="用户主动结束当前会话，仅标记会话结束，积分结算需在问卷提交时进行",
)
async def end_session(
    session_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    结束会话 API

    用户主动结束当前会话，仅标记会话结束时间，不进行积分结算。
    积分结算需在问卷提交时进行。
    支持传递 end_reason 字段指定结束原因。
    """
    from turing_test.backend.models import Session

    # 获取会话信息
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
            detail="会话已结束，无法重复操作",
        )

    # 获取结束原因，默认为 user_gave_up
    # 标准化值：user_normal_end（已判断后结束）, user_gave_up（未判断放弃）, sys_timeout（超时）
    end_reason = request.get("end_reason", "user_gave_up")

    # 设置结束时间和原因
    session.ended_at = datetime.now(timezone.utc)
    session.end_reason = end_reason
    await db.commit()

    # 清理匹配结果缓存（允许用户重新匹配）
    from turing_test.backend.services.match_service import get_match_service
    try:
        match_service = get_match_service()
        await match_service.clear_result(session.user_id)
        if session.opponent_user_id:
            await match_service.clear_result(session.opponent_user_id)
    except RuntimeError:
        pass  # 服务未初始化时忽略

    logger.info(f"用户主动结束会话：session_id={session_id}, reason={end_reason}")

    return SuccessResponse(
        success=True,
        message="会话已结束，请完成问卷提交以结算积分",
    )


# =============================================================================
# 获取会话历史消息
# =============================================================================

@router.get(
    "/session/{session_id}/messages",
    response_model=SessionMessagesResponse,
    tags=["游戏"],
    summary="获取会话历史消息",
    description="获取指定会话的所有历史消息记录",
)
async def get_session_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话历史消息 API

    返回指定会话的所有历史消息，包括发送者、内容、时间戳等信息。
    """
    # 获取会话信息
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    # 获取消息列表，按时间排序
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return SessionMessagesResponse(
        session_id=session.id,
        opponent_type=_normalize_opponent_type(session.opponent_type),
        is_honeypot=session.is_honeypot,
        turn_count=session.turn_count,
        meta_conversation_count=session.meta_conversation_count,
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                content=msg.content,
                is_meta_conversation=msg.is_meta_conversation,
                meta_keyword=msg.meta_keyword,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


# =============================================================================
# 问卷提交
# =============================================================================

@router.get(
    "/session/{session_id}/result",
    response_model=GameResultResponse,
    tags=["游戏"],
    summary="获取会话完整结果",
    description="获取会话的最终结果，包括积分、问卷数据等",
)
async def get_session_result(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话完整结果 API
    
    返回：
    - 会话基本信息
    - 最终得分（不暴露计算细节）
    - 用户提交的问卷数据
    """
    # 获取会话
    result = await db.execute(
        select(Session)
        .options(joinedload(Session.user))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 检查会话是否已结束
    if session.ended_at is None:
        raise HTTPException(
            status_code=400,
            detail="会话尚未结束，无法获取结果"
        )
    
    # 获取用户问卷
    survey_result = await db.execute(
        select(Survey).where(Survey.session_id == session_id)
    )
    survey = survey_result.scalar_one_or_none()
    
    # 构建简化的积分明细（不暴露计算细节）
    score_breakdown = ScoreBreakdownResponse(
        final_score=session.final_score or 0,
        is_correct=session.is_correct or False,
    )

    # 构建问卷响应
    survey_response = None
    if survey:
        survey_response = SurveyResponse(
            session_id=survey.session_id,
            user_guess=survey.user_guess,
            confidence_level=survey.confidence_level,
            fluency_rating=survey.fluency_rating,
            reason=survey.reason,
            self_role=survey.self_role,
            strategy=survey.strategy,
        )
    elif session.triggered_mid_game:
        # 场中判断后，尚未提交问卷时，使用 Session 中的值
        survey_response = SurveyResponse(
            session_id=session.id,
            user_guess=session.user_guess or "unknown",
            confidence_level=session.confidence_level or "high",
            fluency_rating=0,  # 尚未评分
            reason=None,
            self_role="other",  # 尚未选择
            strategy=None,
        )

    return GameResultResponse(
        session_id=session.id,
        opponent_type=_normalize_opponent_type(session.opponent_type),
        user_guess=session.user_guess if session.user_guess else ("unknown" if not survey else survey.user_guess),
        is_correct=session.is_correct or False,
        final_score=session.final_score or 0,
        score_breakdown=score_breakdown,
        survey=survey_response,
    )


@router.post(
    "/survey",
    response_model=GameResultResponse,
    tags=["游戏"],
    summary="提交问卷",
    description="提交问卷和最终判断，结算积分并保存问卷数据",
)
async def submit_survey(
    request: SurveyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    问卷提交 API

    完整流程：
    1. 验证会话存在且未结束
    2. 计算积分（后端独占逻辑，不返回计算细节）
    3. 保存问卷数据到数据库
    4. 更新会话状态
    5. 更新用户积分
    6. 返回简化结果
    """
    # 从请求体中获取 session_id
    session_id = request.session_id
    
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

    # 检查会话和用户是否存在
    if not session or not user:
        raise HTTPException(
            status_code=404,
            detail="会话不存在",
        )

    # 检查是否已提交过问卷（通过检查 Survey 表是否有记录）
    existing_survey = await db.execute(
        select(Survey).where(Survey.session_id == session.id)
    )
    if existing_survey.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="该会话的问卷已提交过，无法重复提交",
        )

    # 检查是否已进行场中判断
    if session.triggered_mid_game:
        # 场中判断后，使用 Session 中存储的值
        if not session.user_guess or not session.confidence_level:
            raise HTTPException(
                status_code=500,
                detail="场中判断数据不完整，无法提交问卷",
            )
        user_guess = session.user_guess
        confidence_level = session.confidence_level  # 'high'
        # 场中判断后积分已结算，无需重复计算
        final_score = session.final_score
        breakdown_is_correct = session.is_correct
        # 获取元对话次数用于统计更新
        meta_count = session.meta_conversation_count
    else:
        # 正常问卷提交，使用请求体中的值
        if not request.user_guess or not request.confidence_level:
            raise HTTPException(
                status_code=400,
                detail="缺少身份判断或信心等级",
            )
        user_guess = request.user_guess
        confidence_level = request.confidence_level

        # 计算积分
        turn = session.turn_count
        meta_count = session.meta_conversation_count

        # 获取对方判断信息
        opponent_guess = None
        opponent_confidence = None

        # 真人对战：从对手会话读取对方判断
        # 注意：opponent_type 可能是 "opponent"（真人对战时），需要结合 opponent_user_id 判断
        is_human_opponent = session.opponent_type == "human" or (
            session.opponent_type == "opponent" and session.opponent_user_id is not None
        )
        
        if is_human_opponent and session.opponent_session_id:
            opponent_session_result = await db.execute(
                select(Session).where(Session.id == session.opponent_session_id)
            )
            opponent_session = opponent_session_result.scalar_one_or_none()
            if opponent_session:
                # 对手的 user_guess 就是当前用户的 opponent_guess
                opponent_guess = opponent_session.user_guess
                opponent_confidence = opponent_session.confidence_level

        # 确定用户真实类型（Alice 是 AI，人类对手是 human）
        # 注意：honeypot 也属于 AI 类型
        is_ai = session.is_honeypot or session.opponent_type == "ai" or (
            session.opponent_type == "opponent" and session.opponent_user_id is None
        )
        user_actual_type = "ai" if is_ai else "human"

        final_score, breakdown = calculate_final_score(
            user_guess=user_guess,
            opponent_type=session.opponent_type,
            confidence_level=confidence_level,
            turn=turn,
            meta_count=meta_count,
            is_mid_game=False,
            opponent_guess=opponent_guess,
            opponent_confidence=opponent_confidence,
            user_actual_type=user_actual_type,
        )

        # 更新会话积分字段
        session.confidence_level = confidence_level
        session.is_correct = breakdown.is_correct
        session.final_score = int(final_score)
        session.score_breakdown = get_score_breakdown_dict(breakdown)
        # 更新对方猜错奖励字段
        session.opponent_guess = opponent_guess
        session.opponent_confidence = opponent_confidence
        session.bonus_from_opponent = int(breakdown.bonus_from_opponent_wrong) if breakdown.bonus_from_opponent_wrong else None
        breakdown_is_correct = breakdown.is_correct

    # 更新用户积分（场中判断后已计算过，跳过）
    if not session.triggered_mid_game:
        # 使用统一函数更新用户积分
        apply_score_change(
            user=user,
            session=session,
            score_change=int(final_score),
            reason="session_end",
            db=db,
            bonus_from_opponent=session.bonus_from_opponent,
            opponent_guess=session.opponent_guess,
            opponent_confidence=session.opponent_confidence,
            opponent_is_correct=not (opponent_guess == user_actual_type) if opponent_guess else None,
        )

    # 设置结束时间
    session.ended_at = datetime.now(timezone.utc)

    # 保存问卷数据
    survey_record = Survey(
        session_id=session.id,
        user_id=user.id,
        user_guess=user_guess,
        confidence_level=confidence_level,
        fluency_rating=request.fluency_rating,
        reason=request.reason,
        self_role=request.self_role,
        strategy=request.strategy,
    )
    db.add(survey_record)

    # 更新用户统计
    await update_user_stats(db, user, session, breakdown_is_correct, meta_count)

    await db.commit()

    logger.info(
        f"问卷提交：user_id={user.id}, session_id={session.id}, "
        f"guess={user_guess}, confidence={confidence_level}, "
        f"correct={breakdown_is_correct}, score={final_score}"
    )

    # 构建简化的积分明细
    score_breakdown = ScoreBreakdownResponse(
        final_score=int(final_score),
        is_correct=breakdown_is_correct,
    )

    # 构建问卷响应
    survey_response = SurveyResponse(
        session_id=session.id,
        user_guess=user_guess,
        confidence_level=confidence_level,
        fluency_rating=request.fluency_rating,
        reason=request.reason,
        self_role=request.self_role,
        strategy=request.strategy,
    )

    return GameResultResponse(
        session_id=session.id,
        opponent_type=_normalize_opponent_type(session.opponent_type),
        user_guess=user_guess,
        is_correct=breakdown_is_correct,
        final_score=int(final_score),
        score_breakdown=score_breakdown,
        survey=survey_response,
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
    # 注意：需要处理 opponent_type="opponent" 的情况（真人对战时的临时掩码）
    stats.total_sessions += 1
    is_ai = session.is_honeypot or session.opponent_type == "ai" or (
        session.opponent_type == "opponent" and session.opponent_user_id is None
    )
    is_human = session.opponent_type == "human" or (
        session.opponent_type == "opponent" and session.opponent_user_id is not None
    )
    
    if is_ai:
        # 将 honeypot 合并到 AI 统计中，向用户隐藏钓鱼机器人的存在
        stats.ai_sessions += 1
    elif is_human:
        stats.human_sessions += 1

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
        # 统一时区处理：如果一个是时区感知，另一个是时区非感知，则统一移除时区信息
        started_at = session.started_at
        ended_at = session.ended_at
        # 检查时区一致性
        if started_at.tzinfo is not None and ended_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=None)
        elif started_at.tzinfo is None and ended_at.tzinfo is not None:
            ended_at = ended_at.replace(tzinfo=None)
        duration = int((ended_at - started_at).total_seconds())
        stats.total_chat_time += duration
        stats.avg_session_duration = (
            (stats.avg_session_duration * (stats.total_sessions - 1) + duration)
            / stats.total_sessions
            if stats.total_sessions > 0 else 0
        )

    await db.flush()
