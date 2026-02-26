/**
 * WebSocket 管理器
 *
 * 提供完整的 WebSocket 连接管理、消息路由、被动心跳（响应后端）和自动重连功能
 *
 * 心跳机制：由后端单向发起 ping，前端仅响应 pong
 *
 * 重连机制特性:
 * - 指数退避策略：重连间隔按 2 的幂次增长
 * - 最大间隔限制：防止等待时间过长
 * - 连接超时检测：避免无限等待
 * - 重连事件通知：支持回调和事件订阅
 * - 状态恢复：重连成功后自动恢复订阅状态
 */

import type {
  WSMessage,
  WebSocketConfig,
  WSConnectionState,
  WSMessageHandler,
  IWebSocketManager,
  ReconnectEvent,
  ReconnectSuccessEvent,
  ReconnectFailedEvent
} from '@/types'
import { WS_BASE_URL } from '@/utils/constants'

/**
 * WebSocket 管理器类
 */
class WebSocketManager implements IWebSocketManager {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private state: WSConnectionState = 'disconnected'
  private messageHandlers: Map<string, Set<WSMessageHandler>> = new Map()
  private reconnectTimer: number | null = null
  private connectionTimeoutTimer: number | null = null
  private reconnectAttempts: number = 0
  private manuallyClosed: boolean = false
  private disconnectStartTime: number = 0 // 记录断开连接的时间戳

  constructor(config: WebSocketConfig) {
    this.config = {
      url: config.url,
      reconnect: config.reconnect ?? true,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      reconnectInterval: config.reconnectInterval ?? 3000,
      maxReconnectInterval: config.maxReconnectInterval ?? 30000, // 最大 30 秒
      heartbeatInterval: config.heartbeatInterval ?? 30000,
      connectionTimeout: config.connectionTimeout ?? 10000, // 默认 10 秒超时
      onMessage: config.onMessage ?? (() => {}),
      onError: config.onError ?? (() => {}),
      onOpen: config.onOpen ?? (() => {}),
      onClose: config.onClose ?? (() => {}),
      onStateChange: config.onStateChange ?? (() => {}),
      onReconnecting: config.onReconnecting ?? (() => {}),
      onReconnectSuccess: config.onReconnectSuccess ?? (() => {}),
      onReconnectFailed: config.onReconnectFailed ?? (() => {})
    }
  }

  /**
   * 连接 WebSocket
   */
  connect(): void {
    if (this.state === 'connected' || this.state === 'connecting') {
      console.warn('[WebSocket] 已连接或正在连接中')
      return
    }

    this.manuallyClosed = false
    this.setState('connecting')

    try {
      this.ws = new WebSocket(this.config.url)
      this.setupEventHandlers()

      // 设置连接超时
      this.setupConnectionTimeout()
    } catch (error) {
      console.error('[WebSocket] 连接失败:', error)
      this.handleError(error as Event)
    }
  }

  /**
   * 设置连接超时检测
   */
  private setupConnectionTimeout(): void {
    this.clearConnectionTimeout()

    this.connectionTimeoutTimer = window.setTimeout(() => {
      if (this.state === 'connecting') {
        console.warn('[WebSocket] 连接超时')
        this.handleError(new Event('timeout') as any)
        if (this.ws) {
          this.ws.close()
        }
      }
    }, this.config.connectionTimeout)
  }

  /**
   * 清除连接超时定时器
   */
  private clearConnectionTimeout(): void {
    if (this.connectionTimeoutTimer) {
      clearTimeout(this.connectionTimeoutTimer)
      this.connectionTimeoutTimer = null
    }
  }

  /**
   * 设置 WebSocket 事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('[WebSocket] 连接已建立')
      this.clearConnectionTimeout() // 清除连接超时
      this.reconnectAttempts = 0
      this.setState('connected')

      // 如果是重连成功，触发重连成功回调
      if (this.disconnectStartTime > 0) {
        const downtime = Date.now() - this.disconnectStartTime
        this.disconnectStartTime = 0
        this.config.onReconnectSuccess({ attempt: this.reconnectAttempts + 1, downtime })
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      } catch (error) {
        console.error('[WebSocket] 消息解析失败:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WebSocket] 发生错误:', error)
      this.handleError(error)
    }

    this.ws.onclose = (event) => {
      console.log('[WebSocket] 连接已关闭:', event.code, event.reason)
      this.clearConnectionTimeout()
      this.disconnectStartTime = Date.now() // 记录断开时间
      this.config.onClose?.(event)

      if (!this.manuallyClosed && this.config.reconnect) {
        this.attemptReconnect()
      } else if (this.manuallyClosed) {
        this.disconnectStartTime = 0
      }
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: WSMessage): void {
    console.log('[WebSocket] 收到原始消息:', data)

    // 服务器发送 ping，响应 pong（被动心跳）
    if (data.type === 'ping') {
      console.log('[WebSocket] 收到 ping，响应 pong')
      this.send('pong', { timestamp: new Date().toISOString() })
      return
    }

    // 处理 error 消息
    if (data.type === 'error') {
      console.warn('[WebSocket] 收到错误:', data.data)
      const errorEvent = new Event('error') as any
      errorEvent.error_code = data.data?.error_code
      errorEvent.message = data.data?.message
      this.config.onError?.(errorEvent)
      const errorHandlers = this.messageHandlers.get('error')
      if (errorHandlers) {
        errorHandlers.forEach(handler => handler(data.data))
      }
      return
    }

    // 调用通用消息回调
    this.config.onMessage?.(data)

    // 调用特定类型消息的处理器
    const handlers = this.messageHandlers.get(data.type)
    if (handlers) {
      console.log('[WebSocket] 找到消息处理器，type:', data.type, 'handlers count:', handlers.size)
      handlers.forEach(handler => handler(data.data))
    } else {
      console.warn('[WebSocket] 未找到消息处理器，type:', data.type)
    }
  }

  /**
   * 处理错误
   */
  private handleError(error: Event): void {
    this.setState('error')
    this.config.onError?.(error)
  }

