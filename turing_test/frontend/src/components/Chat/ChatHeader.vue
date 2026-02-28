<template>
  <div class="chat-header">
    <!-- 左侧：博弈状态信息 -->
    <div class="header-left">
      <GameInfo :turn="turn" :meta-count="metaConversationCount" />

      <!-- 正在输入提示 -->
      <div v-if="isOpponentTyping" class="typing-indicator-header">
        <div class="typing-dots">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
        <span class="typing-text">对方正在输入...</span>
      </div>
    </div>

    <!-- 右侧：场中判断 + 结束对话 + 连接状态 -->
    <div class="header-right">
      <ActionButtons
        :disabled="triggeredMidGame"
        @mid-game="$emit('mid-game')"
        @end-chat="$emit('end-chat')"
      />

      <ConnectionStatus :isConnected="isConnected" :status="connectionStatus" />
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
import { useGameStore } from '@/stores/game'
import type { WSConnectionState } from '@/types'
import GameInfo from './Header/GameInfo.vue'
import ActionButtons from './Header/ActionButtons.vue'
import ConnectionStatus from './Header/ConnectionStatus.vue'

interface Props {
  isConnected?: boolean
  connectionStatus?: WSConnectionState
  isOpponentTyping?: boolean
}

interface Emits {
  (e: 'reconnect'): void
  (e: 'end-chat'): void
  (e: 'mid-game'): void
}

const props = withDefaults(defineProps<Props>(), {
  isConnected: false,
  connectionStatus: 'disconnected',
  isOpponentTyping: false
})

const emit = defineEmits<Emits>()
const gameStore = useGameStore()

// 计算属性
const turn = computed(() => gameStore.gameState.turn)
const metaConversationCount = computed(() => gameStore.metaConversationCount)
const triggeredMidGame = computed(() => gameStore.triggeredMidGame)
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

/* 右侧区域 */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
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

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==============================================
   响应式设计
   ============================================== */

/* 正在输入提示 - Header 内 */
.typing-indicator-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--bg-secondary);
  border-radius: 16px;
  animation: fadeIn 0.3s ease-out;
}

.typing-dots {
  display: flex;
  gap: 3px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: typingBounce 1.4s ease-in-out infinite;
  animation-fill-mode: forwards;
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
    transform: translateY(-6px);
    opacity: 1;
  }
}

.typing-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-style: italic;
  white-space: nowrap;
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

  .header-right {
    justify-content: space-between;
    width: 100%;
  }

  /* 移动端：隐藏文字，仅保留动画点 */
  .typing-indicator-header .typing-text {
    display: none;
  }

  .typing-indicator-header {
    padding: 6px 10px;
    align-self: flex-start;
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
}
</style>
