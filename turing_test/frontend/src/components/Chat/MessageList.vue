<template>
  <div class="message-list">
    <!-- 自动滚动到底部 -->
    <div ref="scrollContainer" class="scroll-container">
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message-item', `message-${message.sender}`]"
        role="article"
        :aria-label="`${message.sender === 'user' ? '我' : '对手'}的消息`"
      >
        <!-- 系统消息 -->
        <div v-if="message.sender === 'system'" class="system-message">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ message.content }}</span>
        </div>

        <!-- 用户/对手消息 -->
        <div v-else class="message-bubble-wrapper">
          <!-- 头像和消息头部 -->
          <div class="message-header-row">
            <div 
              class="avatar" 
              :style="{ backgroundColor: getAvatarColor(message.sender) }"
            >
              {{ getInitials(message.sender === 'user' ? '我' : '对手') }}
            </div>
            
            <div class="message-header">
              <span class="sender-name">
                {{ message.sender === 'user' ? '我' : '对手' }}
              </span>
              <span class="message-time">{{ formatTime(message.timestamp) }}</span>
            </div>
          </div>

          <div
            :class="[
              'message-bubble',
              {
                'meta-conversation': message.isMetaConversation,
                'has-meta-tag': message.isMetaConversation
              }
            ]"
            @mouseenter="showTooltip = message.id"
            @mouseleave="showTooltip = null"
          >
            <div class="message-content">{{ message.content }}</div>

            <!-- 元对话标记 -->
            <div v-if="message.isMetaConversation" class="meta-tag">
              <el-icon><Warning /></el-icon>
              <span>元对话标记：{{ message.metaKeyword }}</span>
              <el-tooltip
                content="元对话会提高风险系数"
                placement="top"
                effect="light"
              >
                <el-icon class="info-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </div>
        </div>
      </div>

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
import {
  InfoFilled,
  Warning,
  QuestionFilled,
  ChatDotRound
} from '@element-plus/icons-vue'
import { stringToColor, getInitials } from '@/utils/formatters'
import type { MessageDisplay } from '@/types'

interface Props {
  messages: MessageDisplay[]
}

const props = defineProps<Props>()
const scrollContainer = ref<HTMLElement>()
const showTooltip = ref<number | null>(null)

// 获取头像颜色
function getAvatarColor(sender: string): string {
  return stringToColor(sender === 'user' ? 'user' : 'opponent')
}

// 格式化时间为相对时间
function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay} 天前`
}

// 自动滚动到底部
watch(() => props.messages, () => {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  }), { deep: true }
}, { immediate: true })
</script>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
  padding: 20px;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-primary);
}

.scroll-container {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding-right: 8px;
  scroll-behavior: smooth;
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

.message-item {
  display: flex;
  flex-direction: column;
  margin: 8px 0;
  animation: messageSlide 0.3s ease-out;
}

@keyframes messageSlide {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 用户消息 */
.message-user {
  align-items: flex-end;
}

/* 对手消息 */
.message-opponent {
  align-items: flex-start;
}

/* 系统消息 */
.system-message {
  align-self: center;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-primary-100);
  color: var(--color-primary);
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.1);
}

/* 消息气泡包装器 */
.message-bubble-wrapper {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 消息头部行（头像 + 信息） */
.message-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

/* 头像 */
.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--rounded-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: white;
  flex-shrink: 0;
  transition: background-color 0.3s ease;
}

/* 用户消息头像在右侧 */
.message-user .message-header-row {
  flex-direction: row-reverse;
}

/* 消息头部 */
.message-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
  opacity: 0.8;
}

.sender-name {
  font-weight: 600;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
}

.message-time {
  opacity: 0.6;
  font-size: 11px;
}

/* 消息气泡 */
.message-bubble {
  padding: 16px 20px;
  border-radius: 16px;
  position: relative;
  word-wrap: break-word;
  word-break: break-all;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}

.message-bubble:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.message-user .message-bubble {
  background: var(--color-primary-gradient);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-user .message-bubble:hover {
  background: linear-gradient(135deg, var(--color-purple-600) 0%, var(--color-purple-700) 100%);
}

.message-opponent .message-bubble {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  border-bottom-left-radius: 4px;
}

.message-opponent .message-bubble:hover {
  border-color: var(--border-secondary);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* 元对话样式 */
.message-bubble.meta-conversation {
  border: 2px solid var(--color-warning);
  box-shadow: 0 0 0 4px var(--color-warning-100);
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-warning);
  font-size: 12px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-warning-200);
  align-items: center;
}

.meta-tag .info-icon {
  font-size: 14px;
  cursor: help;
  opacity: 0.8;
  transition: opacity 0.2s ease;
}

.meta-tag .info-icon:hover {
  opacity: 1;
}

.message-user .meta-tag {
  color: var(--color-warning-200);
  border-top-color: rgba(255, 255, 255, 0.2);
}

.message-content {
  white-space: pre-wrap;
  line-height: 1.6;
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

/* 响应式设计 - 移动端（已在上面的媒体查询中处理） */
/* 这个样式块可以删除，因为我们已经在上面定义了更详细的响应式样式 */

/* 加载动画 */
.loading-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}

/* 响应式设计 - 超小屏 */
@media (max-width: 359px) {
  .message-list {
    padding: var(--spacing-sm);
    gap: var(--spacing-sm);
  }

  .message-bubble-wrapper {
    max-width: 90%;
  }

  .message-bubble {
    padding: var(--spacing-md) var(--spacing-lg);
    font-size: var(--text-sm);
  }

  .message-header {
    font-size: 10px;
    gap: var(--spacing-sm);
  }

  .sender-name {
    font-size: 11px;
  }

  .message-time {
    font-size: 10px;
  }

  .meta-tag {
    font-size: 10px;
    gap: var(--spacing-xs);
  }

  .scroll-container {
    max-height: calc(100vh - 140px);
  }
  
  .avatar {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }
}

/* 小屏 - 手机横屏 */
@media (max-width: 479px) {
  .message-list {
    padding: var(--spacing-md);
    gap: var(--spacing-sm);
  }

  .message-bubble-wrapper {
    max-width: 85%;
  }

  .message-bubble {
    padding: var(--spacing-md) var(--spacing-lg);
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

  .message-bubble-wrapper {
    max-width: 80%;
  }

  .message-bubble {
    padding: var(--spacing-lg) calc(var(--spacing-lg) * 1.25);
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

  .message-bubble-wrapper {
    max-width: 75%;
  }

  .message-bubble {
    padding: var(--spacing-lg) calc(var(--spacing-lg) * 1.5);
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

  .message-bubble-wrapper {
    max-width: 70%;
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
