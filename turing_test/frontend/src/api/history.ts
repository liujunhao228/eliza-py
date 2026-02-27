// 历史会话与分享会话 API
import api from './index'

// ==================== 类型定义 ====================

export interface Session {
  id: number
  opponent_type: 'human' | 'ai'
  turn_count: number
  final_score: number | null
  is_correct: boolean | null
  confidence_level: 'low' | 'mid' | 'high' | null
  started_at: string
  ended_at: string | null
  has_share: boolean
}

export interface SessionDetail {
  id: number
  opponent_type: 'human' | 'ai'
  is_honeypot: boolean
  turn_count: number
  meta_conversation_count: number
  final_score: number | null
  is_correct: boolean | null
  confidence_level: 'low' | 'mid' | 'high' | null
  score_breakdown: Record<string, any> | null
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
}

export interface SessionListResponse {
  items: Session[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface ShareInfo {
  share_id: number
  share_token: string
  share_url: string
  expires_at: string | null
  has_password: boolean
  is_expired?: boolean
  view_count?: number
}

export interface SharePublicInfo {
  share_id: number
  share_token: string
  share_url: string
  session_id: number
  opponent_type: string
  turn_count: number
  final_score: number | null
  is_correct: boolean | null
  started_at: string
  ended_at: string | null
  view_count: number
  is_expired: boolean
  requires_password: boolean
  expires_at: string | null
  has_password: boolean
}

export interface SharedMessage {
  id: number
  session_id: number
  sender: string
  content: string
  is_meta_conversation: boolean
  meta_keyword: string | null
  created_at: string
}

export interface SharedMessagesResponse {
  session_id: number
  opponent_type: string
  messages: SharedMessage[]
}

// ==================== API 函数 ====================

/**
 * 获取用户会话列表
 */
export async function getUserSessions(
  userId: number,
  filters?: {
    page?: number
    page_size?: number
    opponent_type?: string
    is_correct?: boolean
    search?: string
  }
): Promise<SessionListResponse> {
  return api.get(`/user/${userId}/sessions`, { params: filters })
}

/**
 * 获取会话详情
 */
export async function getSessionDetail(sessionId: number): Promise<SessionDetail> {
  return api.get(`/session/${sessionId}/detail`)
}

/**
 * 创建分享链接
 */
export async function createShare(
  sessionId: number,
  options: {
    is_public?: boolean
    expires_days?: number
    password?: string
  }
): Promise<ShareInfo> {
  return api.post(`/session/${sessionId}/share`, options)
}

/**
 * 获取分享信息（公开）
 */
export async function getShareInfo(shareToken: string): Promise<SharePublicInfo> {
  return api.get(`/share/${shareToken}`)
}

/**
 * 验证分享密码
 */
export async function verifySharePassword(
  shareToken: string,
  password: string
): Promise<{ success: boolean; message: string; access_token?: string }> {
  return api.post(`/share/${shareToken}/verify-password`, { password })
}

/**
 * 获取分享会话消息（公开）
 */
export async function getSharedMessages(
  shareToken: string,
  accessToken?: string
): Promise<SharedMessagesResponse> {
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
  return api.get(`/share/${shareToken}/messages`, { headers })
}

/**
 * 更新分享设置
 */
export async function updateShare(
  shareId: number,
  options: {
    is_public?: boolean
    expires_days?: number
    password?: string
  }
): Promise<ShareInfo> {
  return api.put(`/share/${shareId}`, options)
}

/**
 * 删除分享链接
 */
export async function deleteShare(shareId: number): Promise<{ success: boolean; message: string }> {
  return api.delete(`/share/${shareId}`)
}

/**
 * 获取会话的分享列表
 * @param sessionId - 会话 ID
 * @param options - 可选配置
 * @param options.silent - 静默模式，不自动弹出错误提示（用于可选认证场景）
 */
export async function getSessionShares(
  sessionId: number,
  options?: { silent?: boolean }
): Promise<ShareInfo[]> {
  return api.get(`/session/${sessionId}/shares`, {
    skipRetry: options?.silent,  // 静默模式下跳过重试
    silent: options?.silent      // 传递静默标志给响应拦截器
  })
}
