import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserStats } from '@/types'
import { STORAGE_KEYS } from '@/utils/constants'

export const useUserStore = defineStore('user', () => {
  // 状态
  const userId = ref<number | null>(parseInt(localStorage.getItem(STORAGE_KEYS.USER_ID) || '0') || null)
  const username = ref<string>(localStorage.getItem(STORAGE_KEYS.NICKNAME) || '')
  const nickname = ref<string>(localStorage.getItem(STORAGE_KEYS.NICKNAME) || '')  // 兼容旧字段
  const inviteCode = ref<string>(localStorage.getItem(STORAGE_KEYS.INVITE_CODE) || '')
  const score = ref<number>(parseInt(localStorage.getItem(STORAGE_KEYS.USER_SCORE) || '100'))
  const stats = ref<UserStats | null>(null)
  const scoreHistory = ref<any[]>([])

  // 计算属性
  const isLoggedIn = computed(() => !!userId.value)
  const currentUser = computed<User | null>(() => {
    if (!userId.value) return null
    return {
      id: userId.value,
      username: username.value,
      nickname: nickname.value,
      invite_code: inviteCode.value,
      score: score.value,
      created_at: ''
    }
  })

  // 方法
  function setUser(user: User) {
    userId.value = user.id
    username.value = user.username || user.nickname || ''
    nickname.value = user.nickname || user.username || ''
    inviteCode.value = user.invite_code
    score.value = user.score || 100

    // 持久化到 localStorage
    localStorage.setItem(STORAGE_KEYS.USER_ID, user.id.toString())
    localStorage.setItem(STORAGE_KEYS.NICKNAME, nickname.value)
    localStorage.setItem(STORAGE_KEYS.INVITE_CODE, user.invite_code)
    localStorage.setItem(STORAGE_KEYS.USER_SCORE, (user.score || 100).toString())
  }

  function updateScore(newScore: number) {
    score.value = newScore
    localStorage.setItem(STORAGE_KEYS.USER_SCORE, newScore.toString())
  }

  function setStats(userStats: UserStats) {
    stats.value = userStats
  }

  function setScoreHistory(history: any[]) {
    scoreHistory.value = history
  }

  function logout() {
    userId.value = null
    username.value = ''
    nickname.value = ''
    inviteCode.value = ''
    score.value = 100
    stats.value = null
    scoreHistory.value = []

    // 清除 localStorage
    localStorage.removeItem(STORAGE_KEYS.USER_ID)
    localStorage.removeItem(STORAGE_KEYS.NICKNAME)
    localStorage.removeItem(STORAGE_KEYS.INVITE_CODE)
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID)
    localStorage.removeItem(STORAGE_KEYS.OPPONENT_TYPE)
  }

  return {
    // 状态
    userId,
    username,
    nickname,
    inviteCode,
    score,
    stats,
    scoreHistory,

    // 计算属性
    isLoggedIn,
    currentUser,

    // 方法
    setUser,
    updateScore,
    setStats,
    setScoreHistory,
    logout
  }
})
