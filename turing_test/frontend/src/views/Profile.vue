<template>
  <div class="profile-container">
    <!-- 头部 -->
    <div class="profile-header">
      <h1>📊 我的战绩</h1>
      <BaseButton type="info" size="small" @click="handleLogout">
        🚪 退出登录
      </BaseButton>
    </div>

    <!-- 加载状态 -->
    <BaseLoading v-if="loading" :loading="true" text="加载中..." />

    <!-- 错误状态 -->
    <BaseEmpty
      v-else-if="error"
      :title="error"
      size="medium"
    >
      <template #action>
        <BaseButton type="primary" @click="loadData">重试</BaseButton>
      </template>
    </BaseEmpty>

    <!-- 主要内容 -->
    <div v-else class="profile-content">
      <!-- 用户信息卡片 -->
      <div class="user-info-card">
        <div class="user-avatar">
          <div class="avatar-placeholder">
            {{ userStore.nickname.charAt(0).toUpperCase() }}
          </div>
        </div>
        <div class="user-details">
          <h2>{{ userStore.nickname }}</h2>
          <p>邀请码：{{ userStore.inviteCode }}</p>
          <p>当前积分：<span class="current-score">{{ userStore.score }}</span></p>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-section">
        <!-- 对话统计 -->
        <div class="stats-card">
          <h3>📈 对话统计</h3>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-value">{{ stats?.total_sessions || 0 }}</span>
              <span class="stat-label">总对话数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatNumber(stats?.avg_turns || 0) }}</span>
              <span class="stat-label">平均轮数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatConfidence(stats) }}</span>
              <span class="stat-label">平均信心</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatNumber(stats?.avg_session_duration || 0) }}s</span>
              <span class="stat-label">平均时长</span>
            </div>
          </div>
        </div>

        <!-- 积分统计 -->
        <div class="stats-card">
          <h3>💰 积分统计</h3>
          <div class="stats-grid">
            <div class="stat-item highlight">
              <span class="stat-value">{{ userStore.score }}</span>
              <span class="stat-label">当前积分</span>
            </div>
            <div class="stat-item success">
              <span class="stat-value">{{ stats?.highest_score || 0 }}</span>
              <span class="stat-label">历史最高</span>
            </div>
            <div class="stat-item warning">
              <span class="stat-value">{{ stats?.lowest_score || 0 }}</span>
              <span class="stat-label">历史最低</span>
            </div>
          </div>
        </div>

        <!-- 准确率统计 -->
        <div class="stats-card">
          <h3>🎯 判断准确率</h3>
          <div class="stats-grid">
            <div class="stat-item success">
              <span class="stat-value">{{ formatPercent(stats?.accuracy || 0) }}</span>
              <span class="stat-label">整体准确率</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatPercent(stats?.accuracy_with_meta || 0) }}</span>
              <span class="stat-label">使用元对话</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatPercent(stats?.accuracy_without_meta || 0) }}</span>
              <span class="stat-label">未用元对话</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatPercent(stats?.mid_game_accuracy || 0) }}</span>
              <span class="stat-label">场中判断</span>
            </div>
          </div>
        </div>

        <!-- 元对话统计 -->
        <div class="stats-card">
          <h3>💬 元对话统计</h3>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-value">{{ stats?.total_meta_conversations || 0 }}</span>
              <span class="stat-label">总次数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatNumber(stats?.avg_meta_per_session || 0) }}</span>
              <span class="stat-label">平均每局</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ stats?.max_meta_in_one_session || 0 }}</span>
              <span class="stat-label">单局最高</span>
            </div>
          </div>
        </div>

        <!-- 对话类型分布 -->
        <div class="stats-card">
          <h3>🤖 对话类型分布</h3>
          <div class="type-distribution">
            <div class="type-item human">
              <span class="type-label">真人</span>
              <div class="type-bar">
                <div class="type-fill" :style="{ width: getPercentage(stats?.human_sessions || 0) + '%' }"></div>
              </div>
              <span class="type-count">{{ stats?.human_sessions || 0 }}</span>
            </div>
            <div class="type-item ai">
              <span class="type-label">AI</span>
              <div class="type-bar">
                <div class="type-fill" :style="{ width: getPercentage(stats?.ai_sessions || 0) + '%' }"></div>
              </div>
              <span class="type-count">{{ stats?.ai_sessions || 0 }}</span>
            </div>
          </div>
        </div>

        <!-- 信心等级分布 -->
        <div class="stats-card">
          <h3>🎚️ 信心等级分布</h3>
          <div class="confidence-distribution">
            <div class="confidence-item low">
              <span class="confidence-label">低信心</span>
              <div class="confidence-bar">
                <div class="confidence-fill" :style="{ width: getConfidencePercentage('low') + '%' }"></div>
              </div>
              <span class="confidence-count">{{ stats?.low_confidence_count || 0 }}</span>
            </div>
            <div class="confidence-item mid">
              <span class="confidence-label">中信心</span>
              <div class="confidence-bar">
                <div class="confidence-fill" :style="{ width: getConfidencePercentage('mid') + '%' }"></div>
              </div>
              <span class="confidence-count">{{ stats?.mid_confidence_count || 0 }}</span>
            </div>
            <div class="confidence-item high">
              <span class="confidence-label">高信心</span>
              <div class="confidence-bar">
                <div class="confidence-fill" :style="{ width: getConfidencePercentage('high') + '%' }"></div>
              </div>
              <span class="confidence-count">{{ stats?.high_confidence_count || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史记录 -->
      <div class="history-section">
        <h3>📜 对话历史</h3>

        <BaseEmpty
          v-if="!history || history.length === 0"
          title="还没有对话记录"
          size="small"
        >
          <template #action>
            <BaseButton type="primary" @click="goToLobby">开始第一局</BaseButton>
          </template>
        </BaseEmpty>

        <div v-else class="history-list">
          <div 
            v-for="session in history" 
            :key="session.id" 
            class="history-item"
            @click="viewSessionDetail(session)"
          >
            <div class="history-header">
              <span class="history-date">{{ formatDate(session.created_at) }}</span>
              <span class="history-type" :class="session.opponent_type">
                {{ getTypeLabel(session.opponent_type) }}
              </span>
            </div>
            <div class="history-info">
              <div class="history-stats">
                <span class="stat-badge">
                  📝 {{ session.meta_conversation_count || 0 }} 次元对话
                </span>
                <span class="stat-badge">
                  ⏱️ {{ formatDuration(session.match_duration) }}
                </span>
              </div>
              <div v-if="session.triggered_mid_game" class="mid-game-badge">
                ⚡ 场中判断
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 返回按钮 -->
      <div class="action-buttons">
        <BaseButton type="primary" size="large" @click="goToLobby">
          🚀 返回大厅
        </BaseButton>
      </div>
    </div>

    <!-- 详情对话框 -->
    <BaseModal
      v-model="showDetailModal"
      title="对话详情"
      size="medium"
      :show-footer="false"
    >
      <div class="detail-item">
        <span class="detail-label">对话时间：</span>
        <span>{{ formatDate(selectedSession?.created_at || '') }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">对手类型：</span>
        <span :class="selectedSession?.opponent_type">
          {{ getTypeLabel(selectedSession?.opponent_type || '') }}
        </span>
      </div>
      <div class="detail-item">
        <span class="detail-label">元对话次数：</span>
        <span>{{ selectedSession?.meta_conversation_count || 0 }} 次</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">对话时长：</span>
        <span>{{ formatDuration(selectedSession?.match_duration) }}</span>
      </div>
      <div v-if="selectedSession?.triggered_mid_game" class="detail-item">
        <span class="detail-label">场中判断：</span>
        <span>是</span>
      </div>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getUserFullProfile } from '@/api/profile'
import type { Session } from '@/types'
import { BaseButton, BaseLoading, BaseEmpty, BaseModal } from '@/components/common'

const router = useRouter()
const userStore = useUserStore()

// 状态
const loading = ref(true)
const error = ref('')
const stats = ref<any>(null)
const history = ref<Session[]>([])
const showDetailModal = ref(false)
const selectedSession = ref<Session | null>(null)

// 加载数据
const loadData = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const userId = userStore.userId
    if (!userId) {
      error.value = '用户未登录'
      loading.value = false
      return
    }

    const data = await getUserFullProfile(userId)
    stats.value = data.stats
    history.value = data.history
    userStore.setStats(data.stats)
    
    loading.value = false
  } catch (err: any) {
    console.error('加载用户数据失败:', err)
    error.value = err.response?.data?.detail || '加载失败，请重试'
    loading.value = false
  }
}

