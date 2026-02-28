// API响应基础类型
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  detail?: string
}

// 用户相关类型
export interface User {
  id: number
  username: string
  nickname?: string  // 兼容旧字段
  invite_code: string
  created_at: string
  score?: number
  total_score_earned?: number
  total_score_lost?: number
  highest_score?: number
  lowest_score?: number
  risk_preference?: string
  last_login_at?: string
}

// 登录响应类型
export interface LoginResponse {
  id: number
  username: string
  nickname: string
  score: number
  invite_code: string
  access_token: string
  token_type: string
}

// 会话相关类型
export interface Session {
  id: number
  user_id: number
  opponent_type: 'human' | 'ai' | 'honeypot' | 'unknown'
  opponent_id?: number
  status: 'matching' | 'active' | 'completed'
  is_honeypot?: boolean
  triggered_mid_game?: boolean
  meta_conversation_count?: number
  match_duration?: number
  started_at?: string
  ended_at?: string
  created_at: string
  turn_count?: number
  final_score?: number | null
  is_correct?: boolean | null
  confidence_level?: 'low' | 'mid' | 'high' | null
  has_share?: boolean
}

// 消息相关类型
export interface Message {
  id: number
  session_id: number
  sender_id?: number
  is_ai: boolean
  is_meta_conversation?: boolean
  meta_keyword?: string
  content: string
  created_at: string
}

// 问卷相关类型
export interface SurveyData {
  user_guess: 'human' | 'ai' | 'unsure'
  confidence_level?: 'low' | 'mid' | 'high'  // 场中判断后无需填写
  fluency_rating: number
  reason?: string
  self_role: 'prover' | 'interferer' | 'other'
  strategy?: string
}

// 积分明细类型
export interface ScoreBreakdown {
  base_reward?: number
  confidence_multiplier?: number
  meta_multiplier?: number
  penalty_multiplier?: number
  effective_multiplier?: number
  entry_fee?: number
  turn_penalty?: number
  final_score: number
  is_correct: boolean
  // 对方猜错奖励字段
  opponent_guess?: string
  opponent_confidence?: string
  opponent_is_correct?: boolean
  opponent_score_if_correct?: number
  bonus_from_opponent_wrong?: number
}

// 场中判断响应类型
export interface MidGameJudgmentResponse {
  is_correct: boolean
  opponent_type: 'human' | 'ai' | 'honeypot' | 'unknown'
  final_score: number
  score_breakdown: ScoreBreakdown
}

// 问卷提交响应类型
export interface SurveyResponse {
  is_correct: boolean
  opponent_type: 'human' | 'ai' | 'honeypot' | 'unknown'
  final_score: number
  score_breakdown: ScoreBreakdown
}

// 用户统计类型
export interface UserStats {
  total_sessions: number
  ai_sessions: number
  human_sessions: number
  honeypot_sessions: number
  total_guesses: number
  correct_guesses: number
  accuracy: number
  low_confidence_count: number
  mid_confidence_count: number
  high_confidence_count: number
  total_meta_conversations: number
  avg_meta_per_session: number
  max_meta_in_one_session: number
  accuracy_with_meta?: number
  accuracy_without_meta?: number
  mid_game_judgments: number
  mid_game_accuracy: number
  avg_turns: number
  min_turns?: number
  max_turns?: number
  total_chat_time: number
  avg_session_duration: number
}

// 匹配状态类型
export interface MatchStatus {
  waiting_count: number
  active_sessions: number
}

// 积分历史记录类型
export interface ScoreHistory {
  id: number
  user_id: number
  session_id?: number
  score_change: number
  score_before: number
  score_after: number
  reason: string
  created_at: string
  // 对方猜错奖励字段
  bonus_from_opponent?: number
  opponent_guess?: string
  opponent_confidence?: string
  opponent_is_correct?: boolean
}

// 匹配响应类型
export interface MatchResponse {
  status?: 'found' | 'waiting' | 'timeout'
  session_id?: number
  opponent_type?: 'human' | 'ai' | 'unknown' | 'waiting'
  is_honeypot?: boolean
  message?: string
}

// 匹配状态类型
export interface MatchingStatusResponse {
  in_queue?: boolean
  queue_position?: number | null
  estimated_wait_time?: number | null
  waiting_count?: number
}