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
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { Bottom } from '@element-plus/icons-vue'
import ChatHeader from '@/components/Chat/ChatHeader.vue'
import MessageList from '@/components/Chat/MessageList.vue'
import ChatInput from '@/components/Chat/ChatInput.vue'
import MidGameJudgmentModal from '@/components/Chat/MidGameJudgmentModal.vue'
import { useChatState } from './composables/useChatState'
import { useMessageHandler } from './composables/useMessageHandler'
import { useScroll } from './composables/useScroll'

const router = useRouter()
const gameStore = useGameStore()
const userStore = useUserStore()

// 使用 ChatState composable
const {
  isLoading,
  isInitialLoading,
  showMidGameModal,
  isConnected,
  connectionState,
  canConnect,
  reconnect,
  send,
  onMountedSetup: chatStateOnMounted
} = useChatState()

// 使用 MessageHandler composable
const {
  isSending,
  handleSendMessage: handlerSendMessage,
  handleMidGameJudgment,
  handleEndChat,
  loadHistoryMessages
} = useMessageHandler()

// 使用 Scroll composable
const {
  showScrollButton,
  scrollToBottom,
  setupScrollListener,
  cleanupScrollListener
} = useScroll()

// 计算属性
const gameState = computed(() => gameStore.gameState)

// 包装发送消息函数
const handleSendMessage = async (content: string) => {
  await handlerSendMessage(content, send)
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

  // 注册 WebSocket 消息处理器
  chatStateOnMounted()

  // 手动连接 WebSocket
  if (canConnect.value) {
    console.log('[Chat] 开始连接 WebSocket...')
  } else {
    console.error('[Chat] 无法连接 WebSocket：sessionId 或 userId 无效')
    ElMessage.error('连接参数无效，无法建立 WebSocket 连接')
  }

  // 添加滚动事件监听
  setupScrollListener()
})

onUnmounted(() => {
  // 移除滚动事件监听
  cleanupScrollListener()
})
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
