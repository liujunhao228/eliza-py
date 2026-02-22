<template>
  <div class="profile-container">
    <!-- 头部 -->
    <div class="profile-header">
      <h1>📊 我的战绩</h1>
      <button @click="handleLogout" class="btn-logout">
        🚪 退出登录
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="loadData" class="btn btn-primary">重试</button>
    </div>

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
            <div class="type-item honeypot">
              <span class="type-label">钓鱼机器人</span>
              <div class="type-bar">
                <div class="type-fill" :style="{ width: getPercentage(stats?.honeypot_sessions || 0) + '%' }"></div>
              </div>
              <span class="type-count">{{ stats?.honeypot_sessions || 0 }}</span>
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
        
        <div v-if="!history || history.length === 0" class="empty-history">
          <p>还没有对话记录</p>
          <button @click="goToLobby" class="btn btn-primary">开始第一局</button>
        </div>

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
        <button @click="goToLobby" class="btn btn-primary btn-large">
          🚀 返回大厅
        </button>
      </div>
    </div>

    <!-- 详情对话框 -->
    <div v-if="showDetailModal" class="modal-overlay" @click="closeDetailModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>对话详情</h3>
          <button @click="closeDetailModal" class="btn-close">×</button>
        </div>
        <div class="modal-body">
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getUserFullProfile } from '@/api/profile'
import type { Session } from '@/types'

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
    'honeypot': '🎣 钓鱼机器人'
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

// 关闭详情对话框
const closeDetailModal = () => {
  showDetailModal.value = false
  selectedSession.value = null
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
  color: #333;
  margin: 0;
}

.btn-logout {
  padding: 10px 20px;
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.3s;
}

.btn-logout:hover {
  background-color: #e0e0e0;
  color: #333;
}

/* 加载状态 */
.loading-state,
.error-state {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  color: #f56c6c;
}

/* 用户信息卡片 */
.user-info-card {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 16px;
  margin-bottom: 30px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.user-avatar {
  margin-right: 20px;
}

.avatar-placeholder {
  width: 80px;
  height: 80px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
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
  background-color: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stats-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.stat-item.highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stat-item.highlight .stat-label {
  color: rgba(255, 255, 255, 0.9);
}

.stat-item.success {
  background-color: #f0f9ff;
  border: 1px solid #e0f2fe;
}

.stat-item.warning {
  background-color: #fef2f2;
  border: 1px solid #fee2e2;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.highlight .stat-value {
  color: white;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #666;
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
  color: #666;
}

.type-bar,
.confidence-bar {
  flex: 1;
  height: 8px;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.type-fill,
.confidence-fill {
  height: 100%;
  transition: width 0.3s;
}

.human .type-fill {
  background-color: #4caf50;
}

.ai .type-fill {
  background-color: #2196f3;
}

.honeypot .type-fill {
  background-color: #f44336;
}

.low .confidence-fill {
  background-color: #ff9800;
}

.mid .confidence-fill {
  background-color: #2196f3;
}

.high .confidence-fill {
  background-color: #4caf50;
}

.type-count,
.confidence-count {
  min-width: 30px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

/* 历史记录 */
.history-section {
  background-color: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 30px;
}

.history-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.empty-history {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-item {
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background-color: #e9ecef;
  transform: translateX(5px);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.history-date {
  font-size: 14px;
  color: #666;
}

.history-type {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.history-type.human {
  background-color: #e8f5e9;
  color: #4caf50;
}

.history-type.ai {
  background-color: #e3f2fd;
  color: #2196f3;
}

.history-type.honeypot {
  background-color: #ffebee;
  color: #f44336;
}

.history-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-stats {
  display: flex;
  gap: 10px;
}

.stat-badge {
  padding: 4px 8px;
  background-color: white;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.mid-game-badge {
  padding: 4px 8px;
  background-color: #fff3e0;
  border-radius: 4px;
  font-size: 12px;
  color: #ff9800;
  font-weight: 500;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  justify-content: center;
  gap: 15px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background-color: #409eff;
  color: white;
}

.btn-primary:hover {
  background-color: #66b1ff;
}

.btn-large {
  padding: 15px 40px;
  font-size: 18px;
}

.btn-secondary {
  background-color: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
}

.btn-secondary:hover {
  background-color: #e0e0e0;
  color: #333;
}

/* 详情对话框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 12px;
  padding: 30px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: #333;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-label {
  font-weight: 500;
  color: #666;
}

.detail-item span:last-child {
  font-weight: 600;
  color: #333;
}

.human {
  color: #4caf50;
}

.ai {
  color: #2196f3;
}

.honeypot {
  color: #f44336;
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