// WebSocket Composable
// 提供在 Vue 组件中使用 WebSocket 的便捷接口

import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { createMatchWebSocket, createChatWebSocket } from '@/api/game'
import type { 
  WSConnectionState, 
  WSMessageHandler, 
  IWebSocketManager,
  ReconnectEvent,
  ReconnectSuccessEvent,
  ReconnectFailedEvent
} from '@/types'

interface UseWebSocketOptions {
  autoConnect?: boolean // 是否自动连接
  reconnect?: boolean // 是否启用重连
  maxReconnectAttempts?: number // 最大重连次数
  reconnectInterval?: number // 基础重连间隔（毫秒）
  maxReconnectInterval?: number // 最大重连间隔（毫秒）
  connectionTimeout?: number // 连接超时时间（毫秒）
  onMessage?: (data: any) => void // 通用消息回调
  onError?: (error: Event) => void // 错误回调
  onStateChange?: (state: WSConnectionState) => void // 状态变更回调
  onReconnecting?: (event: ReconnectEvent) => void // 重连中回调
  onReconnectSuccess?: (event: ReconnectSuccessEvent) => void // 重连成功回调
  onReconnectFailed?: (event: ReconnectFailedEvent) => void // 重连失败回调
}

interface UseWebSocketReturn {
  ws: Ref<IWebSocketManager | null>
  state: Ref<WSConnectionState>
  isConnected: Ref<boolean>
  reconnectAttempts: Ref<number>
  connect: () => void
  disconnect: () => void
  reset: () => void
  send: (type: string, data?: any) => void
  on: (messageType: string, handler: WSMessageHandler) => void
  off: (messageType: string, handler?: WSMessageHandler) => void
}

/**
 * WebSocket Composable
 * 在 Vue 组件中提供完整的 WebSocket 生命周期管理
 *
 * @param createWs 创建 WebSocketManager 的工厂函数
 * @param options 配置选项
 *
 * @example
 * ```ts
 * // 在组件中使用
 * const { connect, disconnect, send, state, isConnected } = useWebSocket(
 *   () => createChatWebSocket(sessionId.value, userId.value)
 * )
 *
 * onMounted(() => connect())
 * onUnmounted(() => disconnect())
 * ```
 */
export function useWebSocket(
  createWs: () => IWebSocketManager,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    autoConnect = true,
    onMessage,
    onError,
    onStateChange,
    onReconnecting,
    onReconnectSuccess,
    onReconnectFailed
  } = options

  const ws = ref<IWebSocketManager | null>(null) as Ref<IWebSocketManager | null>
  const state = ref<WSConnectionState>('disconnected')
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)

  /**
   * 连接 WebSocket
   */
  function connect(): void {
    if (ws.value) {
      ws.value.connect()
      return
    }

    const manager = createWs()
    ws.value = manager

    // 注册状态变更回调
    const handleStateChange = (newState: WSConnectionState) => {
      state.value = newState
      isConnected.value = newState === 'connected'
      onStateChange?.(newState)
    }

    // 注册错误回调
    const handleError = (error: Event) => {
      onError?.(error)
    }

    // 注册重连相关回调
    const handleReconnecting = (event: ReconnectEvent) => {
      reconnectAttempts.value = event.attempt
      onReconnecting?.(event)
    }

    const handleReconnectSuccess = (event: ReconnectSuccessEvent) => {
      reconnectAttempts.value = 0
      onReconnectSuccess?.(event)
    }

    const handleReconnectFailed = (event: ReconnectFailedEvent) => {
      reconnectAttempts.value = event.totalAttempts
      onReconnectFailed?.(event)
    }

    // 使用内部方法监听状态变化
    manager.on('state_change', handleStateChange)
    manager.on('error', handleError)
    manager.on('reconnecting', handleReconnecting)
    manager.on('reconnectSuccess', handleReconnectSuccess)
    manager.on('reconnectFailed', handleReconnectFailed)

    // 注册通用消息回调
    if (onMessage) {
      manager.on('message', onMessage)
    }

    manager.connect()
  }

  /**
   * 断开连接
   */
  function disconnect(): void {
    if (ws.value) {
      ws.value.disconnect()
      ws.value = null
    }
    state.value = 'disconnected'
    isConnected.value = false
    reconnectAttempts.value = 0
  }

  /**
   * 重置连接状态
   */
  function reset(): void {
    if (ws.value) {
      ws.value.reset()
      ws.value = null
    }
    state.value = 'disconnected'
    isConnected.value = false
    reconnectAttempts.value = 0
  }

  /**
   * 发送消息
   */
  function send(type: string, data?: any): void {
    if (!ws.value) {
      console.warn('[useWebSocket] WebSocket 未初始化')
      return
    }
    ws.value.send(type, data)
  }

  /**
   * 注册消息处理器
   */
  function on(messageType: string, handler: WSMessageHandler): void {
    if (!ws.value) {
      console.warn('[useWebSocket] WebSocket 未初始化')
      return
    }
    ws.value.on(messageType, handler)
  }

  /**
   * 注销消息处理器
   */
  function off(messageType: string, handler?: WSMessageHandler): void {
    if (!ws.value) {
      console.warn('[useWebSocket] WebSocket 未初始化')
      return
    }
    ws.value.off(messageType, handler)
  }

  // 自动连接
  if (autoConnect) {
    onMounted(() => {
      connect()
    })
  }

  // 组件卸载时自动断开
  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    state,
    isConnected,
    reconnectAttempts,
    connect,
    disconnect,
    reset,
    send,
    on,
    off
  }
}

/**
 * 匹配阶段 WebSocket Composable
 *
 * @param userId 用户 ID
 * @param options 配置选项
 */
export function useMatchWebSocket(
  userId: number,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  return useWebSocket(() => createMatchWebSocket(userId), {
    ...options,
    // 匹配阶段的默认重连配置
    maxReconnectAttempts: options.maxReconnectAttempts ?? 3,
    reconnectInterval: options.reconnectInterval ?? 2000,
    maxReconnectInterval: options.maxReconnectInterval ?? 15000
  })
}

/**
 * 聊天阶段 WebSocket Composable
 *
 * @param sessionId 会话 ID
 * @param userId 用户 ID
 * @param options 配置选项
 */
export function useChatWebSocket(
  sessionId: number,
  userId: number,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  return useWebSocket(() => createChatWebSocket(sessionId, userId), {
    ...options,
    // 聊天阶段的默认重连配置
    maxReconnectAttempts: options.maxReconnectAttempts ?? 5,
    reconnectInterval: options.reconnectInterval ?? 3000,
    maxReconnectInterval: options.maxReconnectInterval ?? 30000
  })
}

export default useWebSocket