// 格式化数字
const formatNumber = (num: number): string => {
  if (num === null || num === undefined) return '0'
  return num.toFixed(1)
}

// 格式化百分比
const formatPercent = (num: number): string => {
  if (num === null || num === undefined) return '0%'
  return (num * 100).toFixed(1) + '%'
}

// 格式化日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化时长
const formatDuration = (seconds?: number): string => {
  if (!seconds) return '0秒'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}

// 格式化平均信心
const formatConfidence = (statsData: any): string => {
  if (!statsData) return '0%'
  const total = (statsData.low_confidence_count || 0) + 
                (statsData.mid_confidence_count || 0) + 
                (statsData.high_confidence_count || 0)
  if (total === 0) return '0%'
  
  const weightedSum = (statsData.low_confidence_count || 0) * 0.6 +
                       (statsData.mid_confidence_count || 0) * 0.8 +
                       (statsData.high_confidence_count || 0) * 0.95
  const avg = weightedSum / total
  return (avg * 100).toFixed(1) + '%'
}

// 获取类型标签
const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'human': '👤 真人',
    'ai': '🤖 AI',
    'honeypot': '🤖 AI' // 钓鱼机器人隐藏为 AI
  }
  return labels[type] || type
}

// 获取百分比
const getPercentage = (count: number): number => {
  const total = stats.value?.total_sessions || 0
  if (total === 0) return 0
  return (count / total) * 100
}

