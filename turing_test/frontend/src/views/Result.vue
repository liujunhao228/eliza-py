<template>
  <div class="result-page">
    <div class="container">
      <div class="result-card">
        <h1 class="result-title">🎉 对话结束</h1>

        <!-- 真相揭晓 -->
        <TruthCard
          v-if="resultData"
          :opponent-type="resultData.opponentType"
          :is-correct="resultData.isCorrect"
        />

        <!-- 积分结果 -->
        <ScoreCard
          v-if="resultData"
          :final-score="resultData.finalScore"
          :is-correct="resultData.isCorrect"
        />

        <!-- 你的问卷回顾 -->
        <SurveyCard
          v-if="resultData"
          :data="resultData.surveyData"
        />

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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useGameStore } from '@/stores/game'
import { useToast } from '@/composables/useToast'
import { getSessionResult } from '@/api/game'
import {
  TruthCard,
  ScoreCard,
  SurveyCard
} from '@/components/Result'
import type { SurveyData } from '@/types/result'

const { error: showError } = useToast()
const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()

// 结果数据
const resultData = ref<{
  surveyData: SurveyData
  finalScore: number
  isCorrect: boolean
  opponentType: 'human' | 'ai' | 'honeypot' | 'unknown'
} | null>(null)

// 辅助函数：获取用户判断文本
function getUserGuessText(guess: string): string {
  const map: Record<string, string> = {
    human: '👤 真人',
    ai: '🤖 AI',
    unsure: '❓ 不确定'
  }
  return map[guess] || guess
}

// 辅助函数：获取信心等级文本
function getConfidenceText(level: string): string {
  const map: Record<string, string> = {
    low: '🟢 低信心',
    mid: '🟡 中信心',
    high: '🔴 高信心'
  }
  return map[level] || level
}

// 辅助函数：获取角色文本
function getSelfRoleText(role: string): string {
  const map: Record<string, string> = {
    prover: '🎯 证明者',
    interferer: '🎭 干扰者',
    other: '❓ 其他'
  }
  return map[role] || role
}

// 初始化数据
onMounted(async () => {
  // 优先从 gameStore 获取 sessionId
  const sessionId = gameStore.sessionId

  if (!sessionId) {
    showError('会话信息丢失，请重新开始')
    router.push({ name: 'Lobby' })
    return
  }

  try {
    // 从后端获取会话结果
    const result = await getSessionResult(sessionId)

    // 构建问卷数据
    const processedSurveyData: SurveyData = {
      user_guess: result.survey?.user_guess || 'unsure',
      confidence_level: result.survey?.confidence_level || 'low',
      fluency_rating: result.survey?.fluency_rating || 3,
      reason: result.survey?.reason || '',
      self_role: result.survey?.self_role || 'other',
      strategy: result.survey?.strategy || '',
      user_guess_text: getUserGuessText(result.survey?.user_guess || 'unsure'),
      confidence_level_text: getConfidenceText(result.survey?.confidence_level || 'low'),
      self_role_text: getSelfRoleText(result.survey?.self_role || 'other')
    }

    // 组装完整数据
    resultData.value = {
      surveyData: processedSurveyData,
      finalScore: result.final_score,
      isCorrect: result.is_correct,
      opponentType: result.opponent_type as 'human' | 'ai' | 'honeypot' | 'unknown'
    }

    // 更新用户积分
    userStore.updateScore(result.final_score)

  } catch (error) {
    console.error('获取会话结果失败:', error)
    showError('结果数据获取失败，请重新开始')
    router.push({ name: 'Lobby' })
  }
})

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
  background: var(--color-primary-gradient);
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
  background: var(--bg-surface);
  border-radius: var(--rounded-2xl);
  box-shadow: var(--shadow-2xl);
  padding: 40px;
}

.result-title {
  font-size: 32px;
  font-weight: bold;
  text-align: center;
  margin-bottom: 32px;
  color: var(--text-primary);
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
  border-radius: var(--rounded-md);
}

.action-button.secondary {
  background: var(--bg-surface);
  color: var(--color-primary-600);
  border: 2px solid var(--color-primary-600);
}

.action-button.secondary:hover {
  background: var(--color-primary-50);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .result-card {
    padding: 24px;
  }

  .result-title {
    font-size: 24px;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
