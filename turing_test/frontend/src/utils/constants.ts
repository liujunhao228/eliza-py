// 常量定义

// API配置
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws'

// 游戏常量
export const MIN_CHAT_TURNS = 3
export const MATCH_TIMEOUT = 30 // 秒
export const MAX_TURNS = 15
export const ENTRY_FEE = 2
export const TURN_PENALTY_RATE = 0.5
export const MIN_FREE_TURNS = 3

// 信心等级乘数
export const CONFIDENCE_MULTIPLIER = {
  low: 1.0,
  mid: 2.5,
  high: 5.0
} as const

// 元对话关键词
export const META_KEYWORDS = [
  '真人', '机器', 'AI', '机器人', '人工智能',
  '程序', '算法', '人类', '人', '电脑', '计算',
  '你是', '我是', '身份', '真假', '还是', '到底'
]

// 场中判断关键词
export const IDENTITY_KEYWORDS = [
  '机器人', 'AI', '程序', '机器', '人工智能', '代码', '算法'
]

// LocalStorage键名
export const STORAGE_KEYS = {
  USER_ID: 'userId',
  NICKNAME: 'nickname',
  INVITE_CODE: 'inviteCode',
  SESSION_ID: 'sessionId',
  OPPONENT_TYPE: 'opponentType',
  USER_SCORE: 'userScore'
} as const

// 页面路径
export const ROUTES = {
  LOGIN: '/',
  LOBBY: '/lobby',
  CHAT: '/chat',
  SURVEY: '/survey',
  RESULT: '/result',
  PROFILE: '/profile'
} as const

// 错误消息
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络错误，请稍后重试',
  INVALID_INVITE_CODE: '邀请码无效',
  SESSION_NOT_FOUND: '会话不存在',
  UNAUTHORIZED: '未授权，请重新登录',
  SERVER_ERROR: '服务器错误，请稍后重试'
} as const

// 成功消息
export const SUCCESS_MESSAGES = {
  MATCH_FOUND: '匹配成功！',
  SESSION_ENDED: '对话已结束',
  SURVEY_SUBMITTED: '问卷提交成功'
} as const