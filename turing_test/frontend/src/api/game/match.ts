/**
 * 匹配相关 API
 *
 * 负责：
 * - 开始匹配
 * - AI 匹配
 */

import api from '../index'
import type { MatchResponse } from '@/types'

/**
 * 开始匹配
 * 注意：需要先建立 WebSocket 连接，然后通过 WebSocket 发送 join 消息
 */
export async function startMatching(userId: number): Promise<MatchResponse> {
  // 调用 HTTP API 加入匹配队列（使用 query 参数）
  return api.post(`/match/join?user_id=${userId}`)
}

/**
 * 直接匹配 AI
 */
export async function matchAI(userId: number): Promise<MatchResponse> {
  return api.post('/match/ai', { user_id: userId })
}
