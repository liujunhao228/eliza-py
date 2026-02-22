<template>
  <div class="score-predictor">
    <h4>💰 积分预测（第 {{ turn }} 轮）</h4>
    
    <!-- 预测表格 -->
    <div class="prediction-table">
      <!-- 低信心 -->
      <div 
        class="prediction-row low"
        :class="{ 'recommended': optimalConfidence.level === '低信心' }"
      >
        <div class="confidence-label">
          <span class="confidence">低信心</span>
          <span class="multiplier">×1.0</span>
          <span v-if="optimalConfidence.level === '低信心'" class="badge">推荐</span>
        </div>
        <div class="score-values">
          <span class="correct">+{{ formattedPrediction.lowConfidence.correct }}</span>
          <span class="wrong">{{ formattedPrediction.lowConfidence.wrong }}</span>
        </div>
      </div>
      
      <!-- 中信心 -->
      <div 
        class="prediction-row mid"
        :class="{ 'recommended': optimalConfidence.level === '中信心' }"
      >
        <div class="confidence-label">
          <span class="confidence">中信心</span>
          <span class="multiplier">×2.5</span>
          <span v-if="optimalConfidence.level === '中信心'" class="badge">推荐</span>
        </div>
        <div class="score-values">
          <span class="correct">+{{ formattedPrediction.midConfidence.correct }}</span>
          <span class="wrong">{{ formattedPrediction.midConfidence.wrong }}</span>
        </div>
      </div>
      
      <!-- 高信心 -->
      <div 
        class="prediction-row high"
        :class="{ 'recommended': optimalConfidence.level === '高信心' }"
      >
        <div class="confidence-label">
          <span class="confidence">高信心</span>
          <span class="multiplier">×5.0</span>
          <span v-if="optimalConfidence.level === '高信心'" class="badge">推荐</span>
        </div>
        <div class="score-values">
          <span class="correct">+{{ formattedPrediction.highConfidence.correct }}</span>
          <span class="wrong">{{ formattedPrediction.highConfidence.wrong }}</span>
        </div>
      </div>
    </div>
    
    <!-- 扣除项目 -->
    <div class="penalty-info">
      <span>入场券: 2 分 | </span>
      <span>轮数惩罚: {{ formattedPrediction.turnPenalty }} 分</span>
    </div>
    
    <!-- 元对话影响 -->
    <div class="meta-info">
      <span>元对话次数: {{ metaCount }} | </span>
      <span>元对话倍数: ×{{ formattedPrediction.metaMultiplier }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'
import { useScorePrediction } from '@/composables/useScorePrediction'

const gameStore = useGameStore()
const {
  formattedPrediction,
  optimalConfidence
} = useScorePrediction()

const turn = computed(() => gameStore.turn)
const metaCount = computed(() => gameStore.metaConversationCount)
</script>

<style scoped>
.score-predictor {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.score-predictor h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
}

.prediction-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.prediction-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 12px;
  border-radius: 8px;
  border: 2px solid #e0e0e0;
  transition: all 0.3s;
}

.prediction-row:hover {
  border-color: #667eea;
  transform: translateX(4px);
}

.prediction-row.recommended {
  border-color: #67c23a;
  background: #f0f9ff;
}

.confidence-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.confidence {
  font-weight: 600;
  font-size: 14px;
}

.multiplier {
  font-size: 12px;
  color: #666;
}

.badge {
  align-self: flex-start;
  background: #67c23a;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.score-values {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  text-align: right;
}

.correct {
  color: #67c23a;
  font-weight: 600;
  font-size: 18px;
}

.wrong {
  color: #f56c6c;
  font-size: 16px;
}

.penalty-info, .meta-info {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding-top: 8px;
  border-top: 1px solid #e0e0e0;
}

.meta-info {
  border-top: none;
  padding-top: 4px;
}
</style>