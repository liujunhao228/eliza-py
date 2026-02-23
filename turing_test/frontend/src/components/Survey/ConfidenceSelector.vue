<template>
  <div class="confidence-selector">
    <label class="selector-label">
      <span class="label-text">请选择你的信心等级：</span>
      <span class="label-tip">（这将影响你的积分计算）</span>
    </label>

    <div class="confidence-options">
      <!-- 低信心 -->
      <div
        :class="['confidence-option', 'low', { selected: modelValue === 'low' }]"
        @click="selectConfidence('low')"
      >
        <div class="option-header">
          <el-icon class="option-icon"><CircleCheck /></el-icon>
          <span class="option-title">低信心</span>
        </div>
        <div class="option-description">
          <span class="multiplier">积分倍数 ×1.0</span>
          <p class="desc-text">不太确定，凭直觉判断</p>
        </div>
        <div class="option-scores">
          <span class="score-correct">正确 +10</span>
          <span class="score-wrong">错误 -15</span>
        </div>
      </div>

      <!-- 中信心 -->
      <div
        :class="['confidence-option', 'mid', { selected: modelValue === 'mid' }]"
        @click="selectConfidence('mid')"
      >
        <div class="option-header">
          <el-icon class="option-icon"><Star /></el-icon>
          <span class="option-title">中信心</span>
        </div>
        <div class="option-description">
          <span class="multiplier">积分倍数 ×2.5</span>
          <p class="desc-text">比较确定，有一定把握</p>
        </div>
        <div class="option-scores">
          <span class="score-correct">正确 +25</span>
          <span class="score-wrong">错误 -37</span>
        </div>
      </div>

      <!-- 高信心 -->
      <div
        :class="['confidence-option', 'high', { selected: modelValue === 'high' }]"
        @click="selectConfidence('high')"
      >
        <div class="option-header">
          <el-icon class="option-icon"><Trophy /></el-icon>
          <span class="option-title">高信心</span>
        </div>
        <div class="option-description">
          <span class="multiplier">积分倍数 ×5.0</span>
          <p class="desc-text">非常确定，有充分证据</p>
        </div>
        <div class="option-scores">
          <span class="score-correct">正确 +50</span>
          <span class="score-wrong">错误 -75</span>
        </div>
      </div>
    </div>

    <!-- 风险提示 -->
    <div class="risk-warning">
      <el-alert
        title="风险提示"
        type="warning"
        :closable="false"
        show-icon
      >
        <p>信心等级越高，积分波动越大！请谨慎选择。</p>
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleCheck, Star, Trophy } from '@element-plus/icons-vue'
import type { ConfidenceLevel } from '@/types'

interface Props {
  modelValue?: ConfidenceLevel | ''
}

interface Emits {
  (e: 'update:modelValue', value: ConfidenceLevel | ''): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: ''
})

const emit = defineEmits<Emits>()

// 选择信心等级
function selectConfidence(level: ConfidenceLevel) {
  emit('update:modelValue', level)
}
</script>

<style scoped>
.confidence-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selector-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.label-tip {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.confidence-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.confidence-option {
  position: relative;
  padding: 20px 16px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confidence-option:hover {
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.confidence-option.selected {
  border-color: #67c23a;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  box-shadow: 0 4px 16px rgba(103, 194, 58, 0.3);
}

/* 低信心配色 */
.confidence-option.low.selected {
  border-color: #909399;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  box-shadow: 0 4px 16px rgba(144, 147, 153, 0.3);
}

/* 中信心配色 */
.confidence-option.mid.selected {
  border-color: #409eff;
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
}

/* 高信心配色 */
.confidence-option.high.selected {
  border-color: #67c23a;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  box-shadow: 0 4px 16px rgba(103, 194, 58, 0.3);
}

.option-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-icon {
  font-size: 24px;
}

.confidence-option.low .option-icon {
  color: #909399;
}

.confidence-option.mid .option-icon {
  color: #409eff;
}

.confidence-option.high .option-icon {
  color: #67c23a;
}

.option-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.option-description {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.multiplier {
  font-size: 14px;
  font-weight: 600;
  color: #e6a23c;
}

.desc-text {
  font-size: 12px;
  color: #606266;
  margin: 0;
}

.option-scores {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px dashed #dcdfe6;
}

.score-correct {
  font-size: 14px;
  color: #67c23a;
  font-weight: 600;
}

.score-wrong {
  font-size: 14px;
  color: #f56c6c;
  font-weight: 600;
}

.risk-warning {
  margin-top: 8px;
}

.risk-warning :deep(.el-alert) {
  padding: 12px 16px;
}

.risk-warning :deep(.el-alert__content) {
  font-size: 13px;
}

.risk-warning :deep(.el-alert__title) {
  margin: 0;
}

.risk-warning :deep(p) {
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .confidence-options {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .confidence-options {
    grid-template-columns: 1fr;
  }

  .confidence-option {
    padding: 16px;
  }

  .selector-label {
    font-size: 14px;
  }

  .label-tip {
    font-size: 11px;
  }
}
</style>
