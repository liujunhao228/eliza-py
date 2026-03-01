/**
 * 聊天状态管理 Composable
 *
 * 负责：
 * - 游戏状态管理
 * - WebSocket 连接管理
 * - 连接状态维护
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import { useChatWebSocket } from '@/composables/useWebSocket'
import type { MessageDisplay } from '@/types'

export function useChatState() {
  const router = useRouter()
  const gameStore = useGameStore()
  const userStore = useUserStore()
  const { error: showError, warning: showWarning, success: showSuccess, info: showInfo } = useToast()

  // 状态
  const isLoading = ref(false)
  const isInitialLoading = ref(false)
  const showMidGameModal = ref(false)
  const hasTriggeredMidGame = ref(false)  // 防止重复触发场中判断

  // 验证连接参数
  const canConnect = computed(() => {
    return !!gameStore.sessionId && !!userStore.userId
  })

  // 使用 WebSocket composable
  const {
    isConnected,
    state: connectionState,
    reconnect: wsReconnect,
    send,
    on
  } = useChatWebSocket(gameStore.sessionId || 0, userStore.userId || 0, {
    autoConnect: canConnect.value,
    onMessage: handleWSMessage,
    onError: (error) => {
      console.error('[WebSocket] 连接错误:', error)
      showError('WebSocket 连接失败，请检查后端服务')
    },
    onStateChange: (state) => {
      console.log('[WebSocket] 连接状态变化:', state)
      if (state === 'error') {
        showWarning('WebSocket 连接异常，正在尝试重连...')
      }
    }
  })

  // 注册 WebSocket 消息处理器
  function registerMessageHandlers(showEndSessionToast?: () => void) {
    console.log('[Chat] 注册 WebSocket 消息处理器')

    // 注册 chat 消息处理器
    on('chat', (data: any) => {
      console.log('[Chat] 收到 chat 消息:', data)
      handleChatMessage(data)
    })

    // 注册 typing 消息处理器
    on('typing', () => {
      console.log('[Chat] 收到 typing 消息')
      gameStore.setOpponentTyping(true)
    })

    // 注册 stop_typing 消息处理器
    on('stop_typing', () => {
      console.log('[Chat] 收到 stop_typing 消息')
      gameStore.setOpponentTyping(false)
    })

    // 注册 mid_game_available 消息处理器
    on('mid_game_available', () => {
      console.log('[Chat] 收到 mid_game_available 消息')
      // 只有在 store 中未触发且本地未触发过时才显示弹窗
      if (!gameStore.triggeredMidGame && !hasTriggeredMidGame.value) {
        hasTriggeredMidGame.value = true
        showMidGameModal.value = true
      }
    })

    // 注册 session_ended 消息处理器
    on('session_ended', () => {
      console.log('[Chat] 收到 session_ended 消息')
      // 显示倒计时提示
      if (showEndSessionToast) {
        showEndSessionToast()
      } else {
        // 兜底：直接跳转
        showInfo('会话已结束')
        router.push('/survey')
      }
    })

    // 注册 opponent_ended 消息处理器（对方结束对话通知）
    on('opponent_ended', (data: any) => {
      console.log('[Chat] 收到 opponent_ended 消息:', data)
      // 显示 Toast 提示
      showInfo('对方已结束对话，您可以继续停留 10 秒后填写问卷，或立即结束')
      // 显示倒计时提示
      if (showEndSessionToast) {
        showEndSessionToast()
      } else {
        // 兜底：10 秒后自动跳转
        setTimeout(() => {
          router.push('/survey')
        }, 10000)
      }
    })

    // 注册 session_timeout 消息处理器（会话超时通知）
    on('session_timeout', (data: any) => {
      console.log('[Chat] 收到 session_timeout 消息:', data)
      // 显示 Toast 提示
      showInfo('会话因超时自动结束，请提交问卷结算积分')
      // 自动跳转到 Survey 页面
      router.push('/survey')
    })

    // 注册 conversation_end 消息处理器（兜底机制）
    on('conversation_end', (data: any) => {
      console.log('[Chat] 收到 conversation_end 消息:', data)
      const reason = data.data?.reason || data.reason
      
      // 关键词触发的结束已在前端处理，这里只处理其他原因
      if (reason !== 'user_keyword' && reason !== 'bot_keyword') {
        showInfo('对话已结束')
        router.push('/survey')
      }
    })

    // 注册 mid_game_submitted 消息处理器（场中判断后隐藏结果）
    on('mid_game_submitted', (data: any) => {
      console.log('[Chat] 收到 mid_game_submitted 消息:', data)
      showSuccess('场中判断已记录，结果将在最终问卷提交时揭晓')

      // 仅标记已触发场中判断，不设置结果（隐藏 isCorrect）
      const userGuess = data.data?.user_guess || data.user_guess
      if (userGuess) {
        gameStore.setTriggeredMidGame(true)
        // 注意：不调用 setMidGameResult，避免泄露 isCorrect
      }
    })

    // 注册 connected 消息处理器
    on('connected', (data: any) => {
      console.log('[Chat] WebSocket 连接已确认:', data)

      // 同步服务器状态
      if (data.data) {
        gameStore.syncFromServer({
          turn_count: data.data.turn_count,
          is_user_turn: data.data.is_user_turn,
          meta_conversation_count: data.data.meta_conversation_count,
        })
      }

      if (isInitialLoading.value) {
        isInitialLoading.value = false
      }
    })

    // 注册 error 消息处理器
    on('error', (data: any) => {
      console.error('[Chat] WebSocket 错误:', data)
      showError(data?.message || '发生错误')
    })
  }

  // 处理 WebSocket 消息（通用回调）
  function handleWSMessage(data: any): void {
    console.log('[Chat] 收到 WebSocket 消息 (通用回调):', data.type, data.data)

    switch (data.type) {
      case 'chat':
      case 'message':
      case 'mid_game_available':
      case 'session_ended':
      case 'opponent_ended':  // 已有专用处理器，忽略
      case 'session_timeout':  // 已有专用处理器，忽略
      case 'mid_game_submitted':
      case 'connected':
      case 'error':
      case 'typing':
      case 'stop_typing':
      case 'conversation_end':  // 已有专用处理器，忽略
        // 这些消息类型已有专用处理器，忽略
        break

      default:
        // 处理其他未注册的消息类型
        console.log('[Chat] 收到未注册消息:', data.type, data.data)
    }
  }

  /**
   * 检测是否为结束关键词
   */
  function isEndKeyword(content: string): boolean {
    return content.trim().toLowerCase() === 'end'
  }

  // 处理聊天消息
  function handleChatMessage(data: any): void {
    console.log('[Chat] 处理聊天消息，sender:', data.sender, 'content:', data.content, 'id:', data.id)

    const message: MessageDisplay = {
      id: data.id || Date.now(),
      sender: data.sender === 'user' ? 'user' : 'opponent',
      content: data.content,
      timestamp: data.timestamp || new Date().toISOString(),
      isMetaConversation: data.isMetaConversation || false,
      metaKeyword: data.meta_keyword
    }

    // 检测 Bot 回复 "end" 关键词
    if (message.sender === 'opponent' && isEndKeyword(data.content)) {
      // 添加消息到列表（让用户看到 Bot 回复了 "end"）
      gameStore.addMessage(message)
      
      // 延迟一点再结束，让用户看到 Bot 的回复
      setTimeout(() => {
        showInfo('对方已结束对话')
        router.push('/survey')
      }, 500)
      return
    }

    // 检查是否是用户自己发送的消息（可能已有乐观更新）
    if (message.sender === 'user') {
      // 匹配逻辑：
      // 1. 发送者为 user
      // 2. 内容完全匹配
      // 3. 消息是临时 ID（时间戳格式，1 分钟内的消息视为待确认）
      const now = Date.now()
      const existingIndex = gameStore.messages.findIndex(m => {
        if (m.sender !== 'user') return false
        // 临时 ID 特征：大于 10^12 且小于当前时间 + 1 分钟
        const isTempId = m.id > 1e12 && m.id < now + 60000
        if (isTempId) {
          // 临时 ID 通过内容匹配
          return m.content === message.content
        }
        // 正式 ID 直接匹配
        return m.id === message.id
      })

      if (existingIndex !== -1) {
        // 更新已有消息（使用服务器返回的 ID 和时间戳）
        const existingMessage = gameStore.messages[existingIndex]
        if (existingMessage) {
          console.log('[Chat] 更新已有消息，索引:', existingIndex, '旧 ID:', existingMessage.id, '新 ID:', message.id)
          gameStore.messages[existingIndex] = {
            id: message.id,
            sender: existingMessage.sender,
            content: existingMessage.content,
            timestamp: message.timestamp,
            isMetaConversation: message.isMetaConversation,
            metaKeyword: message.metaKeyword ?? existingMessage.metaKeyword
          }
        }
      } else {
        // 没有乐观更新，添加新消息
        console.log('[Chat] 添加用户消息到 store:', message)
        gameStore.addMessage(message)
      }
    } else {
      // 对手消息，直接添加
      console.log('[Chat] 添加对手消息到 store:', message)
      gameStore.addMessage(message)
    }
  }

  // 重新连接函数
  function reconnect() {
    wsReconnect()
  }

  // 生命周期
  function onMountedSetup(showEndSessionToast?: () => void) {
    registerMessageHandlers(showEndSessionToast)
  }

  function onUnmountedSetup() {
    // 清理逻辑
  }

  return {
    // 状态
    isLoading,
    isInitialLoading,
    showMidGameModal,
    // 连接
    isConnected,
    connectionState,
    canConnect,
    // 方法
    reconnect,
    send,
    handleChatMessage,
    handleWSMessage,
    // 生命周期
    onMountedSetup,
    onUnmountedSetup
  }
}
