<template>
  <div class="chat-container">
    <!-- 顶部状态栏 -->
    <ChatHeader
      :isConnected="isConnected"
      :connectionStatus="connectionState"
      :isOpponentTyping="gameStore.isOpponentTyping"
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

          <!-- 滚动到底部按钮 -->
          <div
            v-show="showScrollButton"
            class="scroll-to-bottom"
            @click="scrollToBottom"
            role="button"
            aria-label="滚动到底部"
            tabindex="0"
            @keydown.enter="scrollToBottom"
            @keydown.space.prevent="scrollToBottom"
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
      v-model="showMidGameModal"
      @confirm="handleMidGameJudgment"
      @cancel="showMidGameModal = false"
    />

    <!-- 结束对话确认弹窗 -->
    <EndSessionModal
      v-model="showEndSessionModal"
      :has-made-judgment="hasMadeJudgment"
      :loading="isEndingSession"
      @cancel="showEndSessionModal = false"
      @confirm="handleConfirmEndSession"
    />

    <!-- 结束对话倒计时提示 -->
    <EndSessionToast
      ref="endSessionToastRef"
      :duration="5"
      redirect-url="/survey"
      @countdown-end="handleCountdownEnd"
    />

    <!-- 对方已离开提示条 -->
    <div v-if="opponentEnded" class="opponent-ended-banner">
      <div class="banner-content">
        <div class="banner-icon">
          <el-icon :size="20"><UserFilled /></el-icon>
        </div>
        <div class="banner-text">
          <h4 class="banner-title">对方已离开</h4>
          <p class="banner-desc">
            您可以继续停留 <strong>{{ countdown }}</strong> 秒后填写问卷，或立即结束
          </p>
        </div>
        <el-button
          type="primary"
          size="small"
          @click="handleImmediateSurvey"
          class="immediate-btn"
        >
          立即填写问卷
        </el-button>
      </div>
      <!-- 进度条 -->
      <div class="banner-progress">
        <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import { Bottom, UserFilled } from '@element-plus/icons-vue'
import ChatHeader from '@/components/Chat/ChatHeader.vue'
import MessageList from '@/components/Chat/MessageList.vue'
import ChatInput from '@/components/Chat/ChatInput.vue'
import MidGameJudgmentModal from '@/components/Chat/MidGameJudgmentModal.vue'
import EndSessionModal from '@/components/Chat/EndSessionModal.vue'
import EndSessionToast from '@/components/Chat/EndSessionToast.vue'
import { useChatState } from './composables/useChatState'
import { useMessageHandler } from './composables/useMessageHandler'
import { useScroll } from './composables/useScroll'
import { MIN_CHAT_TURNS } from '@/utils/constants'

const { error: showError, warning: showWarning, info: showInfo } = useToast()
const router = useRouter()
const gameStore = useGameStore()
const userStore = useUserStore()

// 本地状态
const showEndSessionModal = ref(false)
const isEndingSession = ref(false)
const endSessionToastRef = ref<InstanceType<typeof EndSessionToast> | null>(null)

// 对方离开状态
const opponentEnded = ref(false)
const countdown = ref(10)
const elapsed = ref(0)
let countdownTimer: number | null = null

// 计算进度百分比
const progressPercent = computed(() => {
  const total = 10
  return ((total - elapsed.value) / total) * 100
})

// 计算是否已做判断（根据 triggeredMidGame 判断）
const hasMadeJudgment = computed(() => {
  return gameStore.gameState.triggeredMidGame
})

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
  handleMidGameJudgment: handleMidGameJudgmentAction,
  handleEndChat: baseHandleEndChat,
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

// 处理场中判断
const handleMidGameJudgment = async (choice: 'human' | 'ai') => {
  try {
    await handleMidGameJudgmentAction(choice, send)
    showMidGameModal.value = false  // 提交成功后关闭弹窗
  } catch (error) {
    console.error('[Chat] 场中判断失败:', error)
    // 失败时保持弹窗打开
  }
}

// 处理结束对话（显示确认弹窗）
const handleEndChat = () => {
  // 检查最低轮数（与顶部计数器逻辑保持一致，使用 Math.ceil）
  const currentTurns = Math.ceil(gameStore.turn / 2)
  if (currentTurns < MIN_CHAT_TURNS) {
    showWarning(`请多聊几句再结束哦（至少${MIN_CHAT_TURNS}轮，当前${currentTurns}轮）`)
    return
  }
  showEndSessionModal.value = true
}

