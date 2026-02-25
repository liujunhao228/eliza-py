<template>
  <div class="history-page">
    <div class="header">
      <h1>历史会话</h1>
      <button class="back-btn" @click="$router.push('/profile')">返回</button>
    </div>

    <!-- 过滤栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <label>对手类型：</label>
        <select v-model="filterOpponentType" @change="applyFilters">
          <option value="">全部</option>
          <option value="human">真人</option>
          <option value="ai">AI</option>
        </select>
      </div>

      <div class="filter-group">
        <label>判断结果：</label>
        <select v-model="filterResult" @change="applyFilters">
          <option value="">全部</option>
          <option :value="true">正确 ✓</option>
          <option :value="false">错误 ✗</option>
        </select>
      </div>

      <div class="filter-group">
        <label>每页显示：</label>
        <select v-model="pageSize" @change="changePageSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span>加载中...</span>
    </div>

    <!-- 错误提示 -->
    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <!-- 会话列表 -->
    <div v-else-if="sessions.length > 0" class="session-list">
      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-card"
        :class="{ 'correct': session.is_correct === true, 'incorrect': session.is_correct === false }"
      >
        <div class="session-header">
          <span class="session-id">会话 #{{ session.id }}</span>
          <span class="session-date">{{ formatDate(session.started_at) }}</span>
        </div>

        <div class="session-info">
          <div class="info-row">
            <span class="label">对手：</span>
            <span class="value opponent-type">{{ session.opponent_type === 'human' ? '真人' : 'AI' }}</span>
          </div>
          <div class="info-row">
            <span class="label">轮数：</span>
            <span class="value">{{ session.turn_count }} 回合</span>
          </div>
          <div class="info-row">
            <span class="label">得分：</span>
            <span class="value score" :class="session.final_score && session.final_score > 0 ? 'positive' : 'negative'">
              {{ session.final_score !== null ? (session.final_score > 0 ? '+' : '') + session.final_score : '-' }}
            </span>
          </div>
          <div class="info-row" v-if="session.is_correct !== null">
            <span class="label">判断：</span>
            <span class="value" :class="session.is_correct ? 'correct-text' : 'incorrect-text'">
              {{ session.is_correct ? '正确 ✓' : '错误 ✗' }}
            </span>
          </div>
          <div class="info-row" v-if="session.confidence_level">
            <span class="label">信心：</span>
            <span class="value confidence">{{ getConfidenceText(session.confidence_level) }}</span>
          </div>
        </div>

        <div class="session-actions">
          <button class="btn btn-primary" @click="viewSession(session.id)">查看</button>
          <button
            v-if="!session.has_share"
            class="btn btn-secondary"
            @click="openShareDialog(session.id)"
          >
            分享
          </button>
          <button
            v-else
            class="btn btn-secondary"
            @click="openShareDialog(session.id)"
          >
            管理分享
          </button>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="hasMore" class="pagination">
        <button
          class="btn btn-load-more"
          @click="loadMore"
          :disabled="loading"
        >
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>暂无历史会话</p>
      <button class="btn btn-primary" @click="$router.push('/lobby')">开始新对局</button>
    </div>

    <!-- 分享对话框 -->
    <ShareDialog
      v-if="showShareDialog"
      :session-id="selectedSessionId!"
      :existing-share="existingShare"
      @close="closeShareDialog"
      @share-created="handleShareCreated"
      @share-deleted="handleShareDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/history'
import { useUserStore } from '@/stores/user'
import ShareDialog from '@/components/History/ShareDialog.vue'

const router = useRouter()
const historyStore = useHistoryStore()
const userStore = useUserStore()

// 状态
const loading = computed(() => historyStore.loading)
const error = computed(() => historyStore.error)
const sessions = computed(() => historyStore.sessions)
const hasMore = computed(() => historyStore.hasMore)

// 过滤
const filterOpponentType = ref<string>('')
const filterResult = ref<string>('')
const pageSize = ref(20)

// 分享对话框
const showShareDialog = ref(false)
const selectedSessionId = ref<number | null>(null)
const existingShare = ref<any>(null)

// 格式化日期
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取信心等级文本
function getConfidenceText(level: string): string {
  const map: Record<string, string> = {
    low: '低',
    mid: '中',
    high: '高'
  }
  return map[level] || level
}

// 应用过滤
function applyFilters() {
  historyStore.fetchSessions(userStore.userId!, {
    opponent_type: filterOpponentType.value || undefined,
    is_correct: filterResult.value ? filterResult.value === 'true' : undefined
  })
}

// 改变每页大小
function changePageSize() {
  historyStore.pagination.page_size = pageSize.value
  historyStore.fetchSessions(userStore.userId!, {
    opponent_type: filterOpponentType.value || undefined,
    is_correct: filterResult.value ? filterResult.value === 'true' : undefined
  })
}

// 加载更多
function loadMore() {
  historyStore.loadMoreSessions(userStore.userId!)
}

// 查看会话
function viewSession(sessionId: number) {
  historyStore.fetchSessionDetail(sessionId)
  historyStore.fetchSessionMessages(sessionId)
  historyStore.fetchSessions(userStore.userId!)
  historyStore.fetchSessionDetail(sessionId).then(() => {
    historyStore.fetchSessionMessages(sessionId)
  })
  router.push(`/session/${sessionId}`)
}

// 打开分享对话框
function openShareDialog(sessionId: number) {
  selectedSessionId.value = sessionId
  const session = sessions.value.find(s => s.id === sessionId)
  existingShare.value = session?.has_share ? { sessionId } : null
  showShareDialog.value = true
}

// 关闭分享对话框
function closeShareDialog() {
  showShareDialog.value = false
  selectedSessionId.value = null
  existingShare.value = null
}

// 分享创建成功
function handleShareCreated() {
  // 刷新列表
  historyStore.fetchSessions(userStore.userId!)
  closeShareDialog()
}

// 分享删除成功
function handleShareDeleted() {
  // 刷新列表
  historyStore.fetchSessions(userStore.userId!)
  closeShareDialog()
}

// 初始化
onMounted(() => {
  if (userStore.userId) {
    historyStore.fetchSessions(userStore.userId)
  }
})
</script>

<style scoped>
.history-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
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

.filter-bar {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 8px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 14px;
  color: #666;
}

.filter-group select {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.loading, .error {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error {
  color: #dc3545;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.session-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
  transition: box-shadow 0.2s;
}

.session-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.session-card.correct {
  border-left: 4px solid #28a745;
}

.session-card.incorrect {
  border-left: 4px solid #dc3545;
}

.session-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.session-id {
  font-weight: 600;
  color: #333;
}

.session-date {
  font-size: 13px;
  color: #999;
}

.session-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin-bottom: 15px;
}

.info-row {
  display: flex;
  gap: 4px;
}

.info-row .label {
  color: #666;
  font-size: 13px;
}

.info-row .value {
  font-size: 13px;
  font-weight: 500;
}

.opponent-type {
  color: #007bff;
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

.confidence {
  color: #6c757d;
}

.session-actions {
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

.btn-load-more {
  width: 100%;
  padding: 12px;
  background: #f8f9fa;
  border: 1px solid #ddd;
  color: #333;
}

.btn-load-more:hover:not(:disabled) {
  background: #e9ecef;
}

.btn-load-more:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pagination {
  margin-top: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state p {
  margin-bottom: 20px;
}
</style>
