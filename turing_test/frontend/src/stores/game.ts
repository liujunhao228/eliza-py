import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GameState, MessageDisplay, Session } from '@/types'
import { MIN_CHAT_TURNS } from '@/utils/constants'
import { STORAGE_KEYS } from '@/utils/constants'

export const useGameStore = defineStore('game', () => {
  // 状态
  const sessionId = ref<number | null>(parseInt(localStorage.getItem(STORAGE_KEYS.SESSION_ID) || '0') || null)
  const opponentType = ref<'human' | 'ai' | 'honeypot' | 'unknown' | null>(null)
  const turn = ref<number>(0)
  const metaConversationCount = ref<number>(0)
  const messages = ref<MessageDisplay[]>([])
  const triggeredMidGame = ref<boolean>(false)
  const isHoneypot = ref<boolean>(false)
  const sessionStartedAt = ref<Date | null>(null)
  
  // 轮流发送状态
  const isUserTurn = ref<boolean>(true)
  
  // 正在输入状态
  const isOpponentTyping = ref<boolean>(false)

  // 计算属性
  const canEndChat = computed(() => {
    // 双方各 MIN_CHAT_TURNS 句才算完成一轮
    return turn.value >= MIN_CHAT_TURNS * 2
  })

  const gameState = computed<GameState>(() => ({
    turn: turn.value,
    metaConversationCount: metaConversationCount.value,
    messages: messages.value,
    triggeredMidGame: triggeredMidGame.value,
    canEndChat: canEndChat.value
  }))

  // 方法
  function setSession(session: Session) {
    sessionId.value = session.id
    opponentType.value = session.opponent_type
    isHoneypot.value = session.is_honeypot || false
    triggeredMidGame.value = session.triggered_mid_game || false
    metaConversationCount.value = session.meta_conversation_count || 0
    
    // 使用服务器返回的状态（如果有）
    const serverTurnCount = (session as any).turn_count ?? 0
    const serverIsUserTurn = (session as any).is_user_turn ?? true
    
    turn.value = serverTurnCount
    isUserTurn.value = serverIsUserTurn
    isOpponentTyping.value = false

    if (session.started_at) {
      sessionStartedAt.value = new Date(session.started_at)
    }

    localStorage.setItem(STORAGE_KEYS.SESSION_ID, session.id.toString())
    localStorage.setItem(STORAGE_KEYS.OPPONENT_TYPE, session.opponent_type)
  }

  /**
   * 同步服务器状态
   * 用于 WebSocket connected 消息后同步状态
   */
  function syncFromServer(data: {
    turn_count?: number
    is_user_turn?: boolean
    meta_conversation_count?: number
  }) {
    if (data.turn_count !== undefined) {
      turn.value = data.turn_count
    }
    if (data.is_user_turn !== undefined) {
      isUserTurn.value = data.is_user_turn
    }
    if (data.meta_conversation_count !== undefined) {
      metaConversationCount.value = data.meta_conversation_count
    }
  }

  function addMessage(message: MessageDisplay) {
    messages.value.push(message)

    // 更新轮数（仅用户或对手发送的消息计入，system 消息不计入）
    if (message.sender === 'user' || message.sender === 'opponent') {
      turn.value++
      
      // 切换回合
      if (message.sender === 'user') {
        isUserTurn.value = false // 用户发送后，轮到对手
      } else {
        isUserTurn.value = true // 对手发送后，轮到用户
        isOpponentTyping.value = false // 对手发送消息后，停止"正在输入"状态
      }
    }

    // 检查元对话
    if (message.isMetaConversation) {
      incrementMetaCount(message.metaKeyword || '未知')
    }
  }

  function setInitialMessages(msgs: MessageDisplay[]) {
    // 先清空现有消息和状态，确保数据一致性
    messages.value = []
    turn.value = 0
    metaConversationCount.value = 0
    isUserTurn.value = true // 默认用户回合
    isOpponentTyping.value = false

    // 逐条添加消息，确保正确计算轮数和元对话次数
    msgs.forEach(message => {
      messages.value.push(message)
      // 仅用户或对手发送的消息计入轮数
      if (message.sender === 'user' || message.sender === 'opponent') {
        turn.value++
      }
      // 检查元对话
      if (message.isMetaConversation) {
        metaConversationCount.value++
      }
    })
    
    // 根据最后一条消息判断当前回合
    if (msgs.length > 0) {
      const lastMessage = msgs[msgs.length - 1]
      if (lastMessage) {
        isUserTurn.value = lastMessage.sender !== 'user'
      }
    }
  }

  function incrementMetaCount(_keyword?: string) {
    metaConversationCount.value++

    // 检查是否触发场中判断
    if (!triggeredMidGame.value && metaConversationCount.value > 0) {
      // 可以在这里触发场中判断提示
    }
  }

  function setTriggeredMidGame(value: boolean) {
    triggeredMidGame.value = value
  }
  
  function setUserTurn(turn: boolean) {
    isUserTurn.value = turn
  }
  
  function setOpponentTyping(typing: boolean) {
    isOpponentTyping.value = typing
  }

  function reset() {
    sessionId.value = null
    opponentType.value = null
    turn.value = 0
    metaConversationCount.value = 0
    messages.value = []
    triggeredMidGame.value = false
    isHoneypot.value = false
    sessionStartedAt.value = null
    isUserTurn.value = true
    isOpponentTyping.value = false

    localStorage.removeItem(STORAGE_KEYS.SESSION_ID)
    localStorage.removeItem(STORAGE_KEYS.OPPONENT_TYPE)
  }

  return {
    // 状态
    sessionId,
    opponentType,
    turn,
    metaConversationCount,
    messages,
    triggeredMidGame,
    isHoneypot,
    sessionStartedAt,
    isUserTurn,
    isOpponentTyping,

    // 计算属性
    canEndChat,
    gameState,

    // 方法
    setSession,
    addMessage,
    setInitialMessages,
    incrementMetaCount,
    setTriggeredMidGame,
    setUserTurn,
    setOpponentTyping,
    syncFromServer,
    reset
  }
})
