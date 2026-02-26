<template>
  <div class="survey-page">
    <div class="container">
      <div class="survey-card">
        <h1 class="survey-title">📝 对话结束</h1>
        <p class="survey-subtitle">请填写问卷，告诉我们你的想法</p>

        <el-form
          ref="surveyFormRef"
          :model="surveyForm"
          :rules="formRules"
          label-position="top"
          @submit.prevent="submitSurvey"
        >
          <!-- 身份判断 -->
          <el-form-item label="你认为对方是？" prop="user_guess" required>
            <el-radio-group v-model="surveyForm.user_guess" class="guess-options">
              <el-radio value="human" class="guess-radio">
                <span class="guess-icon">👤</span>
                <span class="guess-text">真人</span>
              </el-radio>
              <el-radio value="ai" class="guess-radio">
                <span class="guess-icon">🤖</span>
                <span class="guess-text">AI</span>
              </el-radio>
              <el-radio value="unsure" class="guess-radio">
                <span class="guess-icon">❓</span>
                <span class="guess-text">不确定</span>
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 信心等级 -->
          <el-form-item label="信心等级" prop="confidence_level" required>
            <ConfidenceSelector v-model="surveyForm.confidence_level" />
          </el-form-item>

          <!-- 流畅度评分 -->
          <el-form-item label="对话流畅度" prop="fluency_rating" required>
            <el-rate
              v-model="surveyForm.fluency_rating"
              :max="5"
              show-score
              :texts="['非常不流畅', '不流畅', '一般', '流畅', '非常流畅']"
              score-template="{value}"
              class="rating-stars"
            />
          </el-form-item>

          <!-- 判断理由 -->
          <el-form-item label="判断理由" prop="reason">
            <el-input
              v-model="surveyForm.reason"
              type="textarea"
              :rows="3"
              placeholder="你为什么做出这个判断？（选填）"
              maxlength="500"
              show-word-limit
              class="text-input"
            />
          </el-form-item>

          <!-- 自我角色 -->
          <el-form-item label="在本次对话中，你的角色是？" prop="self_role" required>
            <p class="hint-text">
              这是回顾你的实际行为，而非预设的目标。你可以在对话中自由切换策略。
            </p>
            <el-radio-group v-model="surveyForm.self_role" class="role-options">
              <el-radio value="prover" class="role-radio">
                <span class="role-icon">🎯</span>
                <span class="role-text">证明者（试图证明自己是真人）</span>
              </el-radio>
              <el-radio value="interferer" class="role-radio">
                <span class="role-icon">🎭</span>
                <span class="role-text">干扰者（试图模拟机器，骗过对方）</span>
              </el-radio>
              <el-radio value="other" class="role-radio">
                <span class="role-icon">❓</span>
                <span class="role-text">其他（不确定或没有特定角色，或在对话中切换了角色）</span>
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 策略描述 -->
          <el-form-item label="你使用了什么策略？" prop="strategy">
            <el-input
              v-model="surveyForm.strategy"
              type="textarea"
              :rows="2"
              placeholder="描述你使用的策略（可选）"
              maxlength="500"
              show-word-limit
              class="text-input"
            />
          </el-form-item>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="submitting"
              @click="submitSurvey"
              class="submit-button"
            >
              提交问卷
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { type FormInstance, type FormRules } from 'element-plus'
import { useGameStore } from '@/stores/game'
import { useToast } from '@/composables/useToast'
import type { SurveyData } from '@/types'
import { submitSurvey as submitSurveyAPI } from '@/api/survey'
import ConfidenceSelector from '@/components/Survey/ConfidenceSelector.vue'

const { showError, showSuccess, showWarning } = useToast()
const router = useRouter()
const gameStore = useGameStore()

// 表单引用
const surveyFormRef = ref<FormInstance>()

// 表单数据
const surveyForm = reactive<SurveyData>({
  user_guess: 'unsure',
  confidence_level: 'low',
  fluency_rating: 3,
  reason: '',
  self_role: 'other',
  strategy: ''
})

