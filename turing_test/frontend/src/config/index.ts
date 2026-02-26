/**
 * 项目集中配置
 * Turing Test Chat Platform 全局配置
 */

import {
  MIN_CHAT_TURNS,
  MATCH_TIMEOUT,
  MAX_TURNS,
  ENTRY_FEE,
  TURN_PENALTY_RATE,
  MIN_FREE_TURNS,
  MAX_MESSAGE_LENGTH,
  MIN_MESSAGE_LENGTH,
  MESSAGE_DEBOUNCE_DELAY,
  TEMP_MESSAGE_TTL,
  CONFIDENCE_MULTIPLIER,
  META_KEYWORDS,
  IDENTITY_KEYWORDS,
  SENSITIVE_WORDS
} from '@/utils/constants'

/**
 * 应用配置对象
 * 所有配置项集中管理，便于维护和测试
 */
export const AppConfig = Object.freeze({
  /**
   * 游戏配置
   */
  game: {
    /** 最少对话轮数（双方各发送 MIN_CHAT_TURNS 句） */
    minChatTurns: MIN_CHAT_TURNS,
    /** 匹配超时时间（秒） */
    matchTimeoutSeconds: MATCH_TIMEOUT,
    /** 最大对话轮数 */
    maxTurns: MAX_TURNS,
    /** 入场费（积分） */
    entryFee: ENTRY_FEE,
    /** 超时惩罚率（每少一轮扣除的积分比例） */
    turnPenaltyRate: TURN_PENALTY_RATE,
    /** 最少免费轮数 */
    minFreeTurns: MIN_FREE_TURNS
  },

  /**
   * 消息配置
   */
  message: {
    /** 单条消息最大字符数 */
    maxLength: MAX_MESSAGE_LENGTH,
    /** 单条消息最小字符数 */
    minLength: MIN_MESSAGE_LENGTH,
    /** 消息发送防抖延迟（毫秒） */
    debounceDelay: MESSAGE_DEBOUNCE_DELAY,
    /** 临时消息 ID 有效期（毫秒） */
    tempMessageTtl: TEMP_MESSAGE_TTL
  },

  /**
   * 元对话配置
   */
  metaConversation: {
    /** 元对话关键词列表 */
    keywords: META_KEYWORDS,
    /** 场中判断关键词列表 */
    identityKeywords: IDENTITY_KEYWORDS
  },

  /**
   * 敏感词配置
   */
  sensitiveWords: {
    /** 敏感词列表 */
    list: SENSITIVE_WORDS
  },

  /**
   * 信心等级乘数
   */
  confidence: CONFIDENCE_MULTIPLIER,

  /**
   * API 配置
   */
  api: {
    /** 请求超时（毫秒） */
    timeout: 10000,
    /** 最大重试次数 */
    maxRetries: 3,
    /** 基础重试延迟（毫秒） */
    retryDelay: 1000,
    /** 重试延迟抖动范围（毫秒） */
    retryJitter: 500
  },

  /**
   * WebSocket 配置
   */
  websocket: {
    /** 匹配阶段最大重连次数 */
    matchMaxReconnectAttempts: 3,
    /** 匹配阶段基础重连间隔（毫秒） */
    matchReconnectInterval: 2000,
    /** 匹配阶段最大重连间隔（毫秒） */
    matchMaxReconnectInterval: 15000,
    /** 聊天阶段最大重连次数 */
    chatMaxReconnectAttempts: 5,
    /** 聊天阶段基础重连间隔（毫秒） */
    chatReconnectInterval: 3000,
    /** 聊天阶段最大重连间隔（毫秒） */
    chatMaxReconnectInterval: 30000,
    /** 心跳间隔（毫秒） */
    heartbeatInterval: 30000
  },

  /**
   * 缓存配置
   */
  cache: {
    /** 历史消息缓存时间（毫秒） */
    historyMessagesTtl: 300000, // 5 分钟
    /** 用户信息缓存时间（毫秒） */
    userInfoTtl: 600000 // 10 分钟
  }
} as const)

/**
 * 配置类型推断
 */
export type AppConfig = typeof AppConfig

/**
 * 获取配置值（支持嵌套路径）
 * @param path 配置路径，如 'game.minChatTurns'
 * @returns 配置值
 *
 * @example
 * ```ts
 * getConfig('game.minChatTurns') // 3
 * getConfig('message.maxLength') // 500
 * ```
 */
export function getConfig<K extends keyof AppConfig>(path: K): AppConfig[K] {
  return AppConfig[path]
}

/**
 * 获取嵌套配置值
 * @param path 配置路径，如 'game.minChatTurns'
 * @returns 配置值
 *
 * @example
 * ```ts
 * getNestedConfig('game', 'minChatTurns') // 3
 * ```
 */
export function getNestedConfig<
  K extends keyof AppConfig,
  T extends keyof AppConfig[K]
>(section: K, key: T): AppConfig[K][T] {
  return AppConfig[section][key]
}

export default AppConfig
