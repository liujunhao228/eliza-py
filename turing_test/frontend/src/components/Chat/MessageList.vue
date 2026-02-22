<template>
  <div class="message-list">
    <div
      v-for="message in messages"
      :key="message.id"
      :class="['message-item', `message-${message.sender}`]"
    >
      <!-- 系统消息 -->
      <div v-if="message.sender === 'system'" class="system-message">
        <el-icon><InfoFilled /></el-icon>
        <span>{{ message.content }}</span>
      </div>

      <!-- 用户/对手消息 -->
      <div v-else class="message-bubble-wrapper">
        <div class="message-header">
          <span class="sender-name">
            {{ message.sender === 'user' ? '我' : '对手' }}
          </span>
          <span class="message-time">{{ formatTime(message.timestamp) }}</span>
        </div>

        <div :class="['message-bubble', { 'meta-conversation': message.isMetaConversation }]">
          <div class="message-content">{{ message.content }}</div>
          
          <!-- 元对话标记 -->
          <div v-if="message.isMetaConversation" class="meta-tag">
            <el-icon><Warning /></el-icon>
            <span>元对话: {{ message.metaKeyword }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="messages.length === 0" class="empty-state">
      <el-empty description="开始对话吧！"></el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { InfoFilled, Warning } from '@element-plus/icons-vue'
import type { MessageDisplay } from '@/types'

interface Props {
  messages: MessageDisplay[]
}

defineProps<Props>()

// 格式化时间
function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}
</script>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.message-item {
  display: flex;
  flex-direction: column;
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
  background: #f0f2f5;
  color: #606266;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  margin: 10px 0;
}

/* 消息气泡包装器 */
.message-bubble-wrapper {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 消息头部 */
.message-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.message-user .message-header {
  flex-direction: row-reverse;
}

.sender-name {
  font-weight: 500;
}

.message-time {
  opacity: 0.8;
}

/* 消息气泡 */
.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
  word-wrap: break-word;
  word-break: break-all;
  line-height: 1.6;
}

.message-user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-opponent .message-bubble {
  background: white;
  color: #303133;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
}

/* 元对话样式 */
.message-bubble.meta-conversation {
  border: 2px solid #f56c6c;
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #f56c6c;
  font-size: 12px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(245, 108, 108, 0.2);
}

.message-user .meta-tag {
  color: #ffe6e6;
  border-top-color: rgba(255, 255, 255, 0.2);
}

.message-content {
  white-space: pre-wrap;
}

/* 空状态 */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .message-bubble-wrapper {
    max-width: 85%;
  }

  .message-bubble {
    padding: 10px 14px;
  }

  .message-list {
    gap: 12px;
  }
}
</style>