<template>
  <div class="history-item" @click="handleClick">
    <div class="history-header">
      <span class="history-date">{{ formatDate(session.started_at) }}</span>
      <span class="history-type" :class="getTypeClass(session.opponent_type)">
        {{ getTypeLabel(session.opponent_type) }}
      </span>
    </div>
    <div class="history-info">
      <div class="history-stats">
        <span class="stat-badge">
          📝 {{ session.meta_conversation_count || 0 }} 次元对话
        </span>
        <span class="stat-badge">
          ⏱️ {{ formatDuration(duration) }}
        </span>
        <span class="stat-badge">
          🔄 {{ session.turn_count }} 回合
        </span>
      </div>
      <div v-if="session.triggered_mid_game" class="mid-game-badge">
        ⚡ 场中判断
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDate, getTypeLabel, getTypeClass, formatDuration } from '../../utils/formatters'
import type { Session } from '@/types'

const emit = defineEmits<{
  click: [session: Session]
}>()

const props = defineProps<{
  session: Session
}>()

// 计算会话时长（秒）
const duration = computed(() => {
  if (!props.session.started_at || !props.session.ended_at) return 0
  const start = new Date(props.session.started_at).getTime()
  const end = new Date(props.session.ended_at).getTime()
  return Math.floor((end - start) / 1000)
})

const handleClick = () => {
  emit('click', props.session)
}
</script>

<style scoped>
.history-item {
  display: flex;
  flex-direction: column;
  padding: 15px;
  margin-bottom: 10px;
  background-color: var(--bg-tertiary);
  border-radius: var(--rounded-md);
  cursor: pointer;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: var(--bg-secondary);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.history-date {
  font-size: 14px;
  color: var(--text-secondary);
}

.history-type {
  padding: 4px 8px;
  border-radius: var(--rounded-sm);
  font-size: 12px;
  font-weight: 600;
}

.history-type.human {
  background-color: var(--color-green-50);
  color: var(--color-green-700);
}

.history-type.ai {
  background-color: var(--color-primary-50);
  color: var(--color-primary-700);
}

.history-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-stats {
  display: flex;
  gap: 10px;
}

.stat-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background-color: var(--bg-surface);
  border-radius: var(--rounded-sm);
  font-size: 12px;
  color: var(--text-secondary);
}

.mid-game-badge {
  padding: 4px 8px;
  background-color: var(--color-amber-50);
  color: var(--color-amber-700);
  border-radius: var(--rounded-sm);
  font-size: 12px;
  font-weight: 600;
}
</style>
