<template>
  <div class="message-list">
    <!-- 自动滚动到底部 -->
    <div ref="scrollContainer" class="scroll-container">
      <MessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
        :show-tooltip="showTooltip"
        @update:show-tooltip="showTooltip = $event"
      />

      <!-- 空状态 -->
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-content">
          <div class="empty-icon">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <h3>对话已开始</h3>
          <p>发送第一条消息吧！</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import MessageItem from './MessageItem/index.vue'
import type { MessageDisplay } from '@/types'

interface Props {
  messages: MessageDisplay[]
}

const props = defineProps<Props>()
const scrollContainer = ref<HTMLElement>()
const showTooltip = ref<number | null>(null)

// 自动滚动到底部
watch(
  () => props.messages,
  () => {
    nextTick(() => {
      if (scrollContainer.value) {
        scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
      }
    })
  },
  { deep: true, immediate: true }
)
</script>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
  padding: 20px;
  background: var(--bg-surface);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-primary);
}

.scroll-container {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding-right: 8px;
  scroll-behavior: smooth;
}

/* 消息最小高度 - 防止内容跳跃 */
.message-item {
  min-height: 60px;
}

/* 自定义滚动条 */
.scroll-container::-webkit-scrollbar {
  width: 6px;
}

.scroll-container::-webkit-scrollbar-track {
  background: var(--bg-secondary);
  border-radius: 3px;
}

.scroll-container::-webkit-scrollbar-thumb {
  background: var(--color-gray-400);
  border-radius: 3px;
}

.scroll-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-gray-500);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  color: var(--text-tertiary);
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.empty-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-100);
  border-radius: var(--rounded-full);
  color: var(--color-primary);
  font-size: 40px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

.empty-content h3 {
  font-size: 20px;
  color: var(--text-primary);
  margin: 0;
}

.empty-content p {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

/* 响应式设计 - 超小屏 */
@media (max-width: 359px) {
  .message-list {
    padding: var(--spacing-sm);
    gap: var(--spacing-sm);
  }

  .scroll-container {
    max-height: calc(100vh - 140px);
  }
}

/* 小屏 - 手机横屏 */
@media (max-width: 479px) {
  .message-list {
    padding: var(--spacing-md);
    gap: var(--spacing-sm);
  }

  .scroll-container {
    max-height: calc(100vh - 160px);
  }
}

/* 中屏 - 小平板 */
@media (max-width: 639px) {
  .message-list {
    padding: var(--spacing-md);
    gap: var(--spacing-md);
  }

  .scroll-container {
    max-height: calc(100vh - 180px);
  }
}

/* 平板 - 竖屏平板 */
@media (max-width: 767px) {
  .message-list {
    padding: var(--spacing-lg);
    gap: var(--spacing-md);
  }

  .scroll-container {
    max-height: calc(100vh - 200px);
  }
}

/* 平板大屏 - 横屏平板 */
@media (max-width: 1023px) {
  .message-list {
    padding: var(--spacing-xl);
    gap: var(--spacing-lg);
  }

  .scroll-container {
    max-height: calc(100vh - 220px);
  }
}

/* 桌面端优化 */
@media (min-width: 1280px) {
  .scroll-container {
    max-height: calc(100vh - 250px);
  }
}

/* 大屏优化 */
@media (min-width: 1440px) {
  .scroll-container {
    max-height: calc(100vh - 280px);
  }
}

/* 4K 屏幕优化 */
@media (min-width: 1920px) {
  .scroll-container {
    max-height: calc(100vh - 320px);
  }
}
</style>
