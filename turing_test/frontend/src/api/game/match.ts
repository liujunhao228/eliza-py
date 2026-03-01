/**
 * 匹配相关 API
 *
 * 简化版接口：
 * - startMatching: 加入匹配队列
 * - getMatchResult: 获取匹配结果
 * - leaveMatch: 离开匹配队列
 *
 * 🛡️ 防重复请求：使用请求锁机制，防止短时间内重复调用
 */

import api from '../index'
import type { MatchResponse } from '@/types'

// 请求锁，防止重复请求
let matchingLock: Promise<any> | null = null

/**
 * 开始匹配（加入队列）
 *
 * 🛡️ 如果已有请求在进行中，直接返回该请求的结果
 */
export async function startMatching(userId: number): Promise<MatchResponse> {
  // 如果有正在进行的请求，直接返回该请求
  if (matchingLock) {
    return matchingLock
  }

  try {
    // 创建新请求锁
    matchingLock = api.post(`/match/join?user_id=${userId}`)
    return await matchingLock
  } catch (error: any) {
    // 409 冲突表示用户已在队列中
    if (error.code === 'CONFLICT' || error.response?.status === 409) {
      // 返回队列中状态
      return {
        session_id: 0,
        opponent_type: 'waiting',
        match_duration_ms: 0,
        message: '正在队列中等待',
      }
    }
    // 其他错误继续抛出
    throw error
  } finally {
    // 请求完成后释放锁（延迟一点，避免立即再次请求）
    setTimeout(() => {
      matchingLock = null
    }, 500)
  }
}

/**
 * 获取匹配结果
 *
 * @returns 匹配结果，如果返回 null 表示结果尚未生成
 */
export async function getMatchResult(userId: number): Promise<MatchResponse | null> {
  try {
    return await api.get(`/match/result?user_id=${userId}`)
  } catch (error: any) {
    // 404 表示结果尚未生成
    if (error.code === 'NOT_FOUND' || error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * 离开匹配队列
 */
export async function leaveMatch(userId: number): Promise<void> {
  return api.post(`/match/leave?user_id=${userId}`)
}
