/**
 * 匹配逻辑 Composable
 *
 * 提供完整的匹配流程管理：
 * - WebSocket 连接与消息监听
 * - HTTP 轮询获取结果
 * - 超时处理
 * - 取消匹配
 */

import { computed, type ComputedRef, type Ref, ref } from 'vue'
import { useMatchStore } from '@/stores/match'
import type { MatchStatus } from '@/stores/match'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { startMatching, getMatchResult, leaveMatch } from '@/api/game/match'
import { useMatchWebSocket, type UseWebSocketReturn } from '@/composables/useWebSocket'
import type { MatchResponse } from '@/types'

interface UseMatchReturn {
  /** 匹配状态 */
  status: ComputedRef<MatchStatus>
  /** 匹配结果 */
  result: ComputedRef<MatchResponse | null>
  /** 等待时间 */
  waitTime: ComputedRef<number>
  /** 错误信息 */
  error: ComputedRef<string | null>
  /** WebSocket 是否已连接 */
  isConnected: Ref<boolean>
  /** 开始匹配 */
  start: () => Promise<void>
  /** 取消匹配 */
  cancel: () => Promise<void>
}

/**
 * 匹配逻辑 Composable
 *
 * @example
 * ```ts
 * // 在组件中使用
 * const { status, waitTime, start, cancel } = useMatch()
 * ```
 */
export function useMatch(): UseMatchReturn {
  const matchStore = useMatchStore()
  const userStore = useUserStore()
  const router = useRouter()

  // WebSocket 管理器（延迟初始化）
  const wsManager = ref<ReturnType<typeof useMatchWebSocket> | null>(null)
  const isConnected = ref(false)

  /**
   * 初始化 WebSocket
   */
  const initWebSocket = () => {
    if (!userStore.userId || wsManager.value) return

    wsManager.value = useMatchWebSocket(userStore.userId, { autoConnect: false })

    // 同步连接状态
    const unsubscribe = wsManager.value.state((state) => {
      isConnected.value = state === 'connected'
    })

    // 立即执行一次
    isConnected.value = wsManager.value.isConnected()
  }

  /**
   * 连接 WebSocket
   */
  const connectWebSocket = async () => {
    if (!wsManager.value) {
      initWebSocket()
    }
    await wsManager.value?.connect()
  }

  /**
   * 断开 WebSocket
   */
  const disconnectWebSocket = () => {
    wsManager.value?.disconnect()
  }

  /**
   * 注册 WebSocket 消息监听
   */
  const setupWSListeners = () => {
    if (!wsManager.value) return

    // 监听匹配成功
    wsManager.value.on('match_found', (data) => {
      matchStore.setMatchSuccess(data)
      stopPolling()
      onMatched()
    })

    // 监听匹配失败
    wsManager.value.on('match_failed', (data) => {
      matchStore.setMatchFailed(data?.reason || '匹配失败')
      stopPolling()
    })
  }
  
  // 轮询定时器
  let pollInterval: number | null = null
  
  /**
   * 启动轮询
   */
  const startPolling = () => {
    stopPolling() // 先清理旧轮询
    
    pollInterval = window.setInterval(async () => {
      if (matchStore.status !== 'matching') {
        stopPolling()
        return
      }
      
      try {
        const result = await getMatchResult(userStore.userId!)
        if (result && result.session_id > 0) {
          matchStore.setMatchSuccess(result)
          stopPolling()
          onMatched()
        }
      } catch {
        // 404 表示结果还未生成，继续轮询
      }
    }, 1000)
  }
  
  /**
   * 停止轮询
   */
  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }
  
  /**
   * 匹配成功回调
   */
  const onMatched = () => {
    disconnect() // 断开匹配 WebSocket
    router.push('/chat')
  }
  
  /**
   * 设置 WebSocket 消息监听
   */
  const setupWSListeners = () => {
    // 监听匹配成功
    on('match_found', (data) => {
      matchStore.setMatchSuccess(data)
      stopPolling()
      onMatched()
    })
    
    // 监听匹配失败
    on('match_failed', (data) => {
      matchStore.setMatchFailed(data?.reason || '匹配失败')
      stopPolling()
    })
  }
  
  /**
   * 开始匹配
   */
  const start = async () => {
    if (!userStore.userId) {
      matchStore.setMatchFailed('用户未登录')
      return
    }

    // 1. 设置匹配状态（并启动超时计时器）
    matchStore.startMatching(() => {
      // 超时回调：设置失败状态并返回大厅
      // 注意：后端在超时会进行 Bot 降级，所以不调用 leaveMatch
      // 用户返回大厅后可以重新开始匹配
      matchStore.setMatchFailed('匹配超时，请重试')
      router.push('/lobby')
    })

    try {
      // 2. 连接 WebSocket（用于实时推送）
      await connectWebSocket()
      setupWSListeners()

      // 3. 调用 HTTP API 加入队列
      const result = await startMatching(userStore.userId)

      // 4. 如果直接返回结果（AI 匹配），直接跳转
      if (result.session_id > 0 && result.opponent_type !== 'waiting') {
        matchStore.setMatchSuccess(result)
        onMatched()
        return
      }

      // 5. 否则开始轮询（等待真人匹配）
      startPolling()

    } catch (error: any) {
      matchStore.setMatchFailed(error.message || '匹配失败')
      disconnectWebSocket()
    }
  }

  /**
   * 取消匹配
   */
  const cancel = async () => {
    // 停止轮询和计时器
    stopPolling()

    // 断开 WebSocket
    disconnectWebSocket()

    // 调用 API 离开队列
    if (userStore.userId) {
      await leaveMatch(userStore.userId)
    }

    // 重置状态
    matchStore.reset()
  }

  return {
    // 状态
    status: computed(() => matchStore.status),
    result: computed(() => matchStore.result),
    waitTime: computed(() => matchStore.waitTime),
    error: computed(() => matchStore.error),
    isConnected,

    // 方法
    start,
    cancel
  }
}
