<template>
  <div class="message-bubble-wrapper">
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
      @mouseenter="$emit('update:showTooltip', message.id)"
      @mouseleave="$emit('update:showTooltip', null)"
    >
      <div class="message-content" v-text="getSanitizedContent(message.content)"></div>

      <!-- 元对话标记 -->
      <div v-if="message.isMetaConversation" class="meta-tag">
        <el-icon><Warning /></el-icon>
        <span v-text="`元对话标记：${message.metaKeyword || '未知'}`"></span>
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
</template>

<script setup lang="ts">
import { Warning, QuestionFilled } from '@element-plus/icons-vue'
import { stringToColor, getInitials } from '@/utils/formatters'
import { sanitizeMessage } from '@/utils/validation'
import type { MessageDisplay } from '@/types'

interface Props {
  message: MessageDisplay
  showTooltip: number | null
}

defineProps<Props>()
defineEmits<{
  (e: 'update:showTooltip', value: number | null): void
}>()

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

// 清理后的消息内容（XSS 防护）
function getSanitizedContent(content: string): string {
  return sanitizeMessage(content)
}
</script>

<style scoped>
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
</style>
