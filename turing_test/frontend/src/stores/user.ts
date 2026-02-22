import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserStats } from '@/types'
import { STORAGE_KEYS } from '@/utils/constants'

export const useUserStore = defineStore('user', () => {
  // 状态
  const userId = ref<number | null>(parseInt(localStorage.getItem(STORAGE_KEYS.USER_ID) || '0') || null)
  const nickname = ref<string>(localStorage.getItem(STORAGE_KEYS.NICKNAME) || '')
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
      nickname: nickname.value,
      invite_code: inviteCode.value,
      score: score.value,
      created_at: ''
    }
  })

  // 方法
  function setUser(user: User) {
    userId.value = user.id
    nickname.value = user.nickname
    inviteCode.value = user.invite_code
    score.value = user.score || 100

    // 持久化到localStorage
    localStorage.setItem(STORAGE_KEYS.USER_ID, user.id.toString())
    localStorage.setItem(STORAGE_KEYS.NICKNAME, user.nickname)
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
    nickname.value = ''
    inviteCode.value = ''
    score.value = 100
    stats.value = null
    scoreHistory.value = []

    // 清除localStorage
    localStorage.removeItem(STORAGE_KEYS.USER_ID)
    localStorage.removeItem(STORAGE_KEYS.NICKNAME)
    localStorage.removeItem(STORAGE_KEYS.INVITE_CODE)
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID)
    localStorage.removeItem(STORAGE_KEYS.OPPONENT_TYPE)
  }

  return {
    // 状态
    userId,
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