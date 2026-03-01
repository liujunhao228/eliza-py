/**
 * 匹配相关 API
 *
 * 支持真人匹配和 AI 匹配：
 * - startHumanMatching: 加入真人匹配队列
 * - getHumanMatchStatus: 获取真人匹配状态
 * - leaveHumanMatch: 离开真人匹配队列
 *
 * 🛡️ 防重复请求：使用请求锁机制，防止短时间内重复调用
 */

import api from '../index'
import type { MatchResponse, MatchingStatusResponse } from '@/types'

// 请求锁，防止重复请求
let matchingLock: Promise<any> | null = null

// 队列中状态标记
let isInQueue: boolean = false

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
  isInQueue = false
  return api.post(`/match/human/leave?user_id=${userId}`)
}

/**
 * 开始匹配（加入队列）- 带防重复锁
 * 
 * 🛡️ 如果已有请求在进行中，直接返回该请求的结果
 * 
 * @returns 匹配结果，如果返回 { in_queue: true } 表示正在队列中等待
 */
export async function startMatching(userId: number): Promise<MatchResponse & { in_queue?: boolean }> {
  // 如果有正在进行的请求，直接返回该请求
  if (matchingLock) {
    return matchingLock
  }

  try {
    // 创建新请求锁
    matchingLock = (async () => {
      try {
        const result = await api.post(`/match/join?user_id=${userId}`)
        isInQueue = false
        return result
      } catch (error: any) {
        // 409 冲突表示用户已在队列中
        if (error.code === 'CONFLICT' || error.response?.status === 409) {
          isInQueue = true
          // 返回队列中状态，而不是抛出错误
          return {
            session_id: 0,
            opponent_type: 'waiting',
            match_duration_ms: 0,
            message: '正在队列中等待',
            in_queue: true,
          }
        }
        // 其他错误继续抛出
        throw error
      }
    })()
    
    return await matchingLock
  } finally {
    // 请求完成后释放锁（延迟一点，避免立即再次请求）
    setTimeout(() => {
      matchingLock = null
    }, 1000)
  }
}

/**
 * 检查是否在队列中
 */
export function isInMatchingQueue(): boolean {
  return isInQueue
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
  isInQueue = false
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
