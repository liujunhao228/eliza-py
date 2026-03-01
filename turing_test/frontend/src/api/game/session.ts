/**
 * 会话相关 API
 *
 * 负责：
 * - 获取会话信息
 * - 结束会话
 * - 获取会话结果
 * - 领取对方结算奖励
 */

import api from '../index'
import type { Session } from '@/types'
import type { GameResultResponse } from '@/types/result'

/**
 * 领取对方结算奖励响应
 */
export interface ClaimOpponentBonusResponse {
  bonus: number
  final_score: number
  message: string
}

/**
 * 获取会话信息
 */
export async function getSession(sessionId: number): Promise<Session> {
  return api.get(`/session/${sessionId}`)
}

/**
 * 结束会话
 */
export async function endSession(sessionId: number, endReason: string = 'user_gave_up'): Promise<any> {
  return api.post(`/session/${sessionId}/end`, { end_reason: endReason })
}

/**
 * 获取会话结果（问卷提交后的完整结果）
 */
export async function getSessionResult(sessionId: number): Promise<GameResultResponse> {
  return api.get(`/session/${sessionId}/result`)
}

/**
 * 领取对方结算奖励（两次结算机制）
 * 当对方结束对话后，用户可在提交问卷后轮询此接口获取对方结算的奖励
 */
export async function claimOpponentBonus(sessionId: number): Promise<ClaimOpponentBonusResponse> {
  return api.post(`/session/${sessionId}/claim-opponent-bonus`)
}
