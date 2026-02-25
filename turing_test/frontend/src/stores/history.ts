import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as historyApi from '@/api/history'

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

export interface ShareInfo {
  share_id: number
  share_token: string
  share_url: string
  expires_at: string | null
  has_password: boolean
  is_expired: boolean
  view_count: number
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

export const useHistoryStore = defineStore('history', () => {
  // ==================== 状态 ====================

  const sessions = ref<Session[]>([])
  const currentSession = ref<SessionDetail | null>(null)
  const currentMessages = ref<SharedMessage[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  const pagination = ref({
    page: 1,
    page_size: 20,
    total: 0,
    has_more: false
  })

  const filters = ref({
    opponent_type: '' as string | undefined,
    is_correct: undefined as boolean | undefined
  })

  // 分享相关状态
  const currentShare = ref<SharePublicInfo | null>(null)
  const shareAccessToken = ref<string | null>(null)

  // ==================== 计算属性 ====================

  const hasMore = computed(() => pagination.value.has_more)
  const totalPages = computed(() => 
    Math.ceil(pagination.value.total / pagination.value.page_size)
  )

  // ==================== 方法 ====================

  /**
   * 获取用户会话列表
   */
  async function fetchSessions(userId: number, newFilters?: typeof filters.value) {
    loading.value = true
    error.value = null

    try {
      if (newFilters) {
        filters.value = newFilters
        pagination.value.page = 1
      }

      const response = await historyApi.getUserSessions(userId, {
        page: pagination.value.page,
        page_size: pagination.value.page_size,
        ...filters.value
      })

      sessions.value = response.items
      pagination.value = {
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        has_more: response.has_more
      }
    } catch (e: any) {
      error.value = e.message
      console.error('获取会话列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载更多会话
   */
  async function loadMoreSessions(userId: number) {
    if (!hasMore.value || loading.value) return
    pagination.value.page += 1
    await fetchSessions(userId)
  }

  /**
   * 获取会话详情
   */
  async function fetchSessionDetail(sessionId: number) {
    loading.value = true
    error.value = null

    try {
      currentSession.value = await historyApi.getSessionDetail(sessionId)
    } catch (e: any) {
      error.value = e.message
      console.error('获取会话详情失败:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取会话消息（通过 game API）
   */
  async function fetchSessionMessages(sessionId: number) {
    loading.value = true
    error.value = null

    try {
      // 使用 game API 获取消息
      const { getSessionMessages } = await import('@/api/game')
      const response = await getSessionMessages(sessionId)
      currentMessages.value = response.messages.map((msg: any) => ({
        id: msg.id,
        session_id: msg.session_id,
        sender: msg.sender,
        content: msg.content,
        is_meta_conversation: msg.is_meta_conversation,
        meta_keyword: msg.meta_keyword,
        created_at: msg.created_at
      }))
    } catch (e: any) {
      error.value = e.message
      console.error('获取会话消息失败:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建分享链接
   */
  async function createShare(
    sessionId: number,
    options: {
      is_public?: boolean
      expires_days?: number
      password?: string
    }
  ) {
    loading.value = true
    error.value = null

    try {
      const share = await historyApi.createShare(sessionId, options)
      // 创建分享后，获取完整的公开信息
      if (share.share_token) {
        currentShare.value = await historyApi.getShareInfo(share.share_token)
      }
      return share
    } catch (e: any) {
      error.value = e.message
      console.error('创建分享失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取分享信息（公开）
   */
  async function fetchShareInfo(shareToken: string) {
    loading.value = true
    error.value = null

    try {
      const info = await historyApi.getShareInfo(shareToken)
      currentShare.value = info
      return info
    } catch (e: any) {
      error.value = e.message
      console.error('获取分享信息失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 验证分享密码
   */
  async function verifySharePassword(shareToken: string, password: string) {
    loading.value = true
    error.value = null

    try {
      const response = await historyApi.verifySharePassword(shareToken, password)
      if (response.access_token) {
        shareAccessToken.value = response.access_token
      }
      return response
    } catch (e: any) {
      error.value = e.message
      console.error('密码验证失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取分享会话消息
   */
  async function fetchSharedMessages(shareToken: string) {
    loading.value = true
    error.value = null

    try {
      const response = await historyApi.getSharedMessages(
        shareToken,
        shareAccessToken.value || undefined
      )
      currentMessages.value = response.messages
      return response
    } catch (e: any) {
      error.value = e.message
      console.error('获取分享消息失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新分享设置
   */
  async function updateShare(
    shareId: number,
    options: {
      is_public?: boolean
      expires_days?: number
      password?: string
    }
  ) {
    loading.value = true
    error.value = null

    try {
      const updated = await historyApi.updateShare(shareId, options)
      // 更新分享后，获取最新的公开信息
      if (updated.share_token) {
        currentShare.value = await historyApi.getShareInfo(updated.share_token)
      }
      return updated
    } catch (e: any) {
      error.value = e.message
      console.error('更新分享失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除分享链接
   */
  async function deleteShare(shareId: number) {
    loading.value = true
    error.value = null

    try {
      await historyApi.deleteShare(shareId)
      currentShare.value = null
      shareAccessToken.value = null
    } catch (e: any) {
      error.value = e.message
      console.error('删除分享失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 清除当前会话
   */
  function clearCurrentSession() {
    currentSession.value = null
    currentMessages.value = []
    error.value = null
  }

  /**
   * 清除分享状态
   */
  function clearShareState() {
    currentShare.value = null
    shareAccessToken.value = null
    error.value = null
  }

  return {
    // 状态
    sessions,
    currentSession,
    currentMessages,
    loading,
    error,
    pagination,
    filters,
    currentShare,
    shareAccessToken,

    // 计算属性
    hasMore,
    totalPages,

    // 方法
    fetchSessions,
    loadMoreSessions,
    fetchSessionDetail,
    fetchSessionMessages,
    createShare,
    fetchShareInfo,
    verifySharePassword,
    fetchSharedMessages,
    updateShare,
    deleteShare,
    clearCurrentSession,
    clearShareState
  }
})
