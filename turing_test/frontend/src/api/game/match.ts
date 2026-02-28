/**
 * 匹配相关 API
 *
 * 支持真人匹配和 AI 匹配：
 * - startHumanMatching: 加入真人匹配队列
 * - getHumanMatchStatus: 获取真人匹配状态
 * - leaveHumanMatch: 离开真人匹配队列
 */

import api from '../index'
import type { MatchResponse, MatchingStatusResponse } from '@/types'

/**
 * 开始真人匹配（加入队列）
 */
export async function startHumanMatching(userId: number): Promise<MatchResponse> {
  return api.post(`/match/human/join?user_id=${userId}`)
}

/**
 * 获取真人匹配状态
 */
export async function getHumanMatchStatus(): Promise<MatchingStatusResponse> {
  return api.get('/match/human/status')
}

/**
 * 离开真人匹配队列
 */
export async function leaveHumanMatch(userId: number): Promise<void> {
  return api.post(`/match/human/leave?user_id=${userId}`)
}

/**
 * 开始匹配（加入队列）- 旧版，保留向后兼容
 */
export async function startMatching(userId: number): Promise<MatchResponse> {
  return api.post(`/match/join?user_id=${userId}`)
}

/**
 * 获取匹配结果 - 旧版，保留向后兼容
 */
export async function getMatchResult(userId: number): Promise<MatchResponse> {
  return api.get(`/match/result?user_id=${userId}`)
}

/**
 * 离开匹配队列 - 旧版，保留向后兼容
 */
export async function leaveMatch(userId: number): Promise<void> {
  return api.post(`/match/leave?user_id=${userId}`)
}

/**
 * 获取匹配状态 - 旧版，保留向后兼容
 */
export async function getMatchStatus(userId: number): Promise<{
  in_queue: boolean
  queue_position: number | null
  estimated_wait_time: number | null
}> {
  return api.get(`/match/status?user_id=${userId}`)
}
