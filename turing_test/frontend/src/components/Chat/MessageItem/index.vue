<template>
  <div :class="['message-item', `message-${message.sender}`]" role="article" :aria-label="`${message.sender === 'user' ? '我' : '对手'}的消息`">
    <!-- 系统消息 -->
    <TextMessage v-if="message.sender === 'system'" :message="message" />
    
    <!-- 用户/对手消息 -->
    <DefaultMessage v-else :message="message" :show-tooltip="showTooltip" @update:show-tooltip="$emit('update:showTooltip', $event)" />
  </div>
</template>

<script setup lang="ts">
import TextMessage from './TextMessage.vue'
import DefaultMessage from './DefaultMessage.vue'
import type { MessageDisplay } from '@/types'

interface Props {
  message: MessageDisplay
  showTooltip: number | null
}

defineProps<Props>()
defineEmits<{
  (e: 'update:showTooltip', value: number | null): void
}>()
</script>

<style scoped>
.message-item {
  display: flex;
  flex-direction: column;
  margin: 8px 0;
  animation: messageSlide 0.3s ease-out;
}

@keyframes messageSlide {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 用户消息 */
.message-user {
  align-items: flex-end;
}

/* 对手消息 */
.message-opponent {
  align-items: flex-start;
}
</style>
