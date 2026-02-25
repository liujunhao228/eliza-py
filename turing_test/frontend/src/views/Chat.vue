<template>
  <div class="chat-container">
    <!-- 顶部状态栏 -->
    <ChatHeader
      :isConnected="isConnected"
      :connectionStatus="connectionState"
      @reconnect="reconnect"
      @end-chat="handleEndChat"
      @mid-game="showMidGameModal = true"
    />

    <!-- 主内容区域 -->
    <div class="chat-content">
      <!-- 消息列表和侧边栏容器 -->
      <div class="main-container">
        <!-- 消息列表 -->
        <div class="message-list-container" ref="messageListRef">
          <!-- 加载状态 -->
          <div v-if="isInitialLoading" class="loading-overlay">
            <div class="loading-content">
              <div class="loading-spinner"></div>
              <p>正在加载对话...</p>
            </div>
          </div>

          <!-- 消息列表（包括空状态） -->
          <MessageList v-else :messages="gameState.messages" />
          
          <!-- 正在输入提示 -->
          <div v-if="gameStore.isOpponentTyping" class="typing-indicator">
            <div class="typing-dots">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
            <span class="typing-text">对方正在输入...</span>
          </div>

          <!-- 滚动到底部按钮 -->
          <div
            v-show="showScrollButton"
            class="scroll-to-bottom"
            @click="scrollToBottom"
            role="button"
            aria-label="滚动到底部"
            tabindex="0"
          >
            <el-icon><Bottom /></el-icon>
          </div>
        </div>
      </div>

      <!-- 底部输入区 -->
      <div class="chat-input-section">
        <ChatInput
          :disabled="!gameStore.isUserTurn || isLoading"
          :sending="isSending"
          :placeholder="gameStore.isUserTurn ? '输入消息...' : '等待对方发送...'"
          @send="handleSendMessage"
        />
      </div>
    </div>

    <!-- 场中判断弹窗 -->
    <MidGameJudgmentModal
      v-if="showMidGameModal"
      @confirm="handleMidGameJudgment"
      @cancel="showMidGameModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bottom } from '@element-plus/icons-vue'
import ChatHeader from '@/components/Chat/ChatHeader.vue'
import MessageList from '@/components/Chat/MessageList.vue'
import ChatInput from '@/components/Chat/ChatInput.vue'
import MidGameJudgmentModal from '@/components/Chat/MidGameJudgmentModal.vue'
import { useChatWebSocket } from '@/composables/useWebSocket'
import { getSessionMessages, makeMidGameJudgment, endSession } from '@/api/game'
import { validateMessage } from '@/utils/validation'
import { isUserCancel, getErrorMessage } from '@/utils/error'
import type { MessageDisplay } from '@/types'
import { MIN_CHAT_TURNS } from '@/utils/constants'

const router = useRouter()
const gameStore = useGameStore()
const userStore = useUserStore()

// 状态
const isLoading = ref(false)
const isInitialLoading = ref(true)
const showMidGameModal = ref(false)
const showScrollButton = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
const isSending = ref(false)
// pendingMessages 用于追踪发送中消息的内容哈希，以便与服务器响应匹配
const pendingMessages = ref<Set<string>>(new Set())

// 验证连接参数
const canConnect = computed(() => {
  return !!gameStore.sessionId && !!userStore.userId
})

// 使用 WebSocket composable
const { isConnected, state: connectionState, reconnect: wsReconnect, send, on } = useChatWebSocket(
  gameStore.sessionId || 0,
  userStore.userId || 0,
  {
    autoConnect: canConnect.value,
    onMessage: handleWSMessage,
    onError: (error) => {
      console.error('[WebSocket] 连接错误:', error)
      ElMessage.error('WebSocket 连接失败，请检查后端服务')
    },
    onStateChange: (state) => {
      console.log('[WebSocket] 连接状态变化:', state)
      if (state === 'error') {
        ElMessage.warning('WebSocket 连接异常，正在尝试重连...')
      }
    }
  }
)

