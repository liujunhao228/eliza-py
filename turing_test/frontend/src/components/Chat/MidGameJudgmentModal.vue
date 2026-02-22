<template>
  <el-dialog
    v-model="dialogVisible"
    title="场中判断"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <div class="mid-game-content">
      <!-- 说明文字 -->
      <div class="description">
        <el-alert
          title="场中判断机会"
          type="info"
          :closable="false"
          show-icon
        >
          <p>你现在可以进行场中判断！</p>
          <p class="highlight">双倍奖励，双倍风险</p>
        </el-alert>
      </div>

      <!-- 规则说明 -->
      <div class="rules-section">
        <h4>规则说明：</h4>
        <ul>
          <li>✅ <strong>判断正确</strong>：获得双倍积分奖励</li>
          <li>❌ <strong>判断错误</strong>：扣除双倍积分惩罚</li>
          <li>⚠️ <strong>风险提示</strong>：元对话次数会增加惩罚倍数</li>
        </ul>
      </div>

      <!-- 积分预测 -->
      <div class="prediction-section">
        <h4>积分预测：</h4>
        <div class="prediction-grid">
          <div class="prediction-card correct">
            <div class="card-icon">✓</div>
            <div class="card-label">判断正确</div>
            <div class="card-value positive">+{{ Math.round(potentialReward) }}</div>
          </div>
          <div class="prediction-card wrong">
            <div class="card-icon">✗</div>
            <div class="card-label">判断错误</div>
            <div class="card-value negative">-{{ Math.round(potentialPenalty) }}</div>
          </div>
        </div>
      </div>

      <!-- 选择按钮 -->
      <div class="choice-section">
        <h4>请选择：</h4>
        <div class="choice-buttons">
          <el-button
            type="success"
            size="large"
            :loading="isSubmitting"
            @click="handleChoice('human')"
          >
            <template #icon>
              <el-icon><User /></el-icon>
            </template>
            我认为是人类
          </el-button>
          
          <el-button
            type="danger"
            size="large"
            :loading="isSubmitting"
            @click="handleChoice('ai')"
          >
            <template #icon>
              <el-icon><Monitor /></el-icon>
            </template>
            我认为是AI
          </el-button>
        </div>
      </div>

      <!-- 取消按钮 -->
      <div class="cancel-section">
        <el-button
          text
          type="info"
          @click="handleCancel"
        >
          暂不判断，继续对话
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { User, Monitor } from '@element-plus/icons-vue'
import { useGameStore } from '@/stores/game'

interface Emits {
  (e: 'confirm', choice: 'human' | 'ai'): void
  (e: 'cancel'): void
}

const emit = defineEmits<Emits>()
const gameStore = useGameStore()

const dialogVisible = ref(true)
const isSubmitting = ref(false)

// 计算潜在奖励和惩罚
const potentialReward = computed(() => {
  if (!gameStore.currentScorePrediction) return 0
  // 场中判断双倍奖励
  const baseReward = Math.max(
    gameStore.currentScorePrediction.highConfidence.correct,
    gameStore.currentScorePrediction.midConfidence.correct
  )
  return baseReward * 2
})

const potentialPenalty = computed(() => {
  if (!gameStore.currentScorePrediction) return 0
  // 场中判断双倍惩罚
  const basePenalty = Math.max(
    Math.abs(gameStore.currentScorePrediction.highConfidence.wrong),
    Math.abs(gameStore.currentScorePrediction.midConfidence.wrong)
  )
  return basePenalty * 2
})

// 处理选择
function handleChoice(choice: 'human' | 'ai') {
  isSubmitting.value = true
  emit('confirm', choice)
}

// 处理取消
function handleCancel() {
  dialogVisible.value = false
  emit('cancel')
}
</script>

<style scoped>
.mid-game-content {
  padding: 20px 0;
}

.description {
  margin-bottom: 24px;
}

.description .highlight {
  font-weight: bold;
  color: #f56c6c;
  font-size: 16px;
  margin: 8px 0;
}

.rules-section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.rules-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
}

.rules-section ul {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.rules-section li {
  margin: 8px 0;
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

.prediction-section {
  margin-bottom: 24px;
}

.prediction-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
}

.prediction-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.prediction-card {
  padding: 16px;
  border-radius: 8px;
  text-align: center;
  transition: all 0.3s;
}

.prediction-card.correct {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
}

.prediction-card.wrong {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid #fecaca;
}

.card-icon {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.card-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: bold;
}

.card-value.positive {
  color: #67c23a;
}

.card-value.negative {
  color: #f56c6c;
}

.choice-section {
  margin-bottom: 24px;
}

.choice-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
}

.choice-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.choice-buttons :deep(.el-button) {
  height: 60px;
  font-size: 16px;
}

.cancel-section {
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .prediction-grid {
    grid-template-columns: 1fr;
  }

  .choice-buttons {
    grid-template-columns: 1fr;
  }
}
</style>