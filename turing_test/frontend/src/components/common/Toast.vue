<template>
  <Teleport to="body">
    <TransitionGroup name="toast-list">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast-${toast.type}`"
        role="alert"
        aria-live="polite"
      >
        <span class="toast-icon" aria-hidden="true">
          <component :is="getIcon(toast.type)" />
        </span>
        <span class="toast-message">{{ toast.message }}</span>
        <button 
          class="toast-close" 
          @click="removeToast(toast.id)"
          type="button"
          aria-label="关闭通知"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { toastState, removeToast } from '../../composables/useToast'
import type { ToastType } from '../../composables/useToast'
import { CircleCheck, CircleClose, InfoFilled, Warning } from '@element-plus/icons-vue'

const toasts = toastState.toasts

function getIcon(type: ToastType) {
  const icons: Record<ToastType, any> = {
    success: CircleCheck,
    error: CircleClose,
    info: InfoFilled,
    warning: Warning
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
  border-radius: var(--rounded-md);
  box-shadow: var(--shadow-lg);
  font-size: var(--text-sm);
  font-weight: 500;
  z-index: 9999;
  min-width: 200px;
  max-width: 400px;
}

.toast-success {
  background: var(--color-success);
  color: white;
}

.toast-error {
  background: var(--color-error);
  color: white;
}

.toast-info {
  background: var(--color-primary);
  color: white;
}

.toast-warning {
  background: var(--color-warning);
  color: var(--text-primary);
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.toast-icon :deep(.el-icon) {
  width: 18px;
  height: 18px;
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
  width: 24px;
  height: 24px;
  border-radius: var(--rounded-sm);
  transition: all 0.2s ease;
}

.toast-close:hover {
  background: rgba(0, 0, 0, 0.1);
}

.toast-close:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
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

/* 移动端适配 */
@media (max-width: 479px) {
  .toast {
    right: 12px;
    left: 12px;
    top: 12px;
    min-width: auto;
    max-width: none;
  }
}
</style>
