/**
 * 匹配相关 API
 *
 * 简化版：
 * - startMatching: 加入匹配队列
 * - getMatchResult: 获取匹配结果（固定等待 3 秒后调用）
 */

import api from '../index'
import type { MatchResponse } from '@/types'

/**
 * 开始匹配（加入队列）
 */
export async function startMatching(userId: number): Promise<MatchResponse> {
  return api.post(`/match/join?user_id=${userId}`)
}

/**
 * 获取匹配结果
 * 前端在加入队列后固定等待 3 秒，然后调用此接口
 */
export async function getMatchResult(userId: number): Promise<MatchResponse> {
  return api.get(`/match/result?user_id=${userId}`)
}

/**
 * 离开匹配队列
 */
export async function leaveMatch(userId: number): Promise<void> {
  return api.post(`/match/leave?user_id=${userId}`)
}

/**
 * 获取匹配状态
 */
export async function getMatchStatus(userId: number): Promise<{
  in_queue: boolean
  queue_position: number | null
  estimated_wait_time: number | null
}> {
  return api.get(`/match/status?user_id=${userId}`)
}
