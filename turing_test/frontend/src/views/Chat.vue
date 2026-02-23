<template>
  <div class="chat-container">
    <!-- 顶部游戏状态栏 -->
    <GameStatusBar />

    <!-- 连接状态提示 -->
    <div v-if="!isConnected && !isConnecting" class="disconnected-banner">
      <el-alert
        title="连接已断开"
        type="error"
        :closable="false"
        show-icon
      >
        <div class="disconnected-content">
          <span>无法连接到服务器，正在尝试重新连接...</span>
          <el-button type="primary" size="small" @click="reconnect">
            立即重连
          </el-button>
        </div>
      </el-alert>
    </div>

    <!-- 主内容区域 -->
    <div class="chat-content">
      <!-- 消息列表 -->
      <div class="message-list-container" ref="messageListRef">
        <!-- 加载状态 -->
        <div v-if="isInitialLoading" class="loading-overlay">
          <el-skeleton :rows="5" animated />
        </div>

        <!-- 空状态 -->
        <div v-else-if="gameState.messages.length === 0" class="empty-state">
          <el-empty description="等待对手消息...">
            <el-button type="primary" :loading="isConnecting" @click="reconnect">
              {{ isConnecting ? '连接中...' : '重新连接' }}
            </el-button>
          </el-empty>
        </div>

        <!-- 消息列表 -->
        <MessageList v-else :messages="gameState.messages" />

        <!-- 滚动到底部按钮 -->
        <div
          v-show="showScrollButton"
          class="scroll-to-bottom"
          @click="scrollToBottom"
        >
          <el-icon><Bottom /></el-icon>
        </div>
      </div>

      <!-- 底部区域：积分预测器和输入框 -->
      <div class="bottom-panel">
        <!-- 积分预测器 -->
        <div class="score-predictor-section">
          <ScorePredictor
            :prediction="gameState.currentScorePrediction"
            :can-end-chat="gameState.canEndChat"
          />
        </div>

        <!-- 聊天输入 -->
        <div class="chat-input-section">
          <ChatInput
            :disabled="isLoading || !isConnected"
            :loading="isLoading"
            @send="handleSendMessage"
          />
        </div>
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { Bottom } from '@element-plus/icons-vue'
import GameStatusBar from '@/widgets/GameStatusBar.vue'
import ScorePredictor from '@/widgets/ScorePredictor.vue'
import MessageList from '@/components/Chat/MessageList.vue'
import ChatInput from '@/components/Chat/ChatInput.vue'
import MidGameJudgmentModal from '@/components/Chat/MidGameJudgmentModal.vue'
import { createChatWebSocket } from '@/api/game'
import type { MessageDisplay, WSMessage, IWebSocketManager, WSConnectionState } from '@/types'

const router = useRouter()
const gameStore = useGameStore()
const userStore = useUserStore()

// 状态
const isLoading = ref(false)
const showMidGameModal = ref(false)
const wsManager = ref<IWebSocketManager | null>(null)
const isConnected = ref(false)
const isConnecting = ref(false)
const isInitialLoading = ref(true)
const showScrollButton = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
const reconnectAttempts = ref(0)
const maxReconnectAttempts = ref(5)

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
 * 处理 WebSocket 连接状态变化
 */
function handleConnectionStateChange(state: WSConnectionState): void {
  switch (state) {
    case 'connecting':
      isConnecting.value = true
      isConnected.value = false
      break
    case 'connected':
      isConnecting.value = false
      isConnected.value = true
      reconnectAttempts.value = 0
      ElMessage.success('连接成功')
      break
    case 'disconnected':
      isConnecting.value = false
      isConnected.value = false
      break
    case 'reconnecting':
      isConnecting.value = true
      isConnected.value = false
      reconnectAttempts.value++
      if (reconnectAttempts.value >= maxReconnectAttempts.value) {
        ElMessage.error('重连失败，请检查网络连接')
      }
      break
    case 'error':
      isConnecting.value = false
      isConnected.value = false
      ElMessage.error('连接错误')
      break
  }
}

/**
 * 处理 WebSocket 消息
 */
function handleWSMessage(data: WSMessage): void {
  switch (data.type) {
    case 'message':
      // 收到对手消息
      const message: MessageDisplay = {
        id: data.data.id,
        sender: data.data.sender === userStore.userId ? 'user' : 'opponent',
        content: data.data.content,
        timestamp: data.data.timestamp,
        isMetaConversation: data.data.is_meta_conversation || false,
        metaKeyword: data.data.meta_keyword
      }
      gameStore.addMessage(message)
      // 新消息到达时滚动到底部
      scrollToBottom()
      // 加载完成后隐藏加载状态
      if (isInitialLoading.value) {
        isInitialLoading.value = false
      }
      break

    case 'session_ended':
      // 会话结束
      ElMessage.info('会话已结束')
      router.push('/survey')
      break

    case 'error':
      // 错误消息
      ElMessage.error(data.data?.message || '发生错误')
      break

    case 'pong':
      // 心跳响应，忽略
      break

    default:
      // 处理其他消息类型（包括 mid_game_available 等）
      console.log('[Chat] 收到消息:', data.type, data.data)
      if (data.type === 'mid_game_available') {
        if (!gameStore.triggeredMidGame) {
          showMidGameModal.value = true
        }
      }
  }
}