// 注册特定消息类型的处理器
onMounted(() => {
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
    if (!gameStore.triggeredMidGame) {
      showMidGameModal.value = true
    }
  })

  // 注册 session_ended 消息处理器
  on('session_ended', () => {
    console.log('[Chat] 收到 session_ended 消息')
    ElMessage.info('会话已结束')
    router.push('/survey')
  })

  // 注册 mid_game_result 消息处理器
  on('mid_game_result', (data: any) => {
    console.log('[Chat] 收到 mid_game_result 消息:', data)
    ElMessage.success(`场中判断结果：${data.is_correct ? '正确' : '错误'}，积分变化：${data.final_score}`)
  })

  // 注册 connected 消息处理器
  on('connected', (data: any) => {
    console.log('[Chat] WebSocket 连接已确认:', data)
    if (isInitialLoading.value) {
      isInitialLoading.value = false
    }
  })

  // 注册 error 消息处理器
  on('error', (data: any) => {
    console.error('[Chat] WebSocket 错误:', data)
    ElMessage.error(data?.message || '发生错误')
  })
})

// 重新连接函数
const reconnect = () => {
  wsReconnect()
}

// 发送消息函数
const handleSendMessage = async (content: string) => {
  if (!content.trim()) return
  if (!gameStore.sessionId) {
    ElMessage.error('会话不存在')
    return
  }
  if (!userStore.userId) {
    ElMessage.error('用户未登录')
    return
  }

  // 验证消息内容
  const validation = validateMessage(content)
  if (!validation.valid) {
    ElMessage.error(validation.error)
    return
  }

  // 检查是否为用户回合
  if (!gameStore.isUserTurn) {
    ElMessage.warning('请等待对方发送消息')
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
    send('message', { content: content.trim(), tempId: contentHash })

    // 加载完成后隐藏加载状态
    if (isInitialLoading.value) {
      isInitialLoading.value = false
    }

  } catch (error) {
    console.error('[Chat] 发送消息失败:', error)
    ElMessage.error('发送失败，请重试')
    // 发送失败时移除刚才添加的消息
    const lastMessage = gameStore.gameState.messages[gameStore.gameState.messages.length - 1]
    if (lastMessage && lastMessage.sender === 'user') {
      gameStore.messages.pop()
    }
  } finally {
    isSending.value = false
  }
}

// 计算属性
const gameState = computed(() => gameStore.gameState)

/**
 * 滚动到底部
 */
