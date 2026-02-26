<template>
  <StatsCard title="💬 元对话统计">
    <StatItem :value="stats.total_meta_conversations || 0" label="总次数" />
    <StatItem :value="formatNumber(stats.avg_meta_per_session || 0)" label="平均每局" />
    <StatItem :value="stats.max_meta_in_one_session || 0" label="单局最高" />
  </StatsCard>
</template>

<script setup lang="ts">
import StatsCard from './StatsCard.vue'
import StatItem from './StatItem.vue'
import { formatNumber } from '../../utils/formatters'
import type { UserStats } from '@/types'

defineProps<{
  stats: UserStats
}>()
</script>
