// 积分预测计算
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'

export function useScorePrediction() {
  const gameStore = useGameStore()

  // 常量定义
  const ENTRY_FEE = 2
  const TURN_PENALTY_RATE = 0.5
  const MIN_FREE_TURNS = 3

  // 基础分（假设对手是 AI）
  const BASE_REWARD_IDENTIFY_AI = 10     // 识别 AI 正确
  const BASE_PENALTY_MISIDENTIFY_AI = -15  // 误判 AI 为真人

  // 信心等级倍数
  const CONFIDENCE_MULTIPLIERS = {
    low: 1.0,
    mid: 2.5,
    high: 5.0
  }

  // 计算轮数惩罚
  const turnPenalty = computed(() => {
    return Math.max(0, (gameStore.turn - MIN_FREE_TURNS) * TURN_PENALTY_RATE)
  })

  // 计算元对话倍数
  const metaMultiplier = computed(() => {
    const count = gameStore.metaConversationCount
    return 1 + (count * 0.2)
  })

  // 计算惩罚倍数（错误时的倍数）
  const penaltyMultiplier = computed(() => {
    const count = gameStore.metaConversationCount
    return 1 + (count * 0.3)
  })

  // 计算积分预测
  const prediction = computed(() => {
    const metaMult = metaMultiplier.value
    const penaltyMult = penaltyMultiplier.value
    const penalty = turnPenalty.value

    // 低信心预测
    const lowConfidence = {
      correct: (BASE_REWARD_IDENTIFY_AI * CONFIDENCE_MULTIPLIERS.low * metaMult) - ENTRY_FEE - penalty,
      wrong: (BASE_PENALTY_MISIDENTIFY_AI * CONFIDENCE_MULTIPLIERS.low * penaltyMult) - ENTRY_FEE - penalty
    }

    // 中信心预测
    const midConfidence = {
      correct: (BASE_REWARD_IDENTIFY_AI * CONFIDENCE_MULTIPLIERS.mid * metaMult) - ENTRY_FEE - penalty,
      wrong: (BASE_PENALTY_MISIDENTIFY_AI * CONFIDENCE_MULTIPLIERS.mid * penaltyMult) - ENTRY_FEE - penalty
    }

    // 高信心预测
    const highConfidence = {
      correct: (BASE_REWARD_IDENTIFY_AI * CONFIDENCE_MULTIPLIERS.high * metaMult) - ENTRY_FEE - penalty,
      wrong: (BASE_PENALTY_MISIDENTIFY_AI * CONFIDENCE_MULTIPLIERS.high * penaltyMult) - ENTRY_FEE - penalty
    }

    return {
      lowConfidence,
      midConfidence,
      highConfidence,
      metaMultiplier: metaMult,
      penaltyMultiplier: penaltyMult,
      turnPenalty: penalty,
      entryFee: ENTRY_FEE
    }
  })

  // 格式化显示
  const formattedPrediction = computed(() => ({
    lowConfidence: {
      correct: prediction.value.lowConfidence.correct.toFixed(1),
      wrong: prediction.value.lowConfidence.wrong.toFixed(1)
    },
    midConfidence: {
      correct: prediction.value.midConfidence.correct.toFixed(1),
      wrong: prediction.value.midConfidence.wrong.toFixed(1)
    },
    highConfidence: {
      correct: prediction.value.highConfidence.correct.toFixed(1),
      wrong: prediction.value.highConfidence.wrong.toFixed(1)
    },
    metaMultiplier: prediction.value.metaMultiplier.toFixed(1),
    penaltyMultiplier: prediction.value.penaltyMultiplier.toFixed(1),
    turnPenalty: prediction.value.turnPenalty.toFixed(1),
    entryFee: prediction.value.entryFee
  }))

  // 获取最优信心等级（收益最高）
  const optimalConfidence = computed(() => {
    const preds = [
      { level: '低信心', correct: prediction.value.lowConfidence.correct },
      { level: '中信心', correct: prediction.value.midConfidence.correct },
      { level: '高信心', correct: prediction.value.highConfidence.correct }
    ]
    return preds.reduce((max, curr) =>
      curr.correct > max.correct ? curr : max
    )
  })

  // 计算场中判断的积分预测
  function calculateMidGamePrediction(
    baseReward: number,
    basePenalty: number
  ) {
    const metaMult = metaMultiplier.value
    const penaltyMult = penaltyMultiplier.value
    const penalty = turnPenalty.value

    // 场中判断倍数
    const MID_GAME_CORRECT_MULTIPLIER = 2.0
    const MID_GAME_WRONG_MULTIPLIER = 1.5

    // 计算
    const correctScore = (baseReward * MID_GAME_CORRECT_MULTIPLIER * metaMult) - ENTRY_FEE - penalty
    const wrongScore = (basePenalty * MID_GAME_WRONG_MULTIPLIER * penaltyMult) - ENTRY_FEE - penalty

    return {
      correct: correctScore.toFixed(1),
      wrong: wrongScore.toFixed(1),
      multiplier: `×${metaMult.toFixed(1)} (场中双倍)`,
      riskLevel: wrongScore < -100 ? '高风险' : '中等风险'
    }
  }

  return {
    prediction,
    formattedPrediction,
    optimalConfidence,
    turnPenalty,
    metaMultiplier,
    penaltyMultiplier,
    calculateMidGamePrediction
  }
}
