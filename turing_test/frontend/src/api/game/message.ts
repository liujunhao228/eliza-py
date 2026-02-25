/**
 * 消息相关 API
 *
 * 负责：
 * - 获取会话历史消息
 */

import api from '../index'

/**
 * 获取会话历史消息
 */
export async function getSessionMessages(sessionId: number): Promise<{
  session_id: number
  opponent_type: string
  is_honeypot: boolean
  turn_count: number
  meta_conversation_count: number
  messages: Array<{
    id: number
    session_id: number
    sender: string
    content: string
    is_meta_conversation: boolean
    meta_keyword: string | null
    created_at: string
  }>
}> {
  return api.get(`/session/${sessionId}/messages`)
}
