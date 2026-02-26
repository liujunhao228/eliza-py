<template>
  <div class="stats-card">
    <h3>{{ title }}</h3>
    <div class="stats-grid">
      <slot>
        <slot name="default"></slot>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<style scoped>
.stats-card {
  background-color: var(--bg-surface);
  border-radius: var(--rounded-xl);
  padding: 20px;
  box-shadow: var(--shadow-md);
}

.stats-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}
</style>
