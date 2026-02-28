/**
 * Profile 数据加载 Composable
 * 负责用户数据的获取、错误处理和状态管理
 */

import { ref } from 'vue'
import { getUserFullProfile } from '@/api/profile'
import type { UserStats, Session, ScoreHistory } from '@/types'

interface ProfileData {
  stats: UserStats
  history: Session[]
  scoreHistory: ScoreHistory[]
}

export function useProfileData() {
  const loading = ref(false)
  const error = ref<string>()
  const stats = ref<UserStats | null>(null)
  const history = ref<Session[]>([])
  const scoreHistory = ref<ScoreHistory[]>([])

  /**
   * 加载用户数据
   */
  const load = async (userId: string) => {
    loading.value = true
    error.value = undefined

    try {
      const data: ProfileData = await getUserFullProfile(Number(userId))
      stats.value = data.stats
      history.value = data.history
      scoreHistory.value = data.scoreHistory
      return data
    } catch (err: any) {
      // 404 错误：用户不存在
      if (err.response?.status === 404) {
        error.value = '用户不存在，请重新登录'
      } else {
        const message = err.response?.data?.detail || err.message || '加载失败，请重试'
        error.value = message
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 清空错误状态
   */
  const clearError = () => {
    error.value = undefined
  }

  return {
    loading,
    error,
    stats,
    history,
    scoreHistory,
    load,
    clearError
  }
}