// 处理确认结束
// 根据是否已做判断自动发送正确的 end_reason
const handleConfirmEndSession = async () => {
  isEndingSession.value = true
  try {
    // 已做判断 = normal_end, 未做判断 = user_gave_up
    const endReason = hasMadeJudgment.value ? 'normal_end' : 'user_gave_up'
    await baseHandleEndChat(endReason)
    showEndSessionModal.value = false
  } catch (error) {
    console.error('[Chat] 结束会话失败:', error)
  } finally {
    isEndingSession.value = false
  }
}

// 处理倒计时结束
const handleCountdownEnd = () => {
  console.log('[Chat] 倒计时结束，即将跳转')
}

// 处理对方离开 - 开始倒计时
const startOpponentEndedCountdown = () => {
  // 清除之前的定时器
  stopCountdown()
  
  // 重置状态
  opponentEnded.value = true
  countdown.value = 10
  elapsed.value = 0
  
  // 启动倒计时
  countdownTimer = window.setInterval(() => {
    elapsed.value += 1
    
    if (elapsed.value >= 10) {
      // 倒计时结束，自动跳转到 Survey
      stopCountdown()
      showInfo('即将跳转到问卷页面')
      router.push('/survey')
    } else {
      countdown.value = 10 - elapsed.value
    }
  }, 1000)
}

// 停止倒计时
const stopCountdown = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

// 立即填写问卷
const handleImmediateSurvey = () => {
  stopCountdown()
  router.push('/survey')
}

// 导出显示倒计时提示的方法给 useChatState 使用
const showEndSessionToast = () => {
  endSessionToastRef.value?.show()
}

// 生命周期
onMounted(async () => {
  // 检查用户登录状态
  if (!userStore.userId) {
    showWarning('请先登录')
    router.push('/login')
    return
  }

  // 检查会话状态
  if (!gameStore.sessionId) {
    showWarning('请先进行匹配')
    router.push('/lobby')
    return
  }

  // 加载历史消息
  await loadHistoryMessages()

  // 注册 WebSocket 消息处理器
  chatStateOnMounted(showEndSessionToast)

  // 注册 opponent_ended 消息处理器（显示对方离开提示条）
  const { on } = useChatState()
  on('opponent_ended', () => {
    console.log('[Chat] 收到 opponent_ended 消息，显示提示条')
    startOpponentEndedCountdown()
  })

  // 手动连接 WebSocket
  if (canConnect.value) {
    console.log('[Chat] 开始连接 WebSocket...')
    reconnect() // 显式调用连接
  } else {
    console.error('[Chat] 无法连接 WebSocket：sessionId 或 userId 无效')
    showError('连接参数无效，无法建立 WebSocket 连接')
  }

  // 添加滚动事件监听
  setupScrollListener()
})

onUnmounted(() => {
  // 移除滚动事件监听
  cleanupScrollListener()
  // 清理倒计时定时器
  stopCountdown()
})
</script>

<style scoped>
/* ==============================================
   Chat 视图样式 - 类微信/QQ 固定布局
   ============================================== */

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  min-height: -webkit-fill-available;
  background: var(--bg-primary);
  overflow: hidden;
}

/* ==============================================
   主内容区域 - flex 布局固定高度
   ============================================== */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  min-height: 0;
}

/* 主容器：固定大小，消息在此容器内滚动 */
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  width: 100%;
  min-height: 0;
}

/* 消息列表容器 - 可滚动区域 */
.message-list-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 20px;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
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
  transition: background 0.2s ease;
}

.message-list-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-gray-500);
}

/* 底部输入区域 - 固定位置 */
.chat-input-section {
  flex-shrink: 0;
  background: var(--bg-surface);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--border-primary);
  padding: 16px 20px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
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
   滚动到底部按钮 - 微交互动效
   ============================================== */
.scroll-to-bottom {
  position: absolute;
  bottom: 80px;
  right: 20px;
  width: 44px;
  height: 44px;
  border-radius: var(--rounded-full);
  background: var(--bg-surface);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
  border: 1px solid var(--border-primary);
  touch-action: manipulation;
}

.scroll-to-bottom:hover {
  background: var(--color-primary);
  color: white;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);
  border-color: var(--color-primary);
}

.scroll-to-bottom:active {
  transform: translateY(0) scale(0.95);
  transition-duration: 0.1s;
}

