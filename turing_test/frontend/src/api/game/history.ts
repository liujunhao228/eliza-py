/**
 * 历史记录 API
 *
 * 负责：
 * - 获取用户统计
 * - 获取积分历史
 */

import api from '../index'

/**
 * 获取用户统计
 */
export async function getUserStats(userId: number): Promise<any> {
  return api.get(`/stats/${userId}`)
}

/**
 * 获取积分历史
 */
export async function getScoreHistory(userId: number): Promise<any[]> {
  return api.get(`/user/${userId}/history`)
}
