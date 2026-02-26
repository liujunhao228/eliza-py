<template>
  <div class="stats-section">
    <DialogStats :stats="stats" />
    <ScoreStats :stats="stats" :score-history="scoreHistory" />
    <AccuracyStats :stats="stats" />
    <MetaStats :stats="stats" />
    <TypeDistribution :stats="stats" />
    <ConfidenceDistribution :stats="stats" />
  </div>
</template>

<script setup lang="ts">
import DialogStats from './DialogStats.vue'
import ScoreStats from './ScoreStats.vue'
import AccuracyStats from './AccuracyStats.vue'
import MetaStats from './MetaStats.vue'
import TypeDistribution from './TypeDistribution.vue'
import ConfidenceDistribution from './ConfidenceDistribution.vue'
import type { UserStats, ScoreHistory } from '@/types'

defineProps<{
  stats: UserStats
  scoreHistory: ScoreHistory[]
}>()
</script>

<style scoped>
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}
</style>