.scroll-to-bottom:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.scroll-to-bottom:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.scroll-to-bottom .el-icon {
  font-size: 20px;
  color: var(--color-primary);
  transition: color 0.2s ease;
}

.scroll-to-bottom:hover .el-icon,
.scroll-to-bottom:focus .el-icon {
  color: white;
}

/* ==============================================
   响应式设计 - 移动优先
   ============================================== */

/* 手机竖屏 (< 360px) */
@media (max-width: 359px) {
  .chat-container {
    font-size: 14px;
  }

  .message-list-container {
    padding: 12px;
    border-radius: 0;
  }

  .chat-input-section {
    padding: 12px;
    border-radius: 0;
  }

  .scroll-to-bottom {
    bottom: 70px;
    right: 12px;
    width: 40px;
    height: 40px;
  }
}

/* 手机横屏 (360px - 479px) */
@media (min-width: 360px) and (max-width: 479px) {
  .message-list-container {
    padding: 14px;
  }

  .chat-input-section {
    padding: 14px;
  }

  .scroll-to-bottom {
    bottom: 75px;
    right: 14px;
  }
}

/* 小平板 (480px - 639px) */
@media (min-width: 480px) and (max-width: 639px) {
  .message-list-container {
    padding: 16px;
  }

  .chat-input-section {
    padding: 16px;
  }

  .scroll-to-bottom {
    bottom: 80px;
    right: 16px;
  }
}

/* 平板竖屏 (640px - 767px) */
@media (min-width: 640px) and (max-width: 767px) {
  .chat-container {
    font-size: 15px;
  }

  .message-list-container {
    padding: 16px;
  }

  .chat-input-section {
    padding: 16px;
  }
}

/* 平板横屏/小桌面 (768px - 1023px) */
@media (min-width: 768px) and (max-width: 1023px) {
  .main-container {
    max-width: 90%;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 95%;
    margin: 0 auto;
  }
}

/* 桌面 (1024px - 1279px) */
@media (min-width: 1024px) and (max-width: 1279px) {
  .main-container {
    max-width: 1000px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 700px;
  }
}

/* 大桌面 (1280px - 1439px) */
@media (min-width: 1280px) and (max-width: 1439px) {
  .main-container {
    max-width: 1100px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 800px;
  }
}

/* 超大桌面 (1440px - 1919px) */
@media (min-width: 1440px) and (max-width: 1919px) {
  .main-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 900px;
  }
}

/* 4K 屏幕 (1920px 以上) */
@media (min-width: 1920px) {
  .chat-container {
    font-size: 16px;
  }

  .main-container {
    max-width: 1400px;
    margin: 0 auto;
  }

  .message-list-container {
    max-width: 1000px;
    padding: 24px;
  }

  .chat-input-section {
    padding: 20px;
  }
}

/* ==============================================
   移动端安全区域适配 (iPhone 刘海屏等)
   ============================================== */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .chat-input-section {
    padding-bottom: calc(16px + env(safe-area-inset-bottom));
  }
}

@supports (padding-top: env(safe-area-inset-top)) {
  .chat-header {
    padding-top: calc(16px + env(safe-area-inset-top));
  }
}

/* ==============================================
   对方已离开提示条
   ============================================== */
.opponent-ended-banner {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9998;
  background: var(--bg-surface);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-primary);
  overflow: hidden;
  min-width: 360px;
  max-width: 90vw;
  animation: slide-down 0.3s ease-out;
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
}

.banner-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--rounded-full);
  background: var(--color-warning-soft);
  color: var(--color-warning);
  flex-shrink: 0;
}

.banner-text {
  flex: 1;
  min-width: 0;
}

.banner-title {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.banner-desc {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.banner-desc strong {
  color: var(--color-primary-600);
  font-weight: 600;
}

.immediate-btn {
  flex-shrink: 0;
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
}

.banner-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--bg-secondary);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-warning-gradient, var(--color-warning));
  transition: width 0.1s linear;
}

/* 响应式设计 */
@media (max-width: 639px) {
  .opponent-ended-banner {
    top: 10px;
    left: 10px;
    right: 10px;
    transform: none;
    min-width: auto;
    max-width: none;
  }

  .banner-content {
    padding: 12px 16px;
    gap: 12px;
  }

  .banner-title {
    font-size: 15px;
  }

  .banner-desc {
    font-size: 13px;
  }

  .immediate-btn {
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
  }
}
</style>