/**
 * 初始化 WebSocket 连接
 */
function initWebSocket(): void {
  const sid = gameStore.sessionId
  const uid = userStore.userId
  
  if (!sid) {
    ElMessage.error('会话 ID 不存在')
    router.push('/lobby')
    return
  }
  
  if (!uid) {
    ElMessage.error('用户未登录')
    router.push('/login')
    return
  }

  isConnecting.value = true

  // 创建 WebSocket 管理器
  wsManager.value = createChatWebSocket(sid, uid)

  // 注册消息处理器
  wsManager.value.on('message', handleWSMessage)
  wsManager.value.on('session_ended', () => handleWSMessage({ type: 'session_ended' }))
  wsManager.value.on('mid_game_available', () => handleWSMessage({ type: 'error' }))

  // 注册连接状态变化处理器
  wsManager.value.on('stateChange', handleConnectionStateChange)

  // 连接
  wsManager.value.connect()

  // 设置加载超时
  setTimeout(() => {
    if (isInitialLoading.value && !isConnected.value) {
      isInitialLoading.value = false
      ElMessage.warning('连接超时，请检查网络')
    }
  }, 10000)
}

/**
 * 重新连接
 */
function reconnect(): void {
  if (isConnecting.value) return

  ElMessage.info('正在重新连接...')
  reconnectAttempts.value = 0
  initWebSocket()
}

/**
 * 发送消息
 */
async function handleSendMessage(content: string): Promise<void> {
  if (!content.trim()) return
  if (!gameStore.sessionId) {
    ElMessage.error('会话不存在')
    return
  }
  if (!wsManager.value || !wsManager.value.isConnected()) {
    ElMessage.error('连接已断开，请刷新页面')
    return
  }

  isLoading.value = true

  try {
    // 通过 WebSocket 发送消息
    wsManager.value.send('message', { content })

    // 添加用户消息到本地
    const userMessage: MessageDisplay = {
      id: Date.now(),
      sender: 'user',
      content: content,
      timestamp: new Date().toISOString(),
      isMetaConversation: false // 这里会在后端检测
    }
    gameStore.addMessage(userMessage)

  } catch (error) {
    console.error('[Chat] 发送消息失败:', error)
    ElMessage.error('发送失败，请重试')
  } finally {
    isLoading.value = false
  }
}

/**
 * 处理场中判断
 */
async function handleMidGameJudgment(choice: 'human' | 'ai'): Promise<void> {
  try {
    gameStore.setTriggeredMidGame(true)
    showMidGameModal.value = false

    // 发送场中判断请求
    const response = await fetch(`http://localhost:8000/api/game/${gameStore.sessionId}/mid-game`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        guess: choice
      })
    })

    if (!response.ok) {
      throw new Error('场中判断失败')
    }

    ElMessage.success(`场中判断已提交，${choice === 'human' ? '你认为是人类' : '你认为是 AI'}`)

  } catch (error) {
    console.error('[Chat] 场中判断失败:', error)
    ElMessage.error('提交失败，请重试')
    gameStore.setTriggeredMidGame(false)
  }
}

// 生命周期
onMounted(() => {
  // 检查会话状态
  if (!gameStore.sessionId) {
    ElMessage.warning('请先进行匹配')
    router.push('/lobby')
    return
  }

  // 初始化 WebSocket 连接
  initWebSocket()

  // 添加滚动事件监听
  const container = messageListRef.value
  if (container) {
    container.addEventListener('scroll', checkScroll)
  }
})

onUnmounted(() => {
  // 移除滚动事件监听
  const container = messageListRef.value
  if (container) {
    container.removeEventListener('scroll', checkScroll)
  }

  // 关闭 WebSocket 连接
  if (wsManager.value) {
    wsManager.value.disconnect()
    wsManager.value = null
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
}

.disconnected-banner {
  padding: 10px 20px;
  background: #fef0f0;
  border-bottom: 1px solid #fde2e2;
}

.disconnected-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.disconnected-content span {
  color: #f56c6c;
  font-size: 14px;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-list-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  position: relative;
  scroll-behavior: smooth;
}

/* 加载状态 */
.loading-overlay {
  padding: 20px;
}

/* 空状态 */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}

/* 滚动到底部按钮 */
.scroll-to-bottom {
  position: absolute;
  bottom: 80px;
  right: 40px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  z-index: 10;
}

.scroll-to-bottom:hover {
  background: #667eea;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
}

.scroll-to-bottom .el-icon {
  font-size: 20px;
  color: #667eea;
}

.scroll-to-bottom:hover .el-icon {
  color: white;
}

.bottom-panel {
  background: white;
  border-top: 1px solid #e4e7ed;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
}

.score-predictor-section {
  flex-shrink: 0;
}

.chat-input-section {
  flex-shrink: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .bottom-panel {
    padding: 15px;
    gap: 10px;
  }

  .message-list-container {
    padding: 15px;
  }

  .scroll-to-bottom {
    bottom: 70px;
    right: 20px;
    width: 36px;
    height: 36px;
  }

  .scroll-to-bottom .el-icon {
    font-size: 18px;
  }

  .disconnected-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .disconnected-content .el-button {
    width: 100%;
  }
}
</style>
