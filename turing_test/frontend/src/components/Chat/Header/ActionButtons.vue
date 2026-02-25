<template>
  <div class="header-actions">
    <!-- 场中判断按钮 -->
    <BaseButton
      type="warning"
      size="small"
      :disabled="disabled"
      @click="$emit('mid-game')"
      class="mid-game-btn"
    >
      ⚡ 场中判断
    </BaseButton>

    <!-- 结束对话按钮 -->
    <BaseButton
      type="danger"
      size="small"
      @click="$emit('end-chat')"
      class="end-chat-btn"
    >
      结束对话
    </BaseButton>
  </div>
</template>

<script setup lang="ts">
import { BaseButton } from '@/components/common'

interface Props {
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  disabled: false
})

defineEmits<{
  (e: 'mid-game'): void
  (e: 'end-chat'): void
}>()
</script>

<style scoped>
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mid-game-btn {
  height: 32px;
  padding: 0 12px;
}

.end-chat-btn {
  height: 32px;
  padding: 0 12px;
}
</style>
