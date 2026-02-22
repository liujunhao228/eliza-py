<template>
  <div class="chat-container">
    <!-- 顶部游戏状态栏 -->
    <GameStatusBar />

    <!-- 主内容区域 -->
    <div class="chat-content">
      <!-- 消息列表 -->
      <div class="message-list-container">
        <MessageList :messages="gameState.messages" />
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import GameStatusBar from '@/widgets/GameStatusBar.vue'
import ScorePredictor from '@/widgets/ScorePredictor.vue'
import MessageList from '@/components/Chat/MessageList.vue'
import ChatInput from '@/components/Chat/ChatInput.vue'
import MidGameJudgmentModal from '@/components/Chat/MidGameJudgmentModal.vue'
import { createChatWebSocket } from '@/api/game'
import type { MessageDisplay, WSMessage, IWebSocketManager } from '@/types'

const router = useRouter()
const gameStore = useGameStore()
const userStore = useUserStore()

// 状态
const isLoading = ref(false)
const showMidGameModal = ref(false)
const wsManager = ref<IWebSocketManager | null>(null)
const isConnected = ref(false)

// 计算属性
const gameState = computed(() => gameStore.gameState)

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
  if (!gameStore.sessionId) {
    ElMessage.error('会话 ID 不存在')
    router.push('/lobby')
    return
  }

  // 创建 WebSocket 管理器
  wsManager.value = createChatWebSocket(gameStore.sessionId)

  // 注册消息处理器
  wsManager.value.on('message', handleWSMessage)
  wsManager.value.on('session_ended', () => handleWSMessage({ type: 'session_ended' }))
  wsManager.value.on('mid_game_available', () => handleWSMessage({ type: 'error' }))

  // 连接
  wsManager.value.connect()
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
})

onUnmounted(() => {
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
}

.bottom-panel {
  background: white;
  border-top: 1px solid #e4e7ed;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
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
}
</style>
