/**
 * 游戏相关 API 统一导出
 */

// 会话相关
export { getSession, endSession, getSessionResult } from './session'

// 消息相关
export { getSessionMessages } from './message'

// 匹配相关
export { startMatching, getMatchResult, leaveMatch } from './match'

// 问卷相关
export { submitSurvey } from './survey'

// 历史相关
export { getUserStats, getScoreHistory } from './history'

// WebSocket
export { WebSocketManager, createMatchWebSocket, createChatWebSocket } from './websocket'

// 类型导出
export type {
  WSMessage,
  WebSocketConfig,
  WSConnectionState,
  WSMessageHandler,
  IWebSocketManager,
  ReconnectEvent,
  ReconnectSuccessEvent,
  ReconnectFailedEvent
} from '@/types'
