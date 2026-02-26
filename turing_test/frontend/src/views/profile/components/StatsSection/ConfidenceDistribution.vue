<template>
  <StatsCard title="🎚️ 信心等级分布">
    <div class="confidence-distribution">
      <div class="confidence-item low">
        <span class="confidence-label">低信心</span>
        <div class="confidence-bar">
          <div class="confidence-fill" :style="{ width: lowPercent + '%' }"></div>
        </div>
        <span class="confidence-count">{{ stats.low_confidence_count || 0 }}</span>
      </div>
      <div class="confidence-item mid">
        <span class="confidence-label">中信心</span>
        <div class="confidence-bar">
          <div class="confidence-fill" :style="{ width: midPercent + '%' }"></div>
        </div>
        <span class="confidence-count">{{ stats.mid_confidence_count || 0 }}</span>
      </div>
      <div class="confidence-item high">
        <span class="confidence-label">高信心</span>
        <div class="confidence-bar">
          <div class="confidence-fill" :style="{ width: highPercent + '%' }"></div>
        </div>
        <span class="confidence-count">{{ stats.high_confidence_count || 0 }}</span>
      </div>
    </div>
  </StatsCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatsCard from './StatsCard.vue'
import { getConfidencePercentage } from '../../utils/calculations'
import type { UserStats } from '@/types'

const props = defineProps<{
  stats: UserStats
}>()

const lowPercent = computed(() => getConfidencePercentage('low', props.stats))
const midPercent = computed(() => getConfidencePercentage('mid', props.stats))
const highPercent = computed(() => getConfidencePercentage('high', props.stats))
</script>

<style scoped>
.confidence-distribution {
  display: flex;
  flex-direction: column;
  gap: 12px;
  grid-column: 1 / -1;
}

.confidence-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.confidence-label {
  min-width: 80px;
  font-size: 14px;
  color: var(--text-secondary);
}

.confidence-bar {
  flex: 1;
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-sm);
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  transition: width 0.3s;
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

.confidence-count {
  min-width: 30px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
