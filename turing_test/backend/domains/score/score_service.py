"""
积分结算领域 - 事务性结算流程

设计原则:
1. 事务性 - 积分变更必须在事务内完成
2. 可追溯 - 所有积分变更都有记录
3. 幂等性 - 同一请求不会重复结算
4. 两次结算 - 基础积分 + 对方猜错奖励

积分规则:
- 入场券：2 分
- 识别 AI 正确：+10 分 × 信心倍率
- 误判 AI: -15 分 × 信心倍率
- 轮数惩罚：超过 3 轮后每轮 -0.5 分
- 元对话倍率：每次元对话 +1 倍率
- 场中判断：双倍积分
- 对方猜错奖励：对方误判的绝对值
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from turing_test.backend.infrastructure.events.event_bus import (
    EventBus, EventType, EventBuilder, event_bus,
)
from turing_test.backend.infrastructure.cqrs.cqrs import (
    Command, CommandHandler, CommandResult,
    Query, QueryHandler,
    SubmitJudgmentCommand, ClaimBonusCommand,
    GetScoreQuery, GetScoreHistoryQuery,
)

logger = logging.getLogger(__name__)


# ============== 常量定义 ==============

ENTRY_FEE = Decimal("2")
TURN_PENALTY_RATE = Decimal("0.5")
MIN_FREE_TURNS = 3

BASE_REWARD_IDENTIFY_AI = Decimal("10")
BASE_PENALTY_MISIDENTIFY_AI = Decimal("-15")

CONFIDENCE_MULTIPLIERS = {
    "low": Decimal("1.0"),
    "mid": Decimal("2.5"),
    "high": Decimal("5.0"),
}

MID_GAME_MULTIPLIER = Decimal("2.0")
META_CONVERSATION_BONUS = Decimal("1.0")  # 每次元对话增加的倍率


# ============== 枚举类型 ==============


class ScoreType(Enum):
    """积分类型"""
    BASE = "base"              # 基础积分
    OPPONENT_BONUS = "opponent_bonus"  # 对方猜错奖励
    REFERRAL = "referral"      # 推荐奖励
    ADMIN_ADJUSTMENT = "admin_adjustment"  # 管理员调整


class JudgmentResult(Enum):
    """判断结果"""
    CORRECT_IDENTIFY_AI = "correct_identify_ai"
    CORRECT_IDENTIFY_HUMAN = "correct_identify_human"
    MISIDENTIFY_AI = "misidentify_ai"
    MISIDENTIFY_HUMAN = "misidentify_human"


# ============== 值对象 ==============


@dataclass(frozen=True)
class ScoreBreakdown:
    """
    积分明细 - 不可变值对象
    
    用于详细记录积分计算过程
    """
    base_score: Decimal = Decimal("0")
    confidence_multiplier: Decimal = Decimal("1.0")
    meta_multiplier: Decimal = Decimal("1.0")
    mid_game_multiplier: Decimal = Decimal("1.0")
    entry_fee: Decimal = ENTRY_FEE
    turn_penalty: Decimal = Decimal("0")
    opponent_bonus: Decimal = Decimal("0")
    
    @property
    def calculated_score(self) -> Decimal:
        """计算最终得分"""
        base = self.base_score * self.confidence_multiplier * self.meta_multiplier * self.mid_game_multiplier
        return base - self.entry_fee - self.turn_penalty + self.opponent_bonus
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "base_score": float(self.base_score),
            "confidence_multiplier": float(self.confidence_multiplier),
            "meta_multiplier": float(self.meta_multiplier),
            "mid_game_multiplier": float(self.mid_game_multiplier),
            "entry_fee": float(self.entry_fee),
            "turn_penalty": float(self.turn_penalty),
            "opponent_bonus": float(self.opponent_bonus),
            "total": float(self.calculated_score),
        }


@dataclass
class ScoreHistory:
    """
    积分历史记录
    
    所有积分变更都必须创建记录
    """
    id: Optional[int]
    user_id: int
    session_id: int
    score_type: ScoreType
    score_change: Decimal
    score_before: Decimal
    score_after: Decimal
    breakdown: Optional[ScoreBreakdown]
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============== 领域服务 ==============


class ScoreCalculator:
    """
    积分计算器 - 纯函数式计算
    
    无副作用，只负责计算逻辑
    """
    
    @staticmethod
    def calculate_base_score(
        user_guess: str,
        opponent_type: str,
        confidence_level: str,
        turn_count: int,
        meta_count: int,
        is_mid_game: bool = False,
    ) -> Tuple[Decimal, ScoreBreakdown]:
        """
        计算基础积分
        
        Returns:
            (最终得分，积分明细)
        """
        # 1. 判断是否正确
        is_correct = (
            (user_guess == "ai" and opponent_type in ["bot", "honeypot", "ai"]) or
            (user_guess == "human" and opponent_type == "human")
        )
        
        # 2. 确定基础分
        if is_correct:
            if user_guess == "ai":
                base_score = BASE_REWARD_IDENTIFY_AI
                description = "Correctly identified AI"
            else:
                base_score = BASE_REWARD_IDENTIFY_AI  # 识别真人也奖励
                description = "Correctly identified human"
        else:
            base_score = BASE_PENALTY_MISIDENTIFY_AI
            description = "Misidentified opponent"
        
        # 3. 获取信心倍率
        confidence_mult = CONFIDENCE_MULTIPLIERS.get(confidence_level.lower(), Decimal("1.0"))
        
        # 4. 计算元对话倍率
        meta_mult = Decimal("1.0") + (Decimal(meta_count) * META_CONVERSATION_BONUS)
        
        # 5. 场中判断双倍
        mid_game_mult = MID_GAME_MULTIPLIER if is_mid_game else Decimal("1.0")
        
        # 6. 计算轮数惩罚
        penalty_turns = max(0, turn_count - MIN_FREE_TURNS)
        turn_penalty = Decimal(penalty_turns) * TURN_PENALTY_RATE
        
        # 7. 计算最终得分
        calculated = (
            base_score * confidence_mult * meta_mult * mid_game_mult
            - ENTRY_FEE
            - turn_penalty
        )
        
        breakdown = ScoreBreakdown(
            base_score=base_score,
            confidence_multiplier=confidence_mult,
            meta_multiplier=meta_mult,
            mid_game_multiplier=mid_game_mult,
            turn_penalty=turn_penalty,
        )
        
        return calculated, breakdown
    
    @staticmethod
    def calculate_opponent_bonus(
        opponent_guess: str,
        opponent_confidence: str,
        user_actual_type: str,
        opponent_turn_count: int,
    ) -> Tuple[Decimal, ScoreBreakdown]:
        """
        计算对方猜错奖励
        
        奖励 = 对方如果正确会得到的积分的绝对值
        """
        # 判断对方是否猜错
        opponent_is_correct = (
            (opponent_guess == "ai" and user_actual_type in ["bot", "honeypot", "ai"]) or
            (opponent_guess == "human" and user_actual_type == "human")
        )
        
        if opponent_is_correct:
            return Decimal("0"), ScoreBreakdown()
        
        # 计算对方如果正确会得到的积分
        opponent_base, opponent_breakdown = ScoreCalculator.calculate_base_score(
            user_guess=opponent_guess,
            opponent_type=user_actual_type,
            confidence_level=opponent_confidence,
            turn_count=opponent_turn_count,
            meta_count=0,
            is_mid_game=False,
        )
        
        # 奖励是对方积分的绝对值
        bonus = abs(opponent_base)
        
        breakdown = ScoreBreakdown(
            base_score=bonus,
            opponent_bonus=bonus,
        )
        
        return bonus, breakdown
    
    @staticmethod
    def calculate_final_score(
        user_guess: str,
        opponent_type: str,
        confidence_level: str,
        turn_count: int,
        meta_count: int,
        is_mid_game: bool = False,
        opponent_guess: Optional[str] = None,
        opponent_confidence: Optional[str] = None,
        user_actual_type: str = "ai",
        opponent_turn_count: Optional[int] = None,
    ) -> Tuple[Decimal, ScoreBreakdown]:
        """
        计算最终积分 (基础分 + 对方猜错奖励)
        """
        # 1. 计算基础分
        base_score, base_breakdown = ScoreCalculator.calculate_base_score(
            user_guess=user_guess,
            opponent_type=opponent_type,
            confidence_level=confidence_level,
            turn_count=turn_count,
            meta_count=meta_count,
            is_mid_game=is_mid_game,
        )
        
        # 2. 计算对方猜错奖励
        opponent_bonus = Decimal("0")
        if opponent_guess and opponent_confidence and opponent_turn_count:
            opponent_bonus, _ = ScoreCalculator.calculate_opponent_bonus(
                opponent_guess=opponent_guess,
                opponent_confidence=opponent_confidence,
                user_actual_type=user_actual_type,
                opponent_turn_count=opponent_turn_count,
            )
        
        # 3. 合并
        total = base_score + opponent_bonus
        
        breakdown = ScoreBreakdown(
            base_score=base_breakdown.base_score,
            confidence_multiplier=base_breakdown.confidence_multiplier,
            meta_multiplier=base_breakdown.meta_multiplier,
            mid_game_multiplier=base_breakdown.mid_game_multiplier,
            entry_fee=base_breakdown.entry_fee,
            turn_penalty=base_breakdown.turn_penalty,
            opponent_bonus=opponent_bonus,
        )
        
        return total, breakdown


# ============== 仓库接口 ==============


class ScoreRepository:
    """积分仓库接口"""
    
    async def get_user_score(self, user_id: int) -> Decimal:
        """获取用户积分"""
        raise NotImplementedError
    
    async def set_user_score(self, user_id: int, score: Decimal):
        """设置用户积分"""
        raise NotImplementedError
    
    async def update_user_score(self, user_id: int, delta: Decimal) -> Decimal:
        """更新用户积分 (原子操作)"""
        raise NotImplementedError
    
    async def add_history(self, history: ScoreHistory) -> ScoreHistory:
        """添加积分历史记录"""
        raise NotImplementedError
    
    async def get_history(
        self,
        user_id: int,
        session_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[ScoreHistory]:
        """获取积分历史"""
        raise NotImplementedError


class SessionScoreRepository:
    """会话积分状态仓库"""
    
    async def mark_base_score_settled(self, session_id: int):
        """标记基础积分已结算"""
        raise NotImplementedError
    
    async def mark_opponent_bonus_pending(self, session_id: int):
        """标记对方猜错奖励待领取"""
        raise NotImplementedError
    
    async def mark_opponent_bonus_claimed(self, session_id: int):
        """标记对方猜错奖励已领取"""
        raise NotImplementedError
    
    async def is_base_score_settled(self, session_id: int) -> bool:
        """检查基础积分是否已结算"""
        raise NotImplementedError
    
    async def is_opponent_bonus_pending(self, session_id: int) -> bool:
        """检查是否有待领取的对方猜错奖励"""
        raise NotImplementedError


# ============== 命令处理器 ==============


class SubmitJudgmentHandler(CommandHandler[ScoreBreakdown]):
    """
    提交判断命令处理器
    
    处理场中判断和最终结算
    """
    
    def __init__(
        self,
        score_repo: ScoreRepository,
        session_repo: SessionScoreRepository,
        event_bus: EventBus,
        calculator: ScoreCalculator = None,
    ):
        self._score_repo = score_repo
        self._session_repo = session_repo
        self._event_bus = event_bus
        self._calculator = calculator or ScoreCalculator()
    
    async def handle(self, command: SubmitJudgmentCommand) -> CommandResult[ScoreBreakdown]:
        try:
            # 1. 检查是否已结算
            if not command.is_mid_game:
                already_settled = await self._session_repo.is_base_score_settled(command.session_id)
                if already_settled:
                    return CommandResult.fail("Score already settled", "ALREADY_SETTLED")
            
            # 2. 获取会话信息 (用于计算积分)
            # TODO: 从会话域获取
            session_info = await self._get_session_info(command.session_id)
            if not session_info:
                return CommandResult.fail("Session not found", "NOT_FOUND")
            
            # 3. 计算积分
            final_score, breakdown = self._calculator.calculate_final_score(
                user_guess=command.guess,
                opponent_type=session_info["opponent_type"],
                confidence_level=command.confidence,
                turn_count=session_info["turn_count"],
                meta_count=session_info["meta_count"],
                is_mid_game=command.is_mid_game,
                opponent_guess=session_info.get("opponent_guess"),
                opponent_confidence=session_info.get("opponent_confidence"),
                user_actual_type=session_info["actual_type"],
                opponent_turn_count=session_info.get("opponent_turn_count"),
            )
            
            # 4. 发布计算中事件
            await EventBuilder(EventType.SCORE_CALCULATING)\
                .aggregate(str(command.session_id), "session")\
                .with_data(guess=command.guess, is_mid_game=command.is_mid_game)\
                .publish(self._event_bus)
            
            # 5. 如果是最终结算，更新积分
            if not command.is_mid_game:
                current_score = await self._score_repo.get_user_score(command.user_id)
                new_score = current_score + final_score
                
                # 原子更新
                await self._score_repo.update_user_score(command.user_id, final_score)
                
                # 记录历史
                history = ScoreHistory(
                    id=None,
                    user_id=command.user_id,
                    session_id=command.session_id,
                    score_type=ScoreType.BASE,
                    score_change=final_score,
                    score_before=current_score,
                    score_after=new_score,
                    breakdown=breakdown,
                    description=f"Session {command.session_id} final score",
                    metadata={
                        "guess": command.guess,
                        "confidence": command.confidence,
                        "meta_keywords": command.meta_keywords,
                    },
                )
                await self._score_repo.add_history(history)
                
                # 标记会话已结算
                await self._session_repo.mark_base_score_settled(command.session_id)
                
                # 检查是否有对方猜错奖励待领取
                if session_info.get("opponent_guess") and not self._is_correct_guess(
                    session_info["opponent_guess"], session_info["actual_type"]
                ):
                    await self._session_repo.mark_opponent_bonus_pending(command.session_id)
            
            # 6. 发布结算事件
            await EventBuilder(EventType.SCORE_SETTLED)\
                .aggregate(str(command.session_id), "session")\
                .with_data(
                    score=float(final_score),
                    breakdown=breakdown.to_dict(),
                    is_mid_game=command.is_mid_game,
                )\
                .publish(self._event_bus)
            
            return CommandResult.ok(data=breakdown)
            
        except Exception as e:
            logger.exception(f"Failed to submit judgment: {e}")
            await EventBuilder(EventType.SCORE_ERROR)\
                .aggregate(str(command.session_id), "session")\
                .with_data(error=str(e))\
                .publish(self._event_bus)
            return CommandResult.fail(str(e), "SUBMIT_ERROR")
    
    def _is_correct_guess(self, guess: str, actual_type: str) -> bool:
        """判断是否正确"""
        if guess == "ai":
            return actual_type in ["bot", "honeypot", "ai"]
        else:
            return actual_type == "human"
    
    async def _get_session_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        # TODO: 从会话域获取
        return {
            "opponent_type": "bot",
            "turn_count": 5,
            "meta_count": 0,
            "actual_type": "ai",
        }


class ClaimBonusHandler(CommandHandler[Decimal]):
    """领取对方猜错奖励命令处理器"""
    
    def __init__(
        self,
        score_repo: ScoreRepository,
        session_repo: SessionScoreRepository,
        event_bus: EventBus,
    ):
        self._score_repo = score_repo
        self._session_repo = session_repo
        self._event_bus = event_bus
    
    async def handle(self, command: ClaimBonusCommand) -> CommandResult[Decimal]:
        try:
            # 1. 检查是否有待领取的奖励
            is_pending = await self._session_repo.is_opponent_bonus_pending(command.session_id)
            if not is_pending:
                return CommandResult.fail("No pending bonus", "NO_BONUS")
            
            # 2. 获取会话信息计算奖励
            session_info = await self._get_session_info(command.session_id)
            
            bonus, breakdown = ScoreCalculator.calculate_opponent_bonus(
                opponent_guess=session_info["opponent_guess"],
                opponent_confidence=session_info["opponent_confidence"],
                user_actual_type=session_info["actual_type"],
                opponent_turn_count=session_info["opponent_turn_count"],
            )
            
            if bonus <= 0:
                return CommandResult.fail("No bonus to claim", "NO_BONUS")
            
            # 3. 更新积分
            current_score = await self._score_repo.get_user_score(command.user_id)
            await self._score_repo.update_user_score(command.user_id, bonus)
            
            # 4. 记录历史
            history = ScoreHistory(
                id=None,
                user_id=command.user_id,
                session_id=command.session_id,
                score_type=ScoreType.OPPONENT_BONUS,
                score_change=bonus,
                score_before=current_score,
                score_after=current_score + bonus,
                breakdown=breakdown,
                description=f"Claimed opponent bonus from session {command.session_id}",
            )
            await self._score_repo.add_history(history)
            
            # 5. 标记已领取
            await self._session_repo.mark_opponent_bonus_claimed(command.session_id)
            
            # 6. 发布事件
            await EventBuilder(EventType.SCORE_BONUS_CLAIMED)\
                .aggregate(str(command.session_id), "session")\
                .with_data(bonus=float(bonus))\
                .publish(self._event_bus)
            
            return CommandResult.ok(data=bonus)
            
        except Exception as e:
            logger.exception(f"Failed to claim bonus: {e}")
            return CommandResult.fail(str(e), "CLAIM_ERROR")
    
    async def _get_session_info(self, session_id: int) -> Dict[str, Any]:
        """获取会话信息"""
        # TODO: 从会话域获取
        return {
            "opponent_guess": "human",
            "opponent_confidence": "mid",
            "actual_type": "ai",
            "opponent_turn_count": 5,
        }


# ============== 查询处理器 ==============


@dataclass
class ScoreDTO:
    """积分 DTO"""
    user_id: int
    total_score: float
    rank: Optional[int] = None
    last_updated: Optional[datetime] = None


class GetScoreHandler(QueryHandler[ScoreDTO]):
    """获取积分查询处理器"""
    
    def __init__(self, repository: ScoreRepository):
        self._repository = repository
    
    async def handle(self, query: GetScoreQuery) -> ScoreDTO:
        score = await self._repository.get_user_score(query.user_id)
        
        return ScoreDTO(
            user_id=query.user_id,
            total_score=float(score),
        )


class GetScoreHistoryHandler(QueryHandler[List[Dict[str, Any]]]):
    """获取积分历史查询处理器"""
    
    def __init__(self, repository: ScoreRepository):
        self._repository = repository
    
    async def handle(self, query: GetScoreHistoryQuery) -> List[Dict[str, Any]]:
        histories = await self._repository.get_history(
            query.user_id,
            query.session_id,
            query.limit,
        )
        
        return [
            {
                "id": h.id,
                "session_id": h.session_id,
                "score_type": h.score_type.value,
                "score_change": float(h.score_change),
                "score_after": float(h.score_after),
                "description": h.description,
                "created_at": h.created_at.isoformat(),
                "breakdown": h.breakdown.to_dict() if h.breakdown else None,
            }
            for h in histories
        ]


# ============== 积分服务 (外观) ==============


class ScoreService:
    """
    积分服务 - 统一外观接口
    """
    
    def __init__(
        self,
        command_bus,
        query_bus,
        calculator: ScoreCalculator = None,
    ):
        self._command_bus = command_bus
        self._query_bus = query_bus
        self._calculator = calculator or ScoreCalculator()
    
    async def submit_judgment(
        self,
        session_id: int,
        user_id: int,
        guess: str,
        confidence: str,
        is_mid_game: bool = False,
        meta_keywords: Optional[List[str]] = None,
    ) -> CommandResult[ScoreBreakdown]:
        """提交判断"""
        command = SubmitJudgmentCommand(
            session_id=session_id,
            user_id=user_id,
            guess=guess,
            confidence=confidence,
            is_mid_game=is_mid_game,
            meta_keywords=meta_keywords or [],
        )
        return await self._command_bus.dispatch(command)
    
    async def claim_bonus(self, session_id: int, user_id: int) -> CommandResult[Decimal]:
        """领取对方猜错奖励"""
        command = ClaimBonusCommand(session_id=session_id, user_id=user_id)
        return await self._command_bus.dispatch(command)
    
    async def get_score(self, user_id: int) -> ScoreDTO:
        """获取积分"""
        query = GetScoreQuery(user_id=user_id)
        return await self._query_bus.dispatch(query)
    
    async def get_score_history(self, user_id: int, session_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取积分历史"""
        query = GetScoreHistoryQuery(user_id=user_id, session_id=session_id)
        return await self._query_bus.dispatch(query)
    
    def calculate_preview(
        self,
        user_guess: str,
        opponent_type: str,
        confidence: str,
        turn_count: int,
        meta_count: int,
    ) -> ScoreBreakdown:
        """预览积分计算结果 (不实际结算)"""
        _, breakdown = self._calculator.calculate_final_score(
            user_guess=user_guess,
            opponent_type=opponent_type,
            confidence_level=confidence,
            turn_count=turn_count,
            meta_count=meta_count,
        )
        return breakdown
