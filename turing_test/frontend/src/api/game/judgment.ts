/**
 * 判断相关 API
 *
 * 负责：
 * - 场中判断（立即结束）
 * - 场中判断（不结束对话）
 */

import api from '../index'
import type { MidGameJudgmentResponse } from '@/types'

/**
 * 场中判断（立即结束）
 */
export async function submitMidGameJudgment(
  sessionId: number,
  userGuess: 'human' | 'ai'
): Promise<MidGameJudgmentResponse> {
  return api.post(`/session/${sessionId}/end-game`, { user_guess: userGuess })
}

/**
 * 场中判断（不结束对话）
 * @param sessionId 会话 ID
 * @param userGuess 用户猜测
 */
export async function makeMidGameJudgment(
  sessionId: number,
  userGuess: 'human' | 'ai'
): Promise<{ is_correct: boolean; score_change: number }> {
  return api.post(`/game/${sessionId}/mid-game`, { guess: userGuess })
}
