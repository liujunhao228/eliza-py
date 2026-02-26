<template>
  <div class="history-section">
    <div class="history-section-header">
      <h3>📜 对话历史</h3>
      <BaseButton type="info" size="small" @click="handleGoToHistory">
        查看全部 →
      </BaseButton>
    </div>

    <BaseEmpty
      v-if="!history || history.length === 0"
      title="还没有对话记录"
      size="small"
    >
      <template #action>
        <BaseButton type="primary" @click="handleGoToLobby">开始第一局</BaseButton>
      </template>
    </BaseEmpty>

    <div v-else class="history-list">
      <HistoryItem
        v-for="session in history"
        :key="session.id"
        :session="session"
        @click="handleClick"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { BaseButton, BaseEmpty } from '@/components/common'
import HistoryItem from './HistoryItem.vue'
import type { Session } from '@/types'

const emit = defineEmits<{
  goToHistory: []
  goToLobby: []
  viewDetail: [session: Session]
}>()

defineProps<{
  history: Session[]
}>()

const handleGoToHistory = () => {
  emit('goToHistory')
}

const handleGoToLobby = () => {
  emit('goToLobby')
}

const handleClick = (session: Session) => {
  emit('viewDetail', session)
}
</script>

<style scoped>
.history-section {
  background-color: var(--bg-surface);
  border-radius: var(--rounded-xl);
  padding: 20px;
  box-shadow: var(--shadow-md);
  margin-bottom: 30px;
}

.history-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.history-section h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-list {
  display: flex;
  flex-direction: column;
}
</style>
