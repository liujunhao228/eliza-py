<template>
  <div class="action-buttons">
    <BaseButton type="primary" size="large" @click="handleGoToLobby">
      🚀 返回大厅
    </BaseButton>
  </div>
</template>

<script setup lang="ts">
import { BaseButton } from '@/components/common'

const emit = defineEmits<{
  goToLobby: []
}>()

const handleGoToLobby = () => {
  emit('goToLobby')
}
</script>

<style scoped>
.action-buttons {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
