<template>
  <StatsCard title="🤖 对话类型分布">
    <div class="type-distribution">
      <div class="type-item human">
        <span class="type-label">真人</span>
        <div class="type-bar">
          <div class="type-fill" :style="{ width: humanPercent + '%' }"></div>
        </div>
        <span class="type-count">{{ stats.human_sessions || 0 }}</span>
      </div>
      <div class="type-item ai">
        <span class="type-label">AI</span>
        <div class="type-bar">
          <div class="type-fill" :style="{ width: aiPercent + '%' }"></div>
        </div>
        <span class="type-count">{{ stats.ai_sessions || 0 }}</span>
      </div>
    </div>
  </StatsCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatsCard from './StatsCard.vue'
import { getPercentage } from '../../utils/calculations'
import type { UserStats } from '@/types'

const props = defineProps<{
  stats: UserStats
}>()

const total = computed(() => props.stats.total_sessions || 0)
const humanPercent = computed(() => getPercentage(props.stats.human_sessions || 0, total.value))
const aiPercent = computed(() => getPercentage(props.stats.ai_sessions || 0, total.value))
</script>

<style scoped>
.type-distribution {
  display: flex;
  flex-direction: column;
  gap: 12px;
  grid-column: 1 / -1;
}

.type-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-label {
  min-width: 80px;
  font-size: 14px;
  color: var(--text-secondary);
}

.type-bar {
  flex: 1;
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-sm);
  overflow: hidden;
}

.type-fill {
  height: 100%;
  transition: width 0.3s;
}

.human .type-fill {
  background-color: var(--color-green-500);
}

.ai .type-fill {
  background-color: var(--color-primary-500);
}

.type-count {
  min-width: 30px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
