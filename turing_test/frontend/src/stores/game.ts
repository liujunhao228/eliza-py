import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GameState, MessageDisplay, ScorePrediction, Session } from '@/types'
import { calculateScorePrediction } from '@/utils/scoreCalculator'
import { MIN_CHAT_TURNS } from '@/utils/constants'
import { STORAGE_KEYS } from '@/utils/constants'

export const useGameStore = defineStore('game', () => {
  // 状态
  const sessionId = ref<number | null>(parseInt(localStorage.getItem(STORAGE_KEYS.SESSION_ID) || '0') || null)
  const opponentType = ref<'human' | 'ai' | 'honeypot' | null>(null)
  const turn = ref<number>(0)
  const metaConversationCount = ref<number>(0)
  const messages = ref<MessageDisplay[]>([])
  const currentScorePrediction = ref<ScorePrediction | null>(null)
  const triggeredMidGame = ref<boolean>(false)
  const isHoneypot = ref<boolean>(false)
  const sessionStartedAt = ref<Date | null>(null)

  // 计算属性
  const canEndChat = computed(() => {
    // 双方各MIN_CHAT_TURNS句才算完成一轮
    return turn.value >= MIN_CHAT_TURNS * 2
  })

  const gameState = computed<GameState>(() => ({
    turn: turn.value,
    metaConversationCount: metaConversationCount.value,
    messages: messages.value,
    currentScorePrediction: currentScorePrediction.value || {
      lowConfidence: { correct: 0, wrong: 0 },
      midConfidence: { correct: 0, wrong: 0 },
      highConfidence: { correct: 0, wrong: 0 },
      metaMultiplier: 1.0,
      penaltyMultiplier: 1.0,
      turnPenalty: 0,
      entryFee: 2
    },
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
    
    if (session.started_at) {
      sessionStartedAt.value = new Date(session.started_at)
    }

    localStorage.setItem(STORAGE_KEYS.SESSION_ID, session.id.toString())
    localStorage.setItem(STORAGE_KEYS.OPPONENT_TYPE, session.opponent_type)
  }

  function addMessage(message: MessageDisplay) {
    messages.value.push(message)
    
    // 更新轮数（用户或对手发送都算）
    if (message.sender === 'user' || message.sender === 'opponent') {
      turn.value++
      updateScorePrediction()
    }
    
    // 检查元对话
    if (message.isMetaConversation) {
      incrementMetaCount(message.metaKeyword || '未知')
    }
  }

  function setInitialMessages(msgs: MessageDisplay[]) {
    messages.value = msgs
    turn.value = msgs.filter(m => m.sender === 'user' || m.sender === 'opponent').length
    const metaCount = msgs.filter(m => m.isMetaConversation).length
    metaConversationCount.value = metaCount
    updateScorePrediction()
  }

  function incrementMetaCount(_keyword?: string) {
    metaConversationCount.value++
    updateScorePrediction()
    
    // 检查是否触发场中判断
    if (!triggeredMidGame.value && metaConversationCount.value > 0) {
      // 可以在这里触发场中判断提示
    }
  }

  function updateScorePrediction() {
    const currentTurns = Math.floor(turn.value / 2) // 轮数 = 消息数 / 2
    currentScorePrediction.value = calculateScorePrediction(currentTurns, metaConversationCount.value)
  }

  function setTriggeredMidGame(value: boolean) {
    triggeredMidGame.value = value
  }

  function reset() {
    sessionId.value = null
    opponentType.value = null
    turn.value = 0
    metaConversationCount.value = 0
    messages.value = []
    currentScorePrediction.value = null
    triggeredMidGame.value = false
    isHoneypot.value = false
    sessionStartedAt.value = null

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
    currentScorePrediction,
    triggeredMidGame,
    isHoneypot,
    sessionStartedAt,
    
    // 计算属性
    canEndChat,
    gameState,
    
    // 方法
    setSession,
    addMessage,
    setInitialMessages,
    incrementMetaCount,
    updateScorePrediction,
    setTriggeredMidGame,
    reset
  }
})