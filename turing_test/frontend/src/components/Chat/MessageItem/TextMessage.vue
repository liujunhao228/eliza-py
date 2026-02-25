<template>
  <div class="system-message">
    <el-icon><InfoFilled /></el-icon>
    <span v-text="message.content"></span>
  </div>
</template>

<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'
import type { MessageDisplay } from '@/types'

interface Props {
  message: MessageDisplay
}

defineProps<Props>()
</script>

<style scoped>
.system-message {
  align-self: center;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-primary-100);
  color: var(--color-primary);
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.1);
}
</style>
