<template>
  <div class="result-page">
    <div class="container">
      <div class="result-card">
        <h1 class="result-title">🎉 对话结束</h1>
        
        <!-- 真相揭晓 -->
        <div class="truth-section">
          <h2 class="section-title">真相揭晓</h2>
          <div class="truth-content">
            <div class="opponent-info">
              <div class="opponent-avatar" :class="opponentTypeClass">
                {{ opponentAvatar }}
              </div>
              <div class="opponent-details">
                <div class="opponent-type">
                  <span class="type-label">对方身份：</span>
                  <span class="type-value" :class="opponentTypeClass">
                    {{ opponentTypeText }}
                  </span>
                </div>
                <div class="result-badge" :class="resultBadgeClass">
                  {{ resultBadgeText }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 积分明细 -->
        <div class="score-section">
          <h2 class="section-title">积分明细</h2>
          <div class="score-card">
            <div class="score-main">
              <div class="score-change" :class="scoreChangeClass">
                <span class="change-sign">{{ scoreChange > 0 ? '+' : '' }}</span>
                <span class="change-value">{{ scoreChange }}</span>
              </div>
              <div class="score-total">
                当前积分：<span class="total-value">{{ userScore }}</span>
              </div>
            </div>
            
            <div class="score-details">
              <div class="detail-item">
                <span class="detail-label">基础奖励：</span>
                <span class="detail-value">{{ scoreBreakdown.base_reward }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">信心倍数：</span>
                <span class="detail-value">{{ scoreBreakdown.confidence_multiplier }}×</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">元对话倍数：</span>
                <span class="detail-value">{{ scoreBreakdown.meta_multiplier }}×</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">有效倍数：</span>
                <span class="detail-value">{{ scoreBreakdown.effective_multiplier }}×</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">入场券：</span>
                <span class="detail-value">-{{ scoreBreakdown.entry_fee }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">轮数惩罚：</span>
                <span class="detail-value">{{ scoreBreakdown.turn_penalty > 0 ? '-' : '' }}{{ scoreBreakdown.turn_penalty }}</span>
              </div>
              <div class="detail-item total">
                <span class="detail-label">最终得分：</span>
                <span class="detail-value">{{ scoreBreakdown.final_score }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 对方判断（彩蛋） -->
        <div class="opinion-section" v-if="opinionData">
          <h2 class="section-title">对方的判断</h2>
          <div class="opinion-card">
            <div class="opinion-guess">
              <span class="guess-label">对方认为你是：</span>
              <span class="guess-value" :class="opinionGuessClass">
                {{ opinionGuessText }}
              </span>
            </div>
            <div class="opinion-reason" v-if="opinionData.reason">
              <span class="reason-label">理由：</span>
              <span class="reason-value">{{ opinionData.reason }}</span>
            </div>
          </div>
        </div>

        <!-- 你的问卷回顾 -->
        <div class="survey-section">
          <h2 class="section-title">你的判断回顾</h2>
          <div class="survey-card">
            <div class="survey-item">
              <span class="survey-label">你的判断：</span>
              <span class="survey-value">{{ surveyData.user_guess_text }}</span>
            </div>
            <div class="survey-item">
              <span class="survey-label">信心等级：</span>
              <span class="survey-value">{{ surveyData.confidence_level_text }}</span>
            </div>
            <div class="survey-item">
              <span class="survey-label">流畅度评分：</span>
              <span class="survey-value">{{ surveyData.fluency_rating }}/5</span>
            </div>
            <div class="survey-item" v-if="surveyData.reason">
              <span class="survey-label">理由：</span>
              <span class="survey-value">{{ surveyData.reason }}</span>
            </div>
            <div class="survey-item">
              <span class="survey-label">你的角色：</span>
              <span class="survey-value">{{ surveyData.self_role_text }}</span>
            </div>
            <div class="survey-item" v-if="surveyData.strategy">
              <span class="survey-label">策略：</span>
              <span class="survey-value">{{ surveyData.strategy }}</span>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="actions">
          <el-button 
            type="primary" 
            size="large" 
            @click="backToLobby"
            class="action-button"
          >
            返回大厅
          </el-button>
          <el-button 
            size="large" 
            @click="viewHistory"
            class="action-button secondary"
          >
            查看历史
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 从localStorage获取数据
const surveyData = ref<any>(null)
const opinionData = ref<any>(null)
const scoreBreakdown = ref<any>(null)
const userScore = ref(0)

// 计算属性
const opponentType = computed(() => {
  return scoreBreakdown.value?.opponent_type || 'unknown'
})

const opponentTypeClass = computed(() => {
  return `opponent-${opponentType.value}`
})

const opponentTypeText = computed(() => {
  const map: Record<string, string> = {
    'human': '👤 真人',
    'ai': '🤖 AI',
    'honeypot': '🎣 钓鱼机器人'
  }
  return map[opponentType.value] || '未知'
})

const opponentAvatar = computed(() => {
  const map: Record<string, string> = {
    'human': '👤',
    'ai': '🤖',
    'honeypot': '🎣'
  }
  return map[opponentType.value] || '❓'
})

const isCorrect = computed(() => {
  return scoreBreakdown.value?.is_correct || false
})

const resultBadgeClass = computed(() => {
  return isCorrect.value ? 'badge-correct' : 'badge-wrong'
})

const resultBadgeText = computed(() => {
  return isCorrect.value ? '判断正确！' : '判断错误'
})

const scoreChange = computed(() => {
  return scoreBreakdown.value?.final_score || 0
})

const scoreChangeClass = computed(() => {
  return scoreChange.value >= 0 ? 'score-positive' : 'score-negative'
})

const opinionGuessClass = computed(() => {
  if (!opinionData.value?.opponent_guess) return ''
  const guessMap: Record<string, string> = {
    'human': 'opponent-human',
    'ai': 'opponent-ai',
    'honeypot': 'opponent-honeypot'
  }
  return guessMap[opinionData.value.opponent_guess] || ''
})

const opinionGuessText = computed(() => {
  if (!opinionData.value?.opponent_guess) return '未知'
  const map: Record<string, string> = {
    'human': '👤 真人',
    'ai': '🤖 AI',
    'honeypot': '🎣 钓鱼机器人'
  }
  return map[opinionData.value.opponent_guess] || '未知'
})

// 初始化数据
onMounted(() => {
  // 从localStorage获取问卷结果
  const surveyResult = localStorage.getItem('surveyResult')
  const surveyDataLocal = localStorage.getItem('surveyData')
  
  if (!surveyResult || !surveyDataLocal) {
    ElMessage.error('结果数据丢失，请重新开始')
    router.push({ name: 'Lobby' })
    return
  }
  
  try {
    const surveyResponse = JSON.parse(surveyResult)
    const survey = JSON.parse(surveyDataLocal)
    
    // 处理问卷数据文本
    surveyData.value = {
      ...survey,
      user_guess_text: getUserGuessText(survey.user_guess),
      confidence_level_text: getConfidenceText(survey.confidence_level),
      self_role_text: getSelfRoleText(survey.self_role)
    }
    
    // 处理对方判断数据
    if (surveyResponse.opponent_guess) {
      opinionData.value = {
        opponent_guess: surveyResponse.opponent_guess,
        reason: surveyResponse.opponent_reason
      }
    }
    
    // 积分明细
    scoreBreakdown.value = surveyResponse.score_breakdown
    
    // 更新用户积分
    userScore.value = surveyResponse.final_score
    
    // 更新store中的积分
    userStore.updateScore(surveyResponse.final_score)
    
    // 清除localStorage数据
    localStorage.removeItem('surveyResult')
    localStorage.removeItem('surveyData')
    
  } catch (error) {
    console.error('解析结果数据失败:', error)
    ElMessage.error('结果数据解析失败，请重新开始')
    router.push({ name: 'Lobby' })
  }
})

// 辅助函数
function getUserGuessText(guess: string): string {
  const map: Record<string, string> = {
    'human': '👤 真人',
    'ai': '🤖 AI',
    'unsure': '❓ 不确定'
  }
  return map[guess] || guess
}

function getConfidenceText(level: string): string {
  const map: Record<string, string> = {
    'low': '🟢 低信心',
    'mid': '🟡 中信心',
    'high': '🔴 高信心'
  }
  return map[level] || level
}

function getSelfRoleText(role: string): string {
  const map: Record<string, string> = {
    'prover': '🎯 证明者',
    'interferer': '🎭 干扰者',
    'other': '❓ 其他'
  }
  return map[role] || role
}

// 操作函数
function backToLobby() {
  router.push({ name: 'Lobby' })
}

function viewHistory() {
  router.push({ name: 'Profile' })
}
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.container {
  width: 100%;
  max-width: 800px;
}

.result-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  padding: 40px;
}

.result-title {
  font-size: 32px;
  font-weight: bold;
  text-align: center;
  margin-bottom: 32px;
  color: #333;
}

.section-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 16px;
  color: #333;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 8px;
}

/* 真相揭晓 */
.truth-section {
  margin-bottom: 32px;
}

.opponent-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.opponent-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  background: #f5f5f5;
  border: 3px solid #e0e0e0;
}

.opponent-avatar.opponent-human {
  background: #e8f5e9;
  border-color: #4caf50;
  color: #2e7d32;
}

.opponent-avatar.opponent-ai {
  background: #e3f2fd;
  border-color: #2196f3;
  color: #1565c0;
}

.opponent-avatar.opponent-honeypot {
  background: #fff3e0;
  border-color: #ff9800;
  color: #e65100;
}

.opponent-details {
  flex: 1;
}

.opponent-type {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 8px;
}

.type-label {
  color: #666;
}

.type-value {
  font-weight: bold;
}

.type-value.opponent-human {
  color: #2e7d32;
}

.type-value.opponent-ai {
  color: #1565c0;
}

.type-value.opponent-honeypot {
  color: #e65100;
}

.result-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 14px;
}

