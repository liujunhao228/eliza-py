<template>
  <StatsCard title="📈 对话统计">
    <StatItem :value="stats.total_sessions || 0" label="总对话数" />
    <StatItem :value="formatNumber(stats.avg_turns || 0)" label="平均轮数" />
    <StatItem :value="formatConfidence(stats)" label="平均信心" />
    <StatItem :value="`${formatNumber(stats.avg_session_duration || 0)}s`" label="平均时长" />
  </StatsCard>
</template>

<script setup lang="ts">
import StatsCard from './StatsCard.vue'
import StatItem from './StatItem.vue'
import { formatNumber } from '../../utils/formatters'
import { calcAvgConfidence } from '../../utils/calculations'
import type { UserStats } from '@/types'

const formatConfidence = (stats: UserStats): string => {
  return calcAvgConfidence(stats)
}

defineProps<{
  stats: UserStats
}>()
</script>