// 获取信心百分比
const getConfidencePercentage = (level: string): number => {
  const total = (stats.value?.low_confidence_count || 0) + 
                (stats.value?.mid_confidence_count || 0) + 
                (stats.value?.high_confidence_count || 0)
  if (total === 0) return 0
  
  const counts: Record<string, number> = {
    'low': stats.value?.low_confidence_count || 0,
    'mid': stats.value?.mid_confidence_count || 0,
    'high': stats.value?.high_confidence_count || 0
  }
  return ((counts[level] ?? 0) / total) * 100
}

// 查看对话详情
const viewSessionDetail = (session: Session) => {
  selectedSession.value = session
  showDetailModal.value = true
}

// 返回大厅
const goToLobby = () => {
  router.push('/lobby')
}

// 退出登录
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    userStore.logout()
    router.push('/login')
  }
}

// 生命周期
onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* ==============================================
   Profile.vue 样式 - 使用主题系统
   ============================================== */
.profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

/* 头部 */
.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.profile-header h1 {
  font-size: 28px;
  font-weight: bold;
  color: var(--text-primary);
  margin: 0;
}

/* 用户信息卡片 */
.user-info-card {
  display: flex;
  align-items: center;
  background: var(--color-primary-gradient);
  color: var(--bg-surface);
  padding: 30px;
  border-radius: var(--rounded-2xl);
  margin-bottom: 30px;
  box-shadow: var(--shadow-lg);
}

.user-avatar {
  margin-right: 20px;
}

.avatar-placeholder {
  width: 80px;
  height: 80px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: var(--rounded-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
}

.user-details h2 {
  margin: 0 0 10px 0;
  font-size: 24px;
}

.user-details p {
  margin: 5px 0;
  opacity: 0.9;
  font-size: 14px;
}

.current-score {
  font-size: 28px;
  font-weight: bold;
  margin-left: 10px;
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stats-card {
  background-color: var(--bg-surface);
  border-radius: var(--rounded-xl);
  padding: 20px;
  box-shadow: var(--shadow-md);
}

.stats-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-md);
}

.stat-item.highlight {
  background: var(--color-primary-gradient);
  color: var(--bg-surface);
}

.stat-item.highlight .stat-label {
  color: rgba(255, 255, 255, 0.9);
}

.stat-item.success {
  background-color: var(--color-primary-50);
  border: 1px solid var(--color-primary-100);
}

.stat-item.warning {
  background-color: var(--color-red-50);
  border: 1px solid var(--color-red-100);
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: var(--text-primary);
  margin-bottom: 5px;
}

.highlight .stat-value {
  color: var(--bg-surface);
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 类型分布 */
.type-distribution,
.confidence-distribution {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.type-item,
.confidence-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-label,
.confidence-label {
  min-width: 80px;
  font-size: 14px;
  color: var(--text-secondary);
}

.type-bar,
.confidence-bar {
  flex: 1;
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-sm);
  overflow: hidden;
}

.type-fill,
.confidence-fill {
  height: 100%;
  transition: width 0.3s;
}

.human .type-fill {
  background-color: var(--color-green-500);
}

.ai .type-fill {
  background-color: var(--color-primary-500);
}

.low .confidence-fill {
  background-color: var(--color-amber-500);
}

.mid .confidence-fill {
  background-color: var(--color-primary-500);
}

.high .confidence-fill {
  background-color: var(--color-green-500);
}

.type-count,
.confidence-count {
  min-width: 30px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 历史记录 */
.history-section {
  background-color: var(--bg-surface);
  border-radius: var(--rounded-xl);
  padding: 20px;
  box-shadow: var(--shadow-md);
  margin-bottom: 30px;
}

.history-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-history {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-tertiary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-container {
    padding: 15px;
  }

  .profile-header h1 {
    font-size: 22px;
  }

  .user-info-card {
    flex-direction: column;
    text-align: center;
  }

  .user-avatar {
    margin-right: 0;
    margin-bottom: 15px;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .history-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>