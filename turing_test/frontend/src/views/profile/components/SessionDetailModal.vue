<template>
  <BaseModal
    :model-value="modelValue"
    title="对话详情"
    size="medium"
    :show-footer="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="session" class="detail-content">
      <div class="detail-item">
        <span class="detail-label">对话时间：</span>
        <span>{{ formatDate(session.started_at) }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">对手类型：</span>
        <span :class="getTypeClass(session.opponent_type)">
          {{ getTypeLabel(session.opponent_type) }}
        </span>
      </div>
      <div class="detail-item">
        <span class="detail-label">回合数：</span>
        <span>{{ session.turn_count || 0 }} 回合</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">元对话次数：</span>
        <span>{{ session.meta_conversation_count || 0 }} 次</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">对话时长：</span>
        <span>{{ formatDuration(duration) }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">最终得分：</span>
        <span :class="getScoreClass(session.final_score)">
          {{ formatScore(session.final_score) }}
        </span>
      </div>
      <div v-if="session.is_correct !== null" class="detail-item">
        <span class="detail-label">判断结果：</span>
        <span :class="getCorrectClass(session.is_correct)">
          {{ session.is_correct ? '正确 ✓' : '错误 ✗' }}
        </span>
      </div>
      <div v-if="session.confidence_level" class="detail-item">
        <span class="detail-label">信心等级：</span>
        <span>{{ getConfidenceLabel(session.confidence_level) }}</span>
      </div>
      <div v-if="session.triggered_mid_game" class="detail-item">
        <span class="detail-label">场中判断：</span>
        <span class="highlight">是</span>
      </div>
    </div>
    <div v-else class="empty-tip">
      暂无会话详情
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BaseModal } from '@/components/common'
import { formatDate, getTypeLabel, getTypeClass, formatDuration } from '../utils/formatters'
import type { Session } from '@/types'

const props = defineProps<{
  modelValue: boolean
  session: Session | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

// 计算会话时长（秒）
const duration = computed(() => {
  if (!props.session?.started_at || !props.session?.ended_at) return 0
  const start = new Date(props.session.started_at).getTime()
  const end = new Date(props.session.ended_at).getTime()
  return Math.floor((end - start) / 1000)
})

// 格式化得分
const formatScore = (score?: number | null): string => {
  if (score === null || score === undefined) return '-'
  return score > 0 ? `+${score}` : `${score}`
}

// 得分样式
const getScoreClass = (score?: number | null): string => {
  if (score === null || score === undefined) return ''
  return score > 0 ? 'positive' : 'negative'
}

// 判断结果样式
const getCorrectClass = (isCorrect?: boolean | null): string => {
  if (isCorrect === null || isCorrect === undefined) return ''
  return isCorrect ? 'correct' : 'incorrect'
}

// 信心等级标签
const getConfidenceLabel = (level: string): string => {
  const map: Record<string, string> = {
    low: '低',
    mid: '中',
    high: '高'
  }
  return map[level] || level
}
</script>

<style scoped>
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--bg-tertiary);
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.detail-item span:last-child {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.human {
  color: var(--color-green-600);
  font-weight: 600;
}

.ai {
  color: var(--color-primary-600);
  font-weight: 600;
}

.highlight {
  color: var(--color-amber-600);
  font-weight: 600;
}

.positive {
  color: var(--color-green-600);
  font-weight: 600;
}

.negative {
  color: var(--color-red-600);
  font-weight: 600;
}

.correct {
  color: var(--color-green-600);
  font-weight: 600;
}

.incorrect {
  color: var(--color-red-600);
  font-weight: 600;
}

.empty-tip {
  text-align: center;
  color: var(--text-secondary);
  padding: 20px;
}
</style>
