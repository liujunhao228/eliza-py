// 游戏相关 API
import api from './index'
import type { Session, MatchResponse, MidGameJudgmentResponse, SurveyResponse } from '@/types'
import type {
  WSMessage,
  WebSocketConfig,
  WSConnectionState,
  WSMessageHandler,
  IWebSocketManager
} from '@/types'
import { WS_BASE_URL } from '@/utils/constants'

/**
 * 开始匹配
 */
export async function startMatching(userId: number): Promise<MatchResponse> {
  return api.post('/match', { user_id: userId })
}

/**
 * 直接匹配 AI
 */
export async function matchAI(userId: number): Promise<MatchResponse> {
  return api.post('/match/ai', { user_id: userId })
}

/**
 * 获取会话信息
 */
export async function getSession(sessionId: number): Promise<Session> {
  return api.get(`/session/${sessionId}`)
}

/**
 * 结束会话
 */
export async function endSession(sessionId: number): Promise<any> {
  return api.post(`/session/${sessionId}/end`)
}

/**
 * 场中判断（立即结束）
 */
export async function submitMidGameJudgment(
  sessionId: number,
  userGuess: 'human' | 'ai'
): Promise<MidGameJudgmentResponse> {
  return api.post(`/session/${sessionId}/end-game`, { user_guess: userGuess })
}

/**
 * 提交问卷
 */
export async function submitSurvey(
  sessionId: number,
  data: {
    user_guess: 'human' | 'ai' | 'unsure'
    confidence_level: 'low' | 'mid' | 'high'
    fluency_rating: number
    reason?: string
  }
): Promise<SurveyResponse> {
  return api.post('/survey', {
    session_id: sessionId,
    ...data
  })
}

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

// ==================== WebSocket 管理器 ====================

/**
 * WebSocket 管理器类
 * 提供完整的 WebSocket 连接管理、消息路由、心跳检测和自动重连功能
 */
class WebSocketManager implements IWebSocketManager {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private state: WSConnectionState = 'disconnected'
  private messageHandlers: Map<string, Set<WSMessageHandler>> = new Map()
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private reconnectAttempts: number = 0
  private manuallyClosed: boolean = false

  constructor(config: WebSocketConfig) {
    this.config = {
      url: config.url,
      reconnect: config.reconnect ?? true,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      reconnectInterval: config.reconnectInterval ?? 3000,
      heartbeatInterval: config.heartbeatInterval ?? 30000,
      onMessage: config.onMessage ?? (() => {}),
      onError: config.onError ?? (() => {}),
      onOpen: config.onOpen ?? (() => {}),
      onClose: config.onClose ?? (() => {}),
      onStateChange: config.onStateChange ?? (() => {})
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
    } catch (error) {
      console.error('[WebSocket] 连接失败:', error)
      this.handleError(error as Event)
    }
  }

  /**
   * 设置 WebSocket 事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = (event) => {
      console.log('[WebSocket] 连接已建立')
      this.reconnectAttempts = 0
      this.setState('connected')
      this.startHeartbeat()
      this.config.onOpen?.(event)
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
      this.stopHeartbeat()
      this.config.onClose?.(event)
      
      if (!this.manuallyClosed && this.config.reconnect) {
        this.attemptReconnect()
      }
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: WSMessage): void {
    // 处理 ping/pong 心跳响应
    if (data.type === 'pong') {
      console.log('[WebSocket] 收到 pong 响应')
      return
    }

    // 调用通用消息回调
    this.config.onMessage?.(data)

    // 调用特定类型消息的处理器
    const handlers = this.messageHandlers.get(data.type)
    if (handlers) {
      handlers.forEach(handler => handler(data.data))
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
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WebSocket] 达到最大重连次数，放弃重连')
      this.setState('disconnected')
      return
    }

    this.reconnectAttempts++
    this.setState('reconnecting')

    const delay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1) // 指数退避
    console.log(`[WebSocket] 将在 ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连`)

    this.reconnectTimer = window.setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * 开始心跳检测
   */
  private startHeartbeat(): void {
    this.stopHeartbeat() // 清除已有的心跳定时器

    this.heartbeatTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send('ping')
      }
    }, this.config.heartbeatInterval)
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.manuallyClosed = true
    this.stopHeartbeat()
    this.clearReconnectTimer()

    if (this.ws) {
      this.ws.close(1000, '用户主动断开')
      this.ws = null
    }

    this.setState('disconnected')
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
  const url = `${WS_BASE_URL}/match/${userId}`
  return new WebSocketManager({
    url,
    reconnect: true,
    maxReconnectAttempts: 3,
    reconnectInterval: 2000,
    heartbeatInterval: 25000
  })
}

/**
 * 创建聊天阶段的 WebSocket 管理器
 * @param sessionId 会话 ID
 */
export function createChatWebSocket(sessionId: number): WebSocketManager {
  const url = `${WS_BASE_URL}/chat/${sessionId}`
  return new WebSocketManager({
    url,
    reconnect: true,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
    heartbeatInterval: 30000
  })
}

export default WebSocketManager