function scrollToBottom(): void {
  nextTick(() => {
    const container = messageListRef.value
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

/**
 * 检查是否需要显示滚动按钮
 */
function checkScroll(): void {
  const container = messageListRef.value
  if (container) {
    const { scrollTop, scrollHeight, clientHeight } = container
    showScrollButton.value = scrollHeight - scrollTop - clientHeight > 200
  }
}

/**
 * 处理聊天消息
 */
function handleChatMessage(data: any): void {
  console.log('[Chat] 处理聊天消息，sender:', data.sender, 'content:', data.content, 'id:', data.id)

  const message: MessageDisplay = {
    id: data.id || Date.now(),
    sender: data.sender === 'user' ? 'user' : 'opponent',
    content: data.content,
    timestamp: data.timestamp || new Date().toISOString(),
    isMetaConversation: data.is_meta_conversation || false,
    metaKeyword: data.meta_keyword
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

  // 新消息到达时滚动到底部
  scrollToBottom()
  // 加载完成后隐藏加载状态
  if (isInitialLoading.value) {
    isInitialLoading.value = false
  }
}

/**
 * 处理 WebSocket 消息（通用回调）
 */
function handleWSMessage(data: any): void {
  console.log('[Chat] 收到 WebSocket 消息 (通用回调):', data.type, data.data)

  switch (data.type) {
    case 'chat':
    case 'message':
    case 'mid_game_available':
    case 'session_ended':
    case 'mid_game_result':
    case 'connected':
    case 'error':
    case 'typing':
    case 'stop_typing':
      // 这些消息类型已有专用处理器，忽略
      break

    default:
      // 处理其他未注册的消息类型
      console.log('[Chat] 收到未注册消息:', data.type, data.data)
  }
}

/**
 * 处理场中判断
 */
async function handleMidGameJudgment(choice: 'human' | 'ai'): Promise<void> {
  if (!gameStore.sessionId) {
    ElMessage.error('会话不存在')
    return
  }

  try {
    gameStore.setTriggeredMidGame(true)
    showMidGameModal.value = false

    // 发送场中判断请求
    const result = await makeMidGameJudgment(gameStore.sessionId, choice)

    ElMessage.success(`场中判断已提交，${choice === 'human' ? '你认为是人类' : '你认为是 AI'}，结果：${result.is_correct ? '正确' : '错误'}`)

  } catch (error: any) {
    console.error('[Chat] 场中判断失败:', error)
    const errorMsg = getErrorMessage(error, '提交失败，请重试')
    ElMessage.error(errorMsg)
    gameStore.setTriggeredMidGame(false)
  }
}

/**
 * 处理结束对话（由 ChatHeader 触发）
 */
async function handleEndChat() {
  // 检查最低轮数
  const currentTurns = Math.floor(gameStore.turn / 2)
  if (currentTurns < MIN_CHAT_TURNS) {
    ElMessage.warning(`请多聊几句再结束哦（至少${MIN_CHAT_TURNS}轮，当前${currentTurns}轮）`)
    return
  }

  // 确认对话框
  try {
    await ElMessageBox.confirm(
      '确定要结束这次对话吗？',
      '结束对话',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 用户确认结束
    if (gameStore.sessionId) {
      await endSession(gameStore.sessionId)
      ElMessage.success('对话已结束')
      router.push('/survey')
    }
  } catch (error) {
    // 用户取消操作不显示错误
    if (!isUserCancel(error)) {
      const errorMsg = getErrorMessage(error, '结束对话失败，请重试')
      ElMessage.error(errorMsg)
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
    isInitialLoading.value = true

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

    // 隐藏加载状态
    isInitialLoading.value = false

  } catch (error) {
    console.error('[Chat] 加载历史消息失败:', error)
    ElMessage.error('加载历史消息失败')
    isInitialLoading.value = false
  }
}

// 生命周期
onMounted(async () => {
  // 检查用户登录状态
  if (!userStore.userId) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  // 检查会话状态
  if (!gameStore.sessionId) {
    ElMessage.warning('请先进行匹配')
    router.push('/lobby')
    return
  }

  // 加载历史消息
  await loadHistoryMessages()

  // 手动连接 WebSocket
  if (canConnect.value) {
    console.log('[Chat] 开始连接 WebSocket...')
  } else {
    console.error('[Chat] 无法连接 WebSocket：sessionId 或 userId 无效')
    ElMessage.error('连接参数无效，无法建立 WebSocket 连接')
  }

  // 添加滚动事件监听
  const container = messageListRef.value
  if (container) {
    container.addEventListener('scroll', checkScroll)
  }

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  // 移除滚动事件监听
  const container = messageListRef.value
  if (container) {
    container.removeEventListener('scroll', checkScroll)
  }

  // 移除窗口大小监听
  window.removeEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  // 恢复页面滚动
  document.body.style.overflow = ''
})

/**
 * 处理窗口大小变化
 */
function handleResize(): void {
  console.log('[Chat] 窗口大小变化:', window.innerWidth)
}
</script>

<style scoped>
/* ==============================================
   Chat 视图样式 - 新的 flex 布局
   ============================================== */

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

/* ==============================================
   主内容区域
   ============================================== */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 主容器：消息列表容器 */
.main-container {
  width: 100%;
  overflow: hidden;
}

/* 消息列表容器 */
.message-list-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  position: relative;
  scroll-behavior: smooth;
  background: var(--bg-surface);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-primary);
}

/* 自定义滚动条 */
.message-list-container::-webkit-scrollbar {
  width: 6px;
}

.message-list-container::-webkit-scrollbar-track {
  background: var(--bg-secondary);
  border-radius: 3px;
}

.message-list-container::-webkit-scrollbar-thumb {
  background: var(--color-gray-400);
  border-radius: 3px;
}

.message-list-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-gray-500);
}

/* 正在输入提示 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  margin-top: 12px;
  background: var(--bg-secondary);
  border-radius: 20px;
  width: fit-content;
  animation: fadeIn 0.3s ease-out;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.typing-text {
  font-size: 14px;
  color: var(--text-secondary);
  font-style: italic;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 底部输入区域 */
.chat-input-section {
  background: var(--bg-surface);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--border-primary);
  padding: 20px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
  border-radius: 0 0 var(--rounded-lg) var(--rounded-lg);
}

/* ==============================================
   加载状态
   ============================================== */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid var(--bg-secondary);
  border-top-color: var(--color-primary);
  border-radius: var(--rounded-full);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-content p {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
}

/* ==============================================
   滚动到底部按钮
   ============================================== */
.scroll-to-bottom {
  position: absolute;
  bottom: 80px;
  right: 20px;
  width: 48px;
  height: 48px;
  border-radius: var(--rounded-full);
  background: var(--bg-surface);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 10;
  border: 1px solid var(--border-primary);
}

.scroll-to-bottom:hover {
  background: var(--color-primary);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);
  border-color: var(--color-primary);
}

