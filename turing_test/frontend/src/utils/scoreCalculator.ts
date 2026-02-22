// 积分计算工具函数

import type { ScorePrediction } from '@/types/game'
import {
  ENTRY_FEE,
  TURN_PENALTY_RATE,
  MIN_FREE_TURNS,
  CONFIDENCE_MULTIPLIER
} from './constants'

/**
 * 计算积分预测
 * @param turn 当前轮数
 * @param metaCount 元对话次数
 * @returns 积分预测结果
 */
export function calculateScorePrediction(
  turn: number,
  metaCount: number
): ScorePrediction {
  // 计算轮数惩罚
  const turnPenalty = Math.max(0, (turn - MIN_FREE_TURNS) * TURN_PENALTY_RATE)

  // 计算元对话乘数
  const metaMultiplier = 1 + (metaCount * 0.2)
  const penaltyMultiplier = 1 + (metaCount * 0.3)

  // 基础奖励/惩罚
  const baseRewardIdentifyAI = 10   // 识别 AI 正确
  const basePenaltyMisidentifyAI = -15  // 误判 AI 为真人

  // 计算不同信心等级的预测
  const lowConfidence = CONFIDENCE_MULTIPLIER.low
  const midConfidence = CONFIDENCE_MULTIPLIER.mid
  const highConfidence = CONFIDENCE_MULTIPLIER.high

  return {
    lowConfidence: {
      correct: (baseRewardIdentifyAI * lowConfidence * metaMultiplier) - ENTRY_FEE - turnPenalty,
      wrong: (basePenaltyMisidentifyAI * lowConfidence * penaltyMultiplier) - ENTRY_FEE - turnPenalty
    },
    midConfidence: {
      correct: (baseRewardIdentifyAI * midConfidence * metaMultiplier) - ENTRY_FEE - turnPenalty,
      wrong: (basePenaltyMisidentifyAI * midConfidence * penaltyMultiplier) - ENTRY_FEE - turnPenalty
    },
    highConfidence: {
      correct: (baseRewardIdentifyAI * highConfidence * metaMultiplier) - ENTRY_FEE - turnPenalty,
      wrong: (basePenaltyMisidentifyAI * highConfidence * penaltyMultiplier) - ENTRY_FEE - turnPenalty
    },
    metaMultiplier,
    penaltyMultiplier,
    turnPenalty,
    entryFee: ENTRY_FEE
  }
}

/**
 * 计算场中判断的积分预测
 * @param turn 当前轮数
 * @param metaCount 元对话次数
 * @returns 场中判断的积分预测
 */
export function calculateMidGameScorePrediction(
  turn: number,
  metaCount: number
): { correct: number; wrong: number } {
  const turnPenalty = Math.max(0, (turn - MIN_FREE_TURNS) * TURN_PENALTY_RATE)
  const metaMultiplier = 1 + (metaCount * 0.2)
  const penaltyMultiplier = 1 + (metaCount * 0.3)

  const baseRewardIdentifyAI = 10
  const basePenaltyMisidentifyAI = -15

  // 场中判断：正确×2.0，错误×1.5
  return {
    correct: (baseRewardIdentifyAI * 2.0 * metaMultiplier) - ENTRY_FEE - turnPenalty,
    wrong: (basePenaltyMisidentifyAI * 1.5 * penaltyMultiplier) - ENTRY_FEE - turnPenalty
  }
}

/**
 * 计算元对话乘数信息
 * @param metaCount 元对话次数
 * @returns 乘数信息
 */
export function calculateMultipliers(metaCount: number) {
  return {
    metaMultiplier: 1 + (metaCount * 0.2),
    penaltyMultiplier: 1 + (metaCount * 0.3)
  }
}
