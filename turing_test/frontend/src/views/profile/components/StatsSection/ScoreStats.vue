<template>
  <StatsCard title="💰 积分统计">
    <StatItem :value="userStore.score" label="当前积分" variant="highlight" />
    <StatItem :value="scoreRange.max || 0" label="历史最高" variant="success" />
    <StatItem :value="scoreRange.min || 0" label="历史最低" variant="warning" />
  </StatsCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatsCard from './StatsCard.vue'
import StatItem from './StatItem.vue'
import { useUserStore } from '@/stores/user'
import type { UserStats, ScoreHistory } from '@/types'

const userStore = useUserStore()

const props = defineProps<{
  stats: UserStats
  scoreHistory: ScoreHistory[]
}>()

// 从积分历史中计算最高和最低分
const scoreRange = computed(() => {
  if (!props.scoreHistory || props.scoreHistory.length === 0) {
    return { max: 0, min: 0 }
  }
  const scores = props.scoreHistory.map(h => h.score_change || 0)
  return {
    max: Math.max(...scores, 0),
    min: Math.min(...scores, 0)
  }
})
</script>
