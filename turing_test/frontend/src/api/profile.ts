// 用户统计相关API
import api from './index'
import type { UserStats, ScoreHistory, Session } from '@/types'

/**
 * 获取用户统计信息
 */
export async function getUserStats(userId: number): Promise<UserStats> {
  return api.get(`/user/${userId}/stats`)
}

/**
 * 获取用户历史记录
 */
export async function getUserHistory(userId: number): Promise<Session[]> {
  return api.get(`/user/${userId}/history`)
}

/**
 * 获取用户积分历史
 */
export async function getUserScoreHistory(userId: number): Promise<ScoreHistory[]> {
  return api.get(`/user/${userId}/score-history`)
}

/**
 * 获取用户完整信息（包括统计和历史）
 */
export async function getUserFullProfile(userId: number): Promise<{
  stats: UserStats
  history: Session[]
  scoreHistory: ScoreHistory[]
}> {
  return api.get(`/user/${userId}/profile`)
}