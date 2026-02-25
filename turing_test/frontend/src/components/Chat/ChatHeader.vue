<template>
  <div class="chat-header">
    <!-- 左侧：返回按钮 + 博弈状态信息 -->
    <div class="header-left">
      <div class="nav-buttons">
        <BaseButton
          type="info"
          size="small"
          @click="handleBack"
          class="back-btn"
        >
          ← 返回
        </BaseButton>
      </div>
      
      <div class="game-info">
        <h2 class="session-title">
          <el-icon><ChatDotRound /></el-icon>
          聊天室
        </h2>
        <div class="turn-info">
          <span class="turn-label">第 {{ turn }} 轮</span>
          <span v-if="metaConversationCount > 0" class="meta-count">
            元对话 {{ metaConversationCount }} 次
          </span>
        </div>
      </div>
    </div>

    <!-- 右侧：场中判断 + 结束对话 + 连接状态 -->
    <div class="header-right">
      <!-- 场中判断按钮 -->
      <BaseButton
        type="warning"
        size="small"
        :disabled="triggeredMidGame"
        @click="handleMidGame"
        class="mid-game-btn"
      >
        ⚡ 场中判断
      </BaseButton>
      
      <!-- 结束对话按钮 -->
      <BaseButton
        type="danger"
        size="small"
        @click="handleEndChat"
        class="end-chat-btn"
      >
        结束对话
      </BaseButton>
      
      <!-- 连接状态指示器 -->
      <div
        class="connection-status"
        :class="connectionStatusClass"
        role="status"
        :aria-label="`连接状态：${connectionStatusText}`"
      >
        <div class="status-indicator">
          <el-icon v-if="connectionStatus !== 'connected'" :class="statusIconClass">
            <Connection />
          </el-icon>
          <el-icon v-else class="status-icon-success">
            <Select />
          </el-icon>
        </div>
        <span class="status-text">{{ connectionStatusText }}</span>
      </div>
    </div>

    <!-- 非侵入式断开连接提示 -->
    <div
      v-if="!isConnected && connectionStatus === 'disconnected'"
      class="connection-warning"
      role="alert"
    >
      <el-alert
        title="连接已断开"
        type="warning"
        :closable="false"
        show-icon
        class="warning-alert"
      >
        <div class="warning-content">
          <span>正在尝试重新连接...</span>
          <el-button
            type="primary"
            size="small"
            link
            @click="$emit('reconnect')"
          >
            立即重连
          </el-button>
        </div>
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, Connection, Select } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'
import { BaseButton } from '@/components/common'
import type { WSConnectionState } from '@/types'
import { MIN_CHAT_TURNS } from '@/utils/constants'
import { endSession } from '@/api/game'

interface Props {
  isConnected?: boolean
  connectionStatus?: WSConnectionState
}

interface Emits {
  (e: 'reconnect'): void
  (e: 'end-chat'): void
  (e: 'mid-game'): void
}

const props = withDefaults(defineProps<Props>(), {
  isConnected: false,
  connectionStatus: 'disconnected'
})

const emit = defineEmits<Emits>()
const router = useRouter()
const gameStore = useGameStore()

// 计算属性
const turn = computed(() => gameStore.gameState.turn)
const metaConversationCount = computed(() => gameStore.metaConversationCount)
const triggeredMidGame = computed(() => gameStore.triggeredMidGame)

// 连接状态相关计算
const connectionStatusText = computed(() => {
  switch (props.connectionStatus) {
    case 'connecting':
      return '连接中...'
    case 'connected':
      return '已连接'
    case 'reconnecting':
      return '重新连接中...'
    case 'error':
      return '连接错误'
    default:
      return '未连接'
  }
})

const connectionStatusClass = computed(() => ({
  'status-disconnected': !props.isConnected && props.connectionStatus === 'disconnected',
  'status-connecting': props.connectionStatus === 'connecting',
  'status-reconnecting': props.connectionStatus === 'reconnecting',
  'status-error': props.connectionStatus === 'error',
  'status-connected': props.isConnected && props.connectionStatus === 'connected'
}))

const statusIconClass = computed(() => ({
  'status-icon-disconnected': !props.isConnected && props.connectionStatus === 'disconnected',
  'status-icon-connecting': props.connectionStatus === 'connecting',
  'status-icon-reconnecting': props.connectionStatus === 'reconnecting',
  'status-icon-error': props.connectionStatus === 'error'
}))

// 返回大厅
function handleBack() {
  router.push('/lobby')
}

// 场中判断
function handleMidGame() {
  emit('mid-game')
}

// 结束对话
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
    // 用户取消或错误
    if (error !== 'cancel') {
      ElMessage.error('结束对话失败，请重试')
    }
  }
}
</script>

<style scoped>
/* ==============================================
   ChatHeader 样式
   ============================================== */

.chat-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-primary);
  min-height: 110px;
}

/* 左侧区域 */
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.nav-buttons {
  display: flex;
  align-items: center;
}

.back-btn {
  height: 32px;
  padding: 0 12px;
}

.game-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.session-title .el-icon {
  color: var(--color-primary);
  font-size: 20px;
}

.turn-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.turn-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: var(--rounded-sm);
}

.meta-count {
  font-size: 13px;
  color: var(--color-amber-600);
  font-weight: 500;
}

/* 右侧区域 */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mid-game-btn {
  height: 32px;
  padding: 0 12px;
}

.end-chat-btn {
  height: 32px;
  padding: 0 12px;
}

/* 连接状态指示器 */
.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--rounded-full);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-disconnected {
  background: var(--color-red-50);
  color: var(--color-error);
}

.status-icon-disconnected {
  animation: pulse 2s ease-in-out infinite;
}

.status-connecting,
.status-reconnecting {
  background: var(--color-amber-50);
  color: var(--color-amber-600);
}

.status-icon-connecting,
.status-icon-reconnecting {
  animation: spin 1.5s linear infinite;
}

.status-error {
  background: var(--color-red-50);
  color: var(--color-error);
}

.status-icon-error {
  animation: shake 0.5s ease-in-out;
}

.status-connected {
  background: var(--color-green-50);
  color: var(--color-success);
}

.status-icon-success {
  color: var(--color-success);
}

.status-text {
  font-weight: 500;
}

/* 非侵入式警告 */
.connection-warning {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-amber-50);
  border-bottom: 1px solid var(--color-amber-200);
  animation: slideDown 0.3s ease-out;
  overflow: hidden;
}

.warning-alert {
  background: transparent;
  border: none;
  margin: 12px 24px;
}

.warning-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.warning-content span {
  color: var(--color-amber-700);
  font-size: 14px;
}

.warning-content .el-button {
  color: var(--color-amber-700);
  font-size: 13px;
}

/* 动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-2px);
  }
  75% {
    transform: translateX(2px);
  }
}

/* ==============================================
   响应式设计
   ============================================== */

/* 移动端 */
@media (max-width: 768px) {
  .chat-header {
    padding: 12px 16px;
    min-height: auto;
  }

  .header-left {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .nav-buttons {
    justify-content: flex-start;
  }

  .session-title {
    font-size: 16px;
  }

  .session-title .el-icon {
    font-size: 18px;
  }

  .turn-info {
    gap: 8px;
  }

  .turn-label {
    font-size: 13px;
    padding: 2px 6px;
  }

  .meta-count {
    font-size: 12px;
  }

  .header-right {
    justify-content: space-between;
    width: 100%;
  }

  .connection-status {
    padding: 3px 10px;
    font-size: 12px;
  }

  .warning-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .warning-content span {
    font-size: 13px;
  }
  
  .mid-game-btn,
  .end-chat-btn {
    flex: 1;
    font-size: 12px;
  }
}

/* 平板端 */
@media (max-width: 1024px) and (min-width: 769px) {
  .chat-header {
    padding: 14px 20px;
  }

  .session-title {
    font-size: 17px;
  }
}
</style>
