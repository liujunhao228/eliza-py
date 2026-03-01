/**
 * 匹配状态管理 Store
 * 
 * 统一管理匹配过程中的所有状态，包括：
 * - 匹配状态（idle/matching/matched/failed）
 * - 匹配结果
 * - 等待时间计时
 * - 错误信息
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MatchResponse } from '@/types'

/** 匹配状态 */
export type MatchStatus = 'idle' | 'matching' | 'matched' | 'failed'

/** 匹配配置常量 */
export const MATCH_CONFIG = {
  /** 匹配超时时间（秒）- 比后端配置多 2 秒，确保后端有机会完成 Bot 降级 */
  TIMEOUT_SECONDS: 12,
} as const

export const useMatchStore = defineStore('match', () => {
  // =============================================================================
  // 状态
  // =============================================================================
  
  /** 当前匹配状态 */
  const status = ref<MatchStatus>('idle')
  
  /** 匹配结果 */
  const result = ref<MatchResponse | null>(null)
  
  /** 等待时间（秒） */
  const waitTime = ref(0)
  
  /** 错误信息 */
  const error = ref<string | null>(null)
  
  // =============================================================================
  // 计时器管理（内部使用）
  // =============================================================================
  
  let pollTimer: number | null = null
  let timeoutTimer: number | null = null
  
  /** 停止所有计时器 */
  function stopTimers() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (timeoutTimer) {
      clearTimeout(timeoutTimer)
      timeoutTimer = null
    }
  }
  
  // =============================================================================
  // 动作
  // =============================================================================
  
  /** 开始匹配 */
  function startMatching(onTimeout: () => void) {
    status.value = 'matching'
    waitTime.value = 0
    error.value = null
    result.value = null
    
    // 启动计时器
    stopTimers() // 先清理旧计时器
    
    // 倒计时计时器
    pollTimer = window.setInterval(() => {
      waitTime.value++
    }, 1000)
    
    // 超时保护计时器
    timeoutTimer = window.setTimeout(() => {
      setMatchTimeout(onTimeout)
    }, MATCH_CONFIG.TIMEOUT_SECONDS * 1000)
  }
  
  /** 设置匹配成功 */
  function setMatchSuccess(matchResult: MatchResponse) {
    status.value = 'matched'
    result.value = matchResult
    stopTimers()
  }
  
  /** 设置匹配失败 */
  function setMatchFailed(message: string) {
    status.value = 'failed'
    error.value = message
    stopTimers()
  }
  
  /** 设置匹配超时 */
  function setMatchTimeout(onTimeout?: () => void) {
    status.value = 'failed'
    error.value = '匹配超时，已返回大厅'
    stopTimers()
    // 执行超时回调
    onTimeout?.()
  }
  
  /** 重置状态 */
  function reset() {
    stopTimers()
    status.value = 'idle'
    result.value = null
    waitTime.value = 0
    error.value = null
  }
  
  /** 更新等待时间（外部调用） */
  function updateWaitTime(time: number) {
    waitTime.value = time
  }
  
  // =============================================================================
  // 导出
  // =============================================================================
  
  return {
    // 状态
    status,
    result,
    waitTime,
    error,
    
    // 方法
    startMatching,
    setMatchSuccess,
    setMatchFailed,
    setMatchTimeout,
    reset,
    updateWaitTime,
  }
})
