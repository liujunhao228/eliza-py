<template>
  <Teleport to="body">
    <TransitionGroup name="toast-list">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast-${toast.type}`"
      >
        <span class="toast-icon">{{ getIcon(toast.type) }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="removeToast(toast.id)">×</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { toastState, removeToast } from '../../composables/useToast'
import type { ToastType } from '../../composables/useToast'

const toasts = toastState.toasts

function getIcon(type: ToastType): string {
  const icons: Record<ToastType, string> = {
    success: '✓',
    error: '✗',
    info: 'ℹ',
    warning: '⚠'
  }
  return icons[type]
}
</script>

<style scoped>
.toast-list-enter-active,
.toast-list-leave-active {
  transition: all 0.3s ease;
}

.toast-list-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-list-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast {
  position: fixed;
  right: 20px;
  top: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-size: 14px;
  font-weight: 500;
  z-index: 9999;
  min-width: 200px;
  max-width: 400px;
}

.toast-success {
  background: #28a745;
  color: white;
}

.toast-error {
  background: #dc3545;
  color: white;
}

.toast-info {
  background: #007bff;
  color: white;
}

.toast-warning {
  background: #ffc107;
  color: #333;
}

.toast-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.toast-close:hover {
  opacity: 1;
}

/* 多个 toast 堆叠 */
.toast-list-enter-from:nth-child(2) {
  transform: translateX(100%) translateY(-60px);
}

.toast-list-enter-from:nth-child(3) {
  transform: translateX(100%) translateY(-120px);
}

.toast-list-enter-from:nth-child(4) {
  transform: translateX(100%) translateY(-180px);
}
</style>