.result-badge.badge-correct {
  background: #e8f5e9;
  color: #2e7d32;
}

.result-badge.badge-wrong {
  background: #ffebee;
  color: #c62828;
}

/* 积分明细 */
.score-section {
  margin-bottom: 32px;
}

.score-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e9ecef;
}

.score-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e9ecef;
}

.score-change {
  font-size: 28px;
  font-weight: bold;
}

.score-change .change-sign {
  font-size: 20px;
}

.score-change .change-value {
  font-size: 32px;
}

.score-change.score-positive {
  color: #2e7d32;
}

.score-change.score-negative {
  color: #c62828;
}

.score-total {
  font-size: 16px;
  color: #666;
}

.score-total .total-value {
  font-weight: bold;
  color: #333;
  font-size: 18px;
}

.score-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item.total {
  border-top: 2px solid #333;
  border-bottom: none;
  padding-top: 12px;
  margin-top: 8px;
  font-weight: bold;
}

.detail-label {
  color: #666;
  font-size: 14px;
}

.detail-value {
  font-weight: 500;
  color: #333;
}

/* 对方判断 */
.opinion-section {
  margin-bottom: 32px;
}

.opinion-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e9ecef;
}

.opinion-guess {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.guess-label {
  color: #666;
  font-weight: 500;
}

.guess-value {
  font-weight: bold;
}

.guess-value.opponent-human {
  color: #2e7d32;
}

.guess-value.opponent-ai {
  color: #1565c0;
}

.guess-value.opponent-honeypot {
  color: #e65100;
}

.opinion-reason {
  padding-left: 12px;
}

.reason-label {
  color: #666;
  font-weight: 500;
  margin-right: 8px;
}

.reason-value {
  color: #333;
  line-height: 1.5;
}

/* 问卷回顾 */
.survey-section {
  margin-bottom: 32px;
}

.survey-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e9ecef;
}

.survey-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.survey-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.survey-label {
  color: #666;
  font-weight: 500;
  min-width: 100px;
}

.survey-value {
  color: #333;
  flex: 1;
  line-height: 1.5;
}

/* 操作按钮 */
.actions {
  display: flex;
  gap: 16px;
  margin-top: 32px;
}

.action-button {
  flex: 1;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
}

.action-button.secondary {
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
}

.action-button.secondary:hover {
  background: #f0f4ff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .result-card {
    padding: 24px;
  }

  .result-title {
    font-size: 24px;
  }

  .section-title {
    font-size: 20px;
  }

  .opponent-info {
    flex-direction: column;
    text-align: center;
  }

  .score-details {
    grid-template-columns: 1fr;
  }

  .actions {
    flex-direction: column;
  }
}
</style>