<template>
  <div class="session-detail-page">
    <div class="header">
      <div class="header-left">
        <button class="back-btn" @click="$router.push('/history')">
          ← 返回列表
        </button>
        <h1>会话 #{{ session?.id }}</h1>
      </div>
      <div class="header-actions">
        <button v-if="!hasShare" class="btn btn-primary" @click="openShareDialog">
          创建分享
        </button>
        <button v-else class="btn btn-secondary" @click="openShareDialog">
          管理分享
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">加载中...</div>

    <!-- 错误提示 -->
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- 会话详情 -->
    <template v-else-if="session">
      <!-- 统计信息 -->
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-label">对手</span>
          <span class="stat-value">{{ session.opponent_type === 'human' ? '真人' : 'AI' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">轮数</span>
          <span class="stat-value">{{ session.turn_count }} 回合</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">元对话</span>
          <span class="stat-value">{{ session.meta_conversation_count }} 次</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">得分</span>
          <span class="stat-value score" :class="session.final_score && session.final_score > 0 ? 'positive' : 'negative'">
            {{ session.final_score !== null ? (session.final_score > 0 ? '+' : '') + session.final_score : '未结算' }}
          </span>
        </div>
        <div class="stat-item" v-if="session.is_correct !== null">
          <span class="stat-label">判断</span>
          <span class="stat-value" :class="session.is_correct ? 'correct-text' : 'incorrect-text'">
            {{ session.is_correct ? '正确 ✓' : '错误 ✗' }}
          </span>
        </div>
        <div class="stat-item" v-if="session.duration_seconds">
          <span class="stat-label">时长</span>
          <span class="stat-value">{{ formatDuration(session.duration_seconds) }}</span>
        </div>
      </div>

      <!-- 聊天记录 -->
      <div class="messages-container">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="message.sender === 'user' ? 'message-user' : 'message-opponent'"
        >
          <div class="message-sender">
            {{ message.sender === 'user' ? '你' : '对方' }}
            <span v-if="message.is_meta_conversation" class="meta-tag">元对话</span>
          </div>
          <div class="message-content">{{ message.content }}</div>
          <div class="message-time">{{ formatMessageTime(message.created_at) }}</div>
        </div>
      </div>
    </template>

    <!-- 分享对话框 -->
    <ShareDialog
      v-if="showShareDialog && sessionId"
      :session-id="sessionId"
      :existing-share="existingShare"
      @close="closeShareDialog"
      @share-created="handleShareCreated"
      @share-deleted="handleShareDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useHistoryStore } from '@/stores/history'
import ShareDialog from '@/components/History/ShareDialog.vue'

const route = useRoute()
const historyStore = useHistoryStore()

const sessionId = ref<number>(parseInt(route.params.id as string))

const loading = computed(() => historyStore.loading)
const error = computed(() => historyStore.error)
const session = computed(() => historyStore.currentSession)
const messages = computed(() => historyStore.currentMessages)
const hasShare = ref(false)
const existingShare = ref<any>(null)

const showShareDialog = ref(false)

// 格式化时长
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}分${secs}秒`
}

// 格式化消息时间
function formatMessageTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 打开分享对话框
function openShareDialog() {
  showShareDialog.value = true
}

// 关闭分享对话框
function closeShareDialog() {
  showShareDialog.value = false
}

// 分享创建成功
function handleShareCreated() {
  hasShare.value = true
  closeShareDialog()
}

// 分享删除成功
function handleShareDeleted() {
  hasShare.value = false
  closeShareDialog()
}

// 初始化
onMounted(async () => {
  await historyStore.fetchSessionDetail(sessionId.value)
  await historyStore.fetchSessionMessages(sessionId.value)
})
</script>

<style scoped>
.session-detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.back-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover {
  background: #f5f5f5;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

.loading, .error {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error {
  color: #dc3545;
}

.stats-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.score.positive {
  color: #28a745;
}

.score.negative {
  color: #dc3545;
}

.correct-text {
  color: #28a745;
}

.incorrect-text {
  color: #dc3545;
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.message {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message-user {
  align-self: flex-end;
  background: #007bff;
  color: white;
}

.message-opponent {
  align-self: flex-start;
  background: white;
  border: 1px solid #e0e0e0;
}

.message-sender {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}

.message-content {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 6px;
  text-align: right;
}
</style>
