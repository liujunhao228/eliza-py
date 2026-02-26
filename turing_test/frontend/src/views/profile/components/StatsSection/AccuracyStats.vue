<template>
  <StatsCard title="🎯 判断准确率">
    <StatItem :value="formatPercent(stats.accuracy || 0)" label="整体准确率" variant="success" />
    <StatItem :value="formatPercent(stats.accuracy_with_meta || 0)" label="使用元对话" />
    <StatItem :value="formatPercent(stats.accuracy_without_meta || 0)" label="未用元对话" />
    <StatItem :value="formatPercent(stats.mid_game_accuracy || 0)" label="场中判断" />
  </StatsCard>
</template>

<script setup lang="ts">
import StatsCard from './StatsCard.vue'
import StatItem from './StatItem.vue'
import { formatPercent } from '../../utils/formatters'
import type { UserStats } from '@/types'

defineProps<{
  stats: UserStats
}>()
</script>
