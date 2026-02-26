/**
 * 消息处理 Composable
 *
 * 负责：
 * - 消息发送
 * - 消息验证
 * - 错误处理
 * - 历史消息加载
 */

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { getSessionMessages, endSession } from '@/api/game'
import { validateMessage } from '@/utils/validation'
import { isUserCancel, getErrorMessage } from '@/utils/error'
import { useToast } from '@/composables/useToast'
import type { MessageDisplay } from '@/types'

export function useMessageHandler() {
  const router = useRouter()
  const gameStore = useGameStore()
  const userStore = useUserStore()
  const { error: showError, success: showSuccess, warning: showWarning } = useToast()

  // 状态
  const isSending = ref(false)
  const showMidGameModal = ref(false)
  // pendingMessages 用于追踪发送中消息的内容哈希，以便与服务器响应匹配
  const pendingMessages = ref<Set<string>>(new Set())

  /**
   * 发送消息
   */
  async function handleSendMessage(content: string, sendFn: (type: string, data: any) => void): Promise<void> {
    if (!content.trim()) return
    if (!gameStore.sessionId) {
      showError('会话不存在')
      return
    }
    if (!userStore.userId) {
      showError('用户未登录')
      return
    }

    // 验证消息内容
    const validation = validateMessage(content)
    if (!validation.valid) {
      if (validation.error) {
        showError(validation.error || '消息验证失败')
      }
      return
    }

    // 检查是否为用户回合
    if (!gameStore.isUserTurn) {
      showWarning('请等待对方发送消息')
      return
    }

    isSending.value = true

    try {
      // 生成消息内容哈希作为临时追踪 ID
      const contentHash = `${Date.now()}-${content.trim().substring(0, 50)}`
      pendingMessages.value.add(contentHash)

      // 先添加消息到本地列表（乐观更新）
      const tempMessageId = Date.now()
      const tempMessage: MessageDisplay = {
        id: tempMessageId,
        sender: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString(),
        isMetaConversation: false
      }
      gameStore.addMessage(tempMessage)

      // 使用 WebSocket composable 发送消息
      sendFn('message', { content: content.trim(), tempId: contentHash })

      // 加载完成后隐藏加载状态
      if (gameStore.messages.length === 0) {
        // 隐藏加载状态的逻辑由父组件处理
      }
    } catch (error) {
      console.error('[Chat] 发送消息失败:', error)
      showError('发送失败，请重试')
      // 发送失败时移除刚才添加的消息
      const lastMessage = gameStore.messages[gameStore.messages.length - 1]
      if (lastMessage && lastMessage.sender === 'user') {
        gameStore.messages.pop()
      }
    } finally {
      isSending.value = false
    }
  }

  /**
   * 处理场中判断
   * @param choice 用户选择 'human' | 'ai'
   * @param send WebSocket send 函数
   */
  async function handleMidGameJudgment(choice: 'human' | 'ai', send: (type: string, data: any) => void): Promise<void> {
    if (!gameStore.sessionId) {
      showError('会话不存在')
      return
    }

    try {
      // 通过 WebSocket 发送场中判断
      send('mid_game_judgment', { user_guess: choice })
      // 更新 store 状态（结果将通过 mid_game_result 消息返回）
      // 注意：实际结果在 WebSocket 消息处理器中更新

      showSuccess(`场中判断已提交：${choice === 'human' ? '你认为是人类' : '你认为是 AI'}`)
    } catch (error: any) {
      console.error('[Chat] 场中判断失败:', error)
      const errorMsg = getErrorMessage(error, '提交失败，请重试')
      showError(errorMsg)
      gameStore.setTriggeredMidGame(false)
    }
  }

  /**
   * 处理结束对话
   */
  async function handleEndChat(endReason: string = 'user_gave_up'): Promise<void> {
    if (!gameStore.sessionId) {
      showError('会话不存在')
      return
    }

    try {
      // 发送结束请求，传递结束原因
      await endSession(gameStore.sessionId, endReason)
      showSuccess('对话已结束，请提交问卷以结算积分')
      router.push('/survey')
    } catch (error) {
      console.error('[Chat] 结束对话失败:', error)
      // 用户取消操作不显示错误
      if (!isUserCancel(error)) {
        const errorMsg = getErrorMessage(error, '结束对话失败，请重试')
        showError(errorMsg)
      }
    }
  }

  /**
   * 加载历史消息
   */
  async function loadHistoryMessages(): Promise<void> {
    if (!gameStore.sessionId) {
      console.warn('[Chat] 会话 ID 不存在，无法加载历史消息')
      return
    }

    try {
      const response = await getSessionMessages(gameStore.sessionId)

      // 转换消息格式
      const historyMessages: MessageDisplay[] = response.messages.map(msg => ({
        id: msg.id,
        sender: msg.sender === 'user' ? 'user' : 'opponent',
        content: msg.content,
        timestamp: msg.created_at,
        isMetaConversation: msg.is_meta_conversation,
        metaKeyword: msg.meta_keyword || undefined
      }))

      // 设置到 store
      gameStore.setInitialMessages(historyMessages)

      console.log(`[Chat] 加载了 ${historyMessages.length} 条历史消息`)
    } catch (error) {
      console.error('[Chat] 加载历史消息失败:', error)
      showError('加载历史消息失败')
    }
  }

  return {
    // 状态
    isSending,
    showMidGameModal,
    pendingMessages,
    // 方法
    handleSendMessage,
    handleMidGameJudgment,
    handleEndChat,
    loadHistoryMessages
  }
}
