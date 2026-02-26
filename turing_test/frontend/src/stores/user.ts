import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserStats, LoginResponse } from '@/types'
import { STORAGE_KEYS } from '@/utils/constants'

export const useUserStore = defineStore('user', () => {
  // 状态
  // 注意：用户名字段统一使用 nickname，username 字段已废弃
  // 初始化时正确处理 localStorage 中的无效值（"0"、"null"、"undefined"、空字符串）
  const userIdFromStorage = localStorage.getItem(STORAGE_KEYS.USER_ID)
  const isValidUserId = userIdFromStorage &&
                        userIdFromStorage !== '0' &&
                        userIdFromStorage !== 'null' &&
                        userIdFromStorage !== 'undefined' &&
                        userIdFromStorage !== ''

  const userId = ref<number | null>(
    isValidUserId ? parseInt(userIdFromStorage, 10) || null : null
  )
  const nickname = ref<string>(localStorage.getItem(STORAGE_KEYS.NICKNAME) || '')
  const inviteCode = ref<string>(localStorage.getItem(STORAGE_KEYS.INVITE_CODE) || '')
  const score = ref<number>(parseInt(localStorage.getItem(STORAGE_KEYS.USER_SCORE) || '100', 10))
  const accessToken = ref<string>(localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || '')
  const stats = ref<UserStats | null>(null)
  const scoreHistory = ref<any[]>([])

  // 计算属性
  const isLoggedIn = computed(() => !!userId.value)
  
  /**
   * 当前用户信息
   * 注意：为兼容旧 API，同时返回 username 和 nickname 字段，两者值相同
   */
  const currentUser = computed<User | null>(() => {
    if (!userId.value) return null
    return {
      id: userId.value,
      username: nickname.value,  // 兼容旧 API 字段
      nickname: nickname.value,
      invite_code: inviteCode.value,
      score: score.value,
      created_at: ''
    }
  })

  // 方法
  /**
   * 设置用户信息（旧版 API，兼容用）
   * @param user 用户对象
   * 注意：优先使用 nickname 字段，兼容旧版 username 字段
   */
  function setUser(user: User) {
    userId.value = user.id
    // 优先使用 nickname，若不存在则使用 username 兼容旧 API
    nickname.value = user.nickname || user.username || ''
    inviteCode.value = user.invite_code
    score.value = user.score || 100

    // 持久化到 localStorage
    localStorage.setItem(STORAGE_KEYS.USER_ID, user.id.toString())
    localStorage.setItem(STORAGE_KEYS.NICKNAME, nickname.value)
    localStorage.setItem(STORAGE_KEYS.INVITE_CODE, user.invite_code)
    localStorage.setItem(STORAGE_KEYS.USER_SCORE, (user.score || 100).toString())
  }

  /**
   * 设置登录响应（包含 token）
   * @param response 登录响应
   */
  function setLoginResponse(response: LoginResponse) {
    userId.value = response.id
    nickname.value = response.nickname || response.username || ''
    inviteCode.value = response.invite_code
    score.value = response.score || 100
    accessToken.value = response.access_token

    // 持久化到 localStorage
    localStorage.setItem(STORAGE_KEYS.USER_ID, response.id.toString())
    localStorage.setItem(STORAGE_KEYS.NICKNAME, nickname.value)
    localStorage.setItem(STORAGE_KEYS.INVITE_CODE, response.invite_code)
    localStorage.setItem(STORAGE_KEYS.USER_SCORE, (response.score || 100).toString())
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.access_token)
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
    accessToken.value = ''
    stats.value = null
    scoreHistory.value = []

    // 清除 localStorage
    localStorage.removeItem(STORAGE_KEYS.USER_ID)
    localStorage.removeItem(STORAGE_KEYS.NICKNAME)
    localStorage.removeItem(STORAGE_KEYS.INVITE_CODE)
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID)
    localStorage.removeItem(STORAGE_KEYS.OPPONENT_TYPE)
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER_SCORE)
    localStorage.removeItem(STORAGE_KEYS.TRIGGERED_MID_GAME)
  }

  return {
    // 状态
    userId,
    nickname,
    inviteCode,
    score,
    accessToken,
    stats,
    scoreHistory,

    // 计算属性
    isLoggedIn,
    currentUser,

    // 方法
    setUser,
    setLoginResponse,
    updateScore,
    setStats,
    setScoreHistory,
    logout
  }
})
