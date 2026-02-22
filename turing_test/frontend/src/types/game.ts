// 游戏相关类型

// 积分预测类型
export interface ScorePrediction {
  lowConfidence: {
    correct: number
    wrong: number
  }
  midConfidence: {
    correct: number
    wrong: number
  }
  highConfidence: {
    correct: number
    wrong: number
  }
  metaMultiplier: number
  penaltyMultiplier: number
  turnPenalty: number
  entryFee: number
}

// 博弈状态类型
export interface GameState {
  turn: number
  metaConversationCount: number
  messages: MessageDisplay[]
  currentScorePrediction: ScorePrediction
  triggeredMidGame: boolean
  canEndChat: boolean
}

// 消息显示类型
export interface MessageDisplay {
  id: number
  sender: 'user' | 'opponent' | 'system'
  content: string
  timestamp: string
  isMetaConversation: boolean
  metaKeyword?: string
}

// WebSocket 连接状态
export type WSConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'

// WebSocket 消息类型
export interface WSMessage {
  type: 'message' | 'typing' | 'stop_typing' | 'match_found' | 'match_timeout' | 'session_ended' | 'mid_game_available' | 'ping' | 'pong' | 'error'
  data?: any
}

// WebSocket 配置选项
export interface WebSocketConfig {
  url: string
  reconnect?: boolean // 是否自动重连
  maxReconnectAttempts?: number // 最大重连次数
  reconnectInterval?: number // 重连间隔（毫秒）
  heartbeatInterval?: number // 心跳间隔（毫秒）
  onMessage?: (message: WSMessage) => void
  onError?: (error: Event) => void
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onStateChange?: (state: WSConnectionState) => void
}

// WebSocket 事件处理器类型
export type WSMessageHandler = (data: any) => void
export type WSErrorHandler = (error: Event) => void
export type WSStateChangeHandler = (state: WSConnectionState) => void

// WebSocket 管理器接口
export interface IWebSocketManager {
  connect(): void
  disconnect(): void
  send(type: string, data?: any): void
  on(messageType: string, handler: WSMessageHandler): void
  off(messageType: string, handler?: WSMessageHandler): void
  getState(): WSConnectionState
  isConnected(): boolean
}

// 元对话触发记录
export interface MetaTrigger {
  turn: number
  speaker: 'user' | 'opponent'
  keyword: string
  timestamp: string
}

// 场中判断选项
export type MidGameChoice = 'human' | 'ai'

// 信心等级选项
export type ConfidenceLevel = 'low' | 'mid' | 'high'

// 用户猜测类型
export type UserGuess = 'human' | 'ai' | 'unsure'

// 对手类型
export type OpponentType = 'human' | 'ai' | 'honeypot'

// 流畅度评分（1-5）
export type FluencyRating = 1 | 2 | 3 | 4 | 5

// 乘数信息
export interface MultiplierInfo {
  metaMultiplier: number
  penaltyMultiplier: number
  metaCount: number
}
