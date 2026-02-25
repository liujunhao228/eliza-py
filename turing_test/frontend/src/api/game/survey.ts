/**
 * 问卷相关 API
 *
 * 负责：
 * - 提交问卷
 */

import api from '../index'
import type { GameResultResponse } from '@/types/result'

/**
 * 提交问卷
 */
export async function submitSurvey(
  sessionId: number,
  data: {
    user_guess: 'human' | 'ai' | 'unsure'
    confidence_level: 'low' | 'mid' | 'high'
    fluency_rating: number
    reason?: string
    self_role: 'prover' | 'interferer' | 'other'
    strategy?: string
  }
): Promise<GameResultResponse> {
  return api.post('/survey', {
    session_id: sessionId,
    ...data
  })
}