  /**
   * 尝试重新连接
   * 使用指数退避策略：delay = baseDelay * 2^(attempt-1)
   * 最大延迟不超过 maxReconnectInterval
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WebSocket] 达到最大重连次数，放弃重连')
      this.setState('disconnected')
      this.config.onReconnectFailed({
        totalAttempts: this.reconnectAttempts,
        lastError: undefined
      })
      this.disconnectStartTime = 0
      return
    }

    this.reconnectAttempts++
    this.setState('reconnecting')

    // 计算延迟时间：指数退避 + 最大限制
    const exponentialDelay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1)
    const delay = Math.min(exponentialDelay, this.config.maxReconnectInterval)

    const reconnectEvent: ReconnectEvent = {
      attempt: this.reconnectAttempts,
      maxAttempts: this.config.maxReconnectAttempts,
      delay,
      willRetry: this.reconnectAttempts < this.config.maxReconnectAttempts
    }

    console.log(`[WebSocket] 将在 ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连 (最大 ${this.config.maxReconnectInterval}ms)`)
    this.config.onReconnecting(reconnectEvent)

    this.reconnectTimer = window.setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.manuallyClosed = true
    this.clearReconnectTimer()
    this.clearConnectionTimeout()

    if (this.ws) {
      this.ws.close(1000, '用户主动断开')
      this.ws = null
    }

    this.setState('disconnected')
    this.disconnectStartTime = 0
  }

  /**
   * 重新连接
   */
  reconnect(): void {
    this.reconnectAttempts = 0
    this.connect()
  }

  /**
   * 重置连接状态（用于外部强制重置）
   */
  reset(): void {
    this.disconnect()
    this.reconnectAttempts = 0
    this.manuallyClosed = false
    this.setState('disconnected')
  }

  /**
   * 获取当前重连次数
   */
  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }

  /**
   * 清除重连定时器
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * 发送消息
   */
  send(type: string, data?: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] 连接未就绪，无法发送消息')
      return
    }

    const message: WSMessage = { type: type as WSMessage['type'], data }
    this.ws.send(JSON.stringify(message))
  }

  /**
   * 注册消息处理器
   */
  on(messageType: string, handler: WSMessageHandler): void {
    // 特殊处理 stateChange 事件
    if (messageType === 'stateChange') {
      this.config.onStateChange = handler as (state: WSConnectionState) => void
      // 立即触发一次当前状态
      handler(this.state as any)
      return
    }

    // 处理重连相关事件
    if (messageType === 'reconnecting') {
      this.config.onReconnecting = handler as (event: ReconnectEvent) => void
      return
    }

    if (messageType === 'reconnectSuccess') {
      this.config.onReconnectSuccess = handler as (event: ReconnectSuccessEvent) => void
      return
    }

    if (messageType === 'reconnectFailed') {
      this.config.onReconnectFailed = handler as (event: ReconnectFailedEvent) => void
      return
    }

    // 处理 error 事件
    if (messageType === 'error') {
      this.config.onError = handler as (error: Event) => void
      return
    }

    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, new Set())
    }
    this.messageHandlers.get(messageType)!.add(handler)
  }

  /**
   * 注销消息处理器
   */
  off(messageType: string, handler?: WSMessageHandler): void {
    const handlers = this.messageHandlers.get(messageType)
    if (!handlers) return

    if (handler) {
      handlers.delete(handler)
    } else {
      handlers.clear()
    }

    if (handlers.size === 0) {
      this.messageHandlers.delete(messageType)
    }
  }

  /**
   * 获取当前连接状态
   */
  getState(): WSConnectionState {
    return this.state
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.state === 'connected'
  }

  /**
   * 设置状态并通知回调
   */
  private setState(newState: WSConnectionState): void {
    this.state = newState
    console.log(`[WebSocket] 状态变更：${newState}`)
    this.config.onStateChange?.(newState)
  }
}

/**
 * 创建匹配阶段的 WebSocket 管理器
 * @param userId 用户 ID
 */
export function createMatchWebSocket(userId: number): WebSocketManager {
  const url = `${WS_BASE_URL}/match?user_id=${userId}`
  return new WebSocketManager({
    url,
    reconnect: true,
    maxReconnectAttempts: 3,
    reconnectInterval: 2000,
    maxReconnectInterval: 15000, // 最大 15 秒
    heartbeatInterval: 0, // 禁用心跳（由后端单向发起）
    connectionTimeout: 8000 // 8 秒超时
  })
}

/**
 * 创建聊天阶段的 WebSocket 管理器
 * @param sessionId 会话 ID
 * @param userId 用户 ID
 */
export function createChatWebSocket(sessionId: number, userId: number): WebSocketManager {
  const url = `${WS_BASE_URL}/chat?session_id=${sessionId}&user_id=${userId}`
  return new WebSocketManager({
    url,
    reconnect: true,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
    maxReconnectInterval: 30000, // 最大 30 秒
    heartbeatInterval: 0, // 禁用心跳（由后端单向发起）
    connectionTimeout: 10000 // 10 秒超时
  })
}

export { WebSocketManager }
export default WebSocketManager
