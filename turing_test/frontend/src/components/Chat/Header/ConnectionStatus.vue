<template>
  <div
    class="connection-status"
    :class="statusClass"
    role="status"
    :aria-label="`连接状态：${statusText}`"
  >
    <div class="status-indicator">
      <el-icon v-if="status !== 'connected'" :class="iconClass">
        <Connection />
      </el-icon>
      <el-icon v-else class="status-icon-success">
        <Select />
      </el-icon>
    </div>
    <span class="status-text">{{ statusText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Connection, Select } from '@element-plus/icons-vue'
import type { WSConnectionState } from '@/types'

interface Props {
  isConnected?: boolean
  status?: WSConnectionState
}

const props = withDefaults(defineProps<Props>(), {
  isConnected: false,
  status: 'disconnected'
})

// 连接状态文本
const statusText = computed(() => {
  switch (props.status) {
    case 'connecting':
      return '连接中...'
    case 'connected':
      return '已连接'
    case 'reconnecting':
      return '重新连接中...'
    case 'error':
      return '连接错误'
    default:
      return '未连接'
  }
})

// 连接状态 class
const statusClass = computed(() => ({
  'status-disconnected': !props.isConnected && props.status === 'disconnected',
  'status-connecting': props.status === 'connecting',
  'status-reconnecting': props.status === 'reconnecting',
  'status-error': props.status === 'error',
  'status-connected': props.isConnected && props.status === 'connected'
}))

// 图标 class
const iconClass = computed(() => ({
  'status-icon-disconnected': !props.isConnected && props.status === 'disconnected',
  'status-icon-connecting': props.status === 'connecting',
  'status-icon-reconnecting': props.status === 'reconnecting',
  'status-icon-error': props.status === 'error'
}))
</script>

<style scoped>
.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--rounded-full);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-disconnected {
  background: var(--color-red-50);
  color: var(--color-error);
}

.status-icon-disconnected {
  animation: pulse 2s ease-in-out infinite;
}

.status-connecting,
.status-reconnecting {
  background: var(--color-amber-50);
  color: var(--color-amber-600);
}

.status-icon-connecting,
.status-icon-reconnecting {
  animation: spin 1.5s linear infinite;
}

.status-error {
  background: var(--color-red-50);
  color: var(--color-error);
}

.status-icon-error {
  animation: shake 0.5s ease-in-out;
}

.status-connected {
  background: var(--color-green-50);
  color: var(--color-success);
}

.status-icon-success {
  color: var(--color-success);
}

.status-text {
  font-weight: 500;
}

/* 动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-2px);
  }
  75% {
    transform: translateX(2px);
  }
}
</style>
