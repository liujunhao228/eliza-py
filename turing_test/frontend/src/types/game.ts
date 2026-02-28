// 游戏相关类型

// 博弈状态类型
export interface GameState {
  turn: number
  metaConversationCount: number
  messages: MessageDisplay[]
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
  type: 'message' | 'chat' | 'typing' | 'stop_typing' | 'match_found' | 'match_timeout' | 'session_ended' | 'mid_game_available' | 'mid_game_submitted' | 'ping' | 'pong' | 'error' | 'connected' | 'status'
  data?: any
}

// WebSocket 配置选项
export interface WebSocketConfig {
  url: string
  reconnect?: boolean // 是否自动重连
  maxReconnectAttempts?: number // 最大重连次数
  reconnectInterval?: number // 基础重连间隔（毫秒）
  maxReconnectInterval?: number // 最大重连间隔（毫秒），用于限制指数退避的上限
  heartbeatInterval?: number // 心跳间隔（毫秒），0 表示由后端单向发起心跳
  connectionTimeout?: number // 连接超时时间（毫秒）
  onMessage?: (message: WSMessage) => void
  onError?: (error: Event) => void
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onStateChange?: (state: WSConnectionState) => void
  onReconnecting?: (event: ReconnectEvent) => void // 重连中回调
  onReconnectSuccess?: (event: ReconnectSuccessEvent) => void // 重连成功回调
  onReconnectFailed?: (event: ReconnectFailedEvent) => void // 重连失败回调
}

// 重连事件数据
export interface ReconnectEvent {
  attempt: number // 当前重连次数
  maxAttempts: number // 最大重连次数
  delay: number // 下次重连延迟（毫秒）
  willRetry: boolean // 是否将继续重试
}

// 重连成功事件数据
export interface ReconnectSuccessEvent {
  attempt: number // 重连成功时的尝试次数
  downtime: number // 断开连接的时长（毫秒）
}

// 重连失败事件数据
export interface ReconnectFailedEvent {
  totalAttempts: number // 总尝试次数
  lastError?: Event // 最后一次错误
}

// WebSocket 事件处理器类型
export type WSMessageHandler = (data: any) => void
export type WSErrorHandler = (error: Event) => void
export type WSStateChangeHandler = (state: WSConnectionState) => void
export type WSReconnectHandler = (event: ReconnectEvent) => void
export type WSReconnectSuccessHandler = (event: ReconnectSuccessEvent) => void
export type WSReconnectFailedHandler = (event: ReconnectFailedEvent) => void

// WebSocket 管理器接口
export interface IWebSocketManager {
  connect(): void
  disconnect(): void
  reconnect(): void
  send(type: string, data?: any): void
  on(messageType: string, handler: WSMessageHandler | ((state: WSConnectionState) => void)): void
  off(messageType: string, handler?: WSMessageHandler): void
  getState(): WSConnectionState
  isConnected(): boolean
  getReconnectAttempts(): number // 获取当前重连次数
  reset(): void // 重置连接状态
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

// 对手类型（包含 unknown 和 opponent 以支持匿名机制）
export type OpponentType = 'human' | 'ai' | 'honeypot' | 'unknown' | 'opponent'

// 结束原因
export type EndReason =
  | 'user_gave_up'        // 用户未判断主动放弃
  | 'user_normal_end'     // 用户完成判断后正常结束
  | 'user_keyword'        // 用户关键词触发（如 "end"）
  | 'bot_keyword'         // Bot 关键词触发（如 "end"）
  | 'bot_max_turns'       // 达到最大轮数
  | 'bot_medium_turns'    // 达到中等轮数
  | 'bot_defense'         // Bot 被识破/怀疑
  | 'bot_timeout'         // 用户敷衍/无实质内容
  | 'bot_farewell'        // 用户告别后 Bot 离开
  | 'bot_time_limit'      // 时间过晚/过早
  | 'sys_timeout'         // 系统超时
  | 'sys_error'           // 系统错误

// 流畅度评分（1-5）
export type FluencyRating = 1 | 2 | 3 | 4 | 5

// =============================================================================
// WebSocket 消息专用类型
// =============================================================================

// 匹配成功消息数据
export interface MatchFoundData {
  session_id: string
  opponent_type: OpponentType
  is_honeypot: boolean
  matched_at: string
}

// 匹配成功消息
export interface MatchFoundMessage {
  type: 'match_found'
  data: MatchFoundData
}

// 积分明细（简化版 - 不暴露计算细节）
export interface ScoreBreakdownDetail {
  final_score: number
  is_correct: boolean
  // 对方猜错奖励字段
  opponent_guess?: string
  opponent_confidence?: string
  opponent_is_correct?: boolean
  opponent_score_if_correct?: number
  bonus_from_opponent_wrong?: number
}

// 场中判断提交确认消息数据
export interface MidGameSubmittedData {
  session_id: string
  message: string
}

// 场中判断提交确认消息
export interface MidGameSubmittedMessage {
  type: 'mid_game_submitted'
  data: MidGameSubmittedData
}

// 场中可用消息数据
export interface MidGameAvailableData {
  session_id: string
  turn: number
  opponent_type: OpponentType
}

// 场中可用消息
export interface MidGameAvailableMessage {
  type: 'mid_game_available'
  data: MidGameAvailableData
}

// 匹配超时消息数据
export interface MatchTimeoutData {
  reason: string
}

// 匹配超时消息
export interface MatchTimeoutMessage {
  type: 'match_timeout'
  data: MatchTimeoutData
}

// 会话结束消息数据
export interface SessionEndedData {
  session_id: string
  final_score: number
  total_turns: number
  meta_conversations: number
}

// 会话结束消息
export interface SessionEndedMessage {
  type: 'session_ended'
  data: SessionEndedData
}

// 状态更新消息数据
export interface StatusData {
  in_queue: boolean
  queue_size?: number
  position?: number
  estimated_wait_time?: number
}

// 状态更新消息
export interface StatusMessage {
  type: 'status'
  data: StatusData
}

// 聊天消息数据
export interface ChatMessageData {
  sender: 'user' | 'opponent' | 'system'
  content: string
  timestamp: string
  is_meta_conversation?: boolean
  meta_keyword?: string
}

// 聊天消息
export interface ChatMessage {
  type: 'chat'
  data: ChatMessageData
}

// 打字状态消息数据
export interface TypingData {
  sender: 'opponent'
  is_typing: boolean
}

// 打字状态消息
export interface TypingMessage {
  type: 'typing' | 'stop_typing'
  data: TypingData
}

// 错误消息数据
export interface ErrorData {
  error_code: string
  message: string
}

// 错误消息
export interface ErrorMessage {
  type: 'error'
  data: ErrorData
}

// 所有 WebSocket 消息类型的联合类型
export type TypedWSMessage =
  | MatchFoundMessage
  | MatchTimeoutMessage
  | SessionEndedMessage
  | MidGameAvailableMessage
  | MidGameSubmittedMessage
  | ChatMessage
  | TypingMessage
  | StatusMessage
  | ErrorMessage
