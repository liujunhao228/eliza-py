// 问卷相关API
import api from './index'
import type { SurveyResponse } from '@/types'

/**
 * 问卷数据类型
 */
export interface SurveyData {
  user_guess: 'human' | 'ai' | 'unsure'
  confidence_level?: 'low' | 'mid' | 'high'  // 场中判断后无需填写
  fluency_rating: number
  reason?: string
  self_role: 'prover' | 'interferer' | 'other'
  strategy?: string
}

/**
 * 提交问卷
 */
export async function submitSurvey(
  sessionId: number,
  data: SurveyData
): Promise<SurveyResponse> {
  return api.post('/survey', {
    session_id: sessionId,
    user_guess: data.user_guess,
    confidence_level: data.confidence_level,
    fluency_rating: data.fluency_rating,
    reason: data.reason || '',
    self_role: data.self_role,
    strategy: data.strategy || ''
  })
}