/**
 * Result.vue 相关类型定义
 */

/**
 * 问卷数据
 */
export interface SurveyData {
  user_guess: 'human' | 'ai' | 'unsure'
  confidence_level?: 'low' | 'mid' | 'high'  // 场中判断后无需填写
  fluency_rating: number
  reason?: string
  self_role: 'prover' | 'interferer' | 'other'
  strategy?: string
  // 文本展示版本
  user_guess_text?: string
  confidence_level_text?: string
  self_role_text?: string
}

/**
 * 积分明细（简化版 - 不暴露计算细节）
 */
export interface ScoreBreakdownDisplay {
  final_score: number
  is_correct: boolean
  // 对方猜错奖励字段
  opponent_guess?: string
  opponent_confidence?: string
  opponent_is_correct?: boolean
  opponent_score_if_correct?: number
  bonus_from_opponent_wrong?: number
}

/**
 * 游戏结果响应
 */
export interface GameResultResponse {
  session_id: number
  opponent_type: string
  user_guess: string
  is_correct: boolean
  final_score: number
  score_breakdown: ScoreBreakdownDisplay
  survey?: SurveyData
}

/**
 * 对手类型展示配置
 */
export interface OpponentTypeConfig {
  text: string
  avatar: string
  class: string
  color: string
  bg: string
  border: string
}

/**
 * 信心等级展示配置
 */
export interface ConfidenceLevelConfig {
  text: string
  icon: string
}

/**
 * 用户角色展示配置
 */
export interface SelfRoleConfig {
  text: string
  icon: string
}