.scroll-to-bottom:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.scroll-to-bottom .el-icon {
  font-size: 20px;
  color: var(--color-primary);
}

.scroll-to-bottom:hover .el-icon,
.scroll-to-bottom:focus .el-icon {
  color: white;
}

/* ==============================================
   响应式设计
   ============================================== */

/* 超小屏 - 手机竖屏 (< 360px) */
@media (max-width: 359px) {
  .chat-container {
    font-size: 14px;
  }

  .message-list-container {
    padding: var(--spacing-sm);
    border-radius: 0;
  }

  .chat-input-section {
    padding: var(--spacing-sm);
    border-radius: 0;
  }

  .scroll-to-bottom {
    bottom: 90px;
    right: var(--spacing-sm);
    width: 36px;
    height: 36px;
  }
}

/* 小屏 - 手机横屏 (360px - 479px) */
@media (max-width: 479px) {
  .message-list-container {
    padding: var(--spacing-sm);
  }

  .chat-input-section {
    padding: var(--spacing-md);
  }
}

/* 中屏 - 小平板 (480px - 639px) */
@media (max-width: 639px) {
  .main-container {
    flex-direction: column;
  }

  .message-list-container {
    border-radius: 0;
    margin: 0;
    max-width: 100%;
    padding: var(--spacing-md);
  }

  .chat-input-section {
    padding: var(--spacing-md);
    border-radius: 0;
  }

  .scroll-to-bottom {
    bottom: 100px;
    right: var(--spacing-md);
    width: 40px;
    height: 40px;
  }
}

/* 平板 - 竖屏平板 (640px - 767px) */
@media (max-width: 767px) {
  .chat-container {
    font-size: 15px;
  }

  .main-container {
    flex-direction: column;
  }

  .message-list-container {
    border-radius: 0;
    margin: 0;
    padding: var(--spacing-lg);
  }

  .chat-input-section {
    padding: var(--spacing-lg);
  }
}

/* 平板大屏 - 横屏平板 (768px - 1023px) */
@media (max-width: 1023px) {
  .main-container {
    flex-direction: column;
  }

  .message-list-container {
    border-radius: 0;
    margin: 0;
    padding: var(--spacing-lg);
  }

  .chat-input-section {
    padding: var(--spacing-lg);
  }
}

/* 大屏 - 小桌面 (1024px - 1279px) */
@media (min-width: 1024px) and (max-width: 1279px) {
  .main-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 800px;
    border-radius: var(--rounded-lg) 0 0 0;
  }
}

/* 超大屏 - 大桌面 (1440px - 1919px) */
@media (min-width: 1440px) and (max-width: 1919px) {
  .main-container {
    max-width: 1400px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 1000px;
    border-radius: var(--rounded-lg) 0 0 0;
  }
}

/* 4K 屏幕 (1920px 以上) */
@media (min-width: 1920px) {
  .chat-container {
    font-size: 16px;
  }

  .main-container {
    max-width: 1600px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 1200px;
    border-radius: var(--rounded-lg) 0 0 0;
  }

  .chat-input-section {
    padding: var(--spacing-xl);
  }

  .message-list-container {
    padding: var(--spacing-xl);
  }
}
</style>
