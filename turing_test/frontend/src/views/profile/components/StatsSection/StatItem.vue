<template>
  <div class="stat-item" :class="variant">
    <span class="stat-value">{{ value }}</span>
    <span class="stat-label">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  value: string | number
  label: string
  variant?: 'default' | 'highlight' | 'success' | 'warning'
}>()
</script>

<style scoped>
.stat-item {
  text-align: center;
  padding: 15px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-md);
}

.stat-item.highlight {
  background: var(--color-primary-gradient);
  color: var(--bg-surface);
}

.stat-item.highlight .stat-label {
  color: rgba(255, 255, 255, 0.9);
}

.stat-item.success {
  background-color: var(--color-primary-50);
  border: 1px solid var(--color-primary-100);
}

.stat-item.warning {
  background-color: var(--color-red-50);
  border: 1px solid var(--color-red-100);
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: var(--text-primary);
  margin-bottom: 5px;
}

.highlight .stat-value {
  color: var(--bg-surface);
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