// 表单验证规则
const formRules: FormRules<SurveyData> = {
  user_guess: [
    { required: true, message: '请选择你的判断', trigger: 'change' }
  ],
  confidence_level: [
    { required: true, message: '请选择信心等级', trigger: 'change' }
  ],
  fluency_rating: [
    { required: true, message: '请评价对话流畅度', trigger: 'change' }
  ],
  self_role: [
    { required: true, message: '请选择你的角色', trigger: 'change' }
  ]
}

// 提交状态
const submitting = ref(false)

// 提交问卷
async function submitSurvey() {
  if (!surveyFormRef.value) return

  try {
    // 验证表单
    const valid = await surveyFormRef.value.validate()
    if (!valid) return

    submitting.value = true

    // 获取会话 ID
    const sessionId = gameStore.sessionId
    if (!sessionId) {
      showError('会话信息丢失，请重新开始')
      router.push({ name: 'Lobby' })
      return
    }

    // 提交问卷
    const result = await submitSurveyAPI(sessionId, surveyForm)

    // 保存结果到 localStorage（Result 页面需要）
    localStorage.setItem('surveyResult', JSON.stringify(result))
    localStorage.setItem('surveyData', JSON.stringify(surveyForm))

    showSuccess('问卷提交成功！')

    // 跳转到结果页
    router.push({ name: 'Result' })
  } catch (error) {
    console.error('提交问卷失败:', error)
    showError('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

// 页面加载时检查会话
onMounted(() => {
  if (!gameStore.sessionId) {
    showWarning('请先完成对话')
    router.push({ name: 'Lobby' })
  }
})
</script>

<style scoped>
/* ==============================================
   Survey 视图样式 - 使用主题系统
   ============================================== */

.survey-page {
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

.survey-card {
  background: var(--bg-surface);
  border-radius: var(--rounded-2xl);
  box-shadow: var(--shadow-2xl);
  padding: 40px;
  border: 1px solid var(--border-primary);
}

.survey-title {
  font-size: 32px;
  font-weight: bold;
  text-align: center;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.survey-subtitle {
  text-align: center;
  color: var(--text-secondary);
  margin-bottom: 40px;
  font-size: 16px;
}

/* 猜测选项 */
.guess-options {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.guess-radio {
  flex: 1;
  min-width: 120px;
  border: 2px solid var(--border-secondary);
  border-radius: var(--rounded-md);
  padding: 16px;
  transition: all 0.3s;
  cursor: pointer;
}

.guess-radio:hover {
  border-color: var(--color-primary-600);
  background-color: var(--bg-tertiary);
}

.guess-radio.is-checked {
  border-color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.guess-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 8px;
}

.guess-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 流畅度评分 */
.rating-stars {
  font-size: 32px;
}

/* 提示文本 */
.hint-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 12px;
  padding: 12px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-md);
  border-left: 4px solid var(--color-primary-600);
}

/* 角色选项 */
.role-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.role-radio {
  border: 2px solid var(--border-secondary);
  border-radius: var(--rounded-md);
  padding: 16px 20px;
  transition: all 0.3s;
  cursor: pointer;
  width: 100%;
}

.role-radio:hover {
  border-color: var(--color-primary-600);
  background-color: var(--bg-tertiary);
}

.role-radio.is-checked {
  border-color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.role-icon {
  font-size: 24px;
  margin-right: 12px;
  vertical-align: middle;
}

.role-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.5;
}

/* 文本输入框 */
.text-input :deep(.el-textarea__inner) {
  border-radius: var(--rounded-md);
  font-size: 15px;
  line-height: 1.6;
}

/* 提交按钮 */
.submit-button {
  width: 100%;
  height: 48px;
  font-size: 18px;
  font-weight: bold;
  border-radius: var(--rounded-md);
  background: var(--color-primary-gradient);
  border: none;
  color: white;
}

.submit-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.submit-button:active {
  transform: translateY(0);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .survey-card {
    padding: 24px;
  }

  .survey-title {
    font-size: 24px;
  }

  .survey-subtitle {
    font-size: 14px;
  }

  .guess-options {
    flex-direction: column;
  }

  .guess-radio {
    min-width: auto;
  }
}
</style>
