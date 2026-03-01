/**
 * 匹配相关 API
 *
 * 前端行为说明：
 * - startMatching: 调用 POST /api/match/join 加入队列
 * - getMatchResult: 轮询 GET /api/match/result 获取结果
 * - leaveMatch: 超时或取消时调用 POST /api/match/leave 离开队列
 *
 * 后端行为说明：
 * - 接收 /join 后全权处理匹配逻辑（真人匹配 → 超时 Bot 降级）
 * - 结果存储在服务器，等待前端轮询
 */

import api from '../index'
import type { MatchResponse } from '@/types'

/**
 * 开始匹配（加入队列）
 *
 * 后端行为：
 * - 加入匹配队列
 * - 决定匹配类型（真人/Bot/钓鱼）
 * - 真人匹配超时 10 秒后自动 Bot 降级
 *
 * @returns 如果有结果直接返回，否则返回 waiting 状态
 */
export async function startMatching(userId: number): Promise<MatchResponse> {
  return api.post(`/match/join?user_id=${userId}`)
}

/**
 * 获取匹配结果
 *
 * 前端轮询使用，每 1 秒调用一次
 *
 * 后端行为：
 * - 返回已存储的匹配结果（如果有）
 * - 404 表示结果尚未生成（继续轮询）
 *
 * @returns 匹配结果，null 表示尚未生成
 */
export async function getMatchResult(userId: number): Promise<MatchResponse | null> {
  try {
    return await api.get(`/match/result?user_id=${userId}`)
  } catch (error: any) {
    // 404 表示结果还未生成
    if (error.code === 'NOT_FOUND' || error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * 离开匹配队列
 *
 * 前端在以下情况调用：
 * - 用户主动取消
 * - 前端超时（12 秒）
 *
 * 后端行为：
 * - 从队列中移除用户
 * - 清理相关状态
 */
export async function leaveMatch(userId: number): Promise<void> {
  return api.post(`/match/leave?user_id=${userId}`)
}
