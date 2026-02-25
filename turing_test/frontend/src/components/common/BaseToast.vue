<template>
  <Teleport to="body">
    <div class="base-toast-container" :style="containerStyle">
      <transition-group name="toast-list">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'base-toast',
            `base-toast--${toast.type}`,
            `base-toast--${toast.position}`
          ]"
          role="alert"
          @mouseenter="pauseTimer(toast.id)"
          @mouseleave="resumeTimer(toast.id)"
        >
          <!-- 图标 -->
          <span class="base-toast__icon">
            <svg v-if="toast.type === 'success'" width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="8" fill="currentColor" opacity="0.2"/>
              <path d="M6 10L9 13L14 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="toast.type === 'error'" width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="8" fill="currentColor" opacity="0.2"/>
              <path d="M10 6V10M10 14H10.01M6 10L14 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="toast.type === 'warning'" width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 2L18 16H2L10 2Z" fill="currentColor" opacity="0.2"/>
              <path d="M10 7V11M10 13H10.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="8" fill="currentColor" opacity="0.2"/>
              <circle cx="10" cy="10" r="2" fill="currentColor"/>
            </svg>
          </span>

          <!-- 内容 -->
          <div class="base-toast__content">
            <h4 v-if="toast.title" class="base-toast__title">{{ toast.title }}</h4>
            <p class="base-toast__message">{{ toast.message }}</p>
          </div>

          <!-- 关闭按钮 -->
          <button
            v-if="toast.closable"
            class="base-toast__close"
            @click="remove(toast.id)"
            aria-label="关闭提示"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>

          <!-- 进度条 -->
          <div
            v-if="toast.duration > 0"
            class="base-toast__progress"
            :style="{ animationDuration: `${toast.duration}ms` }"
          >
            <div class="base-toast__progress-bar"></div>
          </div>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'
export type ToastPosition = 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right'

export interface ToastOptions {
  id?: number
  type?: ToastType
  title?: string
  message: string
  duration?: number
  position?: ToastPosition
  closable?: boolean
}

interface Toast extends ToastOptions {
  id: number
  type: ToastType
  duration: number
  position: ToastPosition
  closable: boolean
  timerId?: number
  paused?: boolean
  remaining?: number
}

interface Props {
  maxToasts?: number
  defaultDuration?: number
  defaultPosition?: ToastPosition
}

const props = withDefaults(defineProps<Props>(), {
  maxToasts: 5,
  defaultDuration: 3000,
  defaultPosition: 'top-right'
})

const toasts = ref<Toast[]>([])
let idCounter = 0

const containerStyle = computed(() => {
  const positionMap: Record<ToastPosition, { top?: string; bottom?: string; left?: string; right?: string; transform?: string }> = {
    'top-left': { top: '20px', left: '20px' },
    'top-center': { top: '20px', left: '50%', transform: 'translateX(-50%)' },
    'top-right': { top: '20px', right: '20px' },
    'bottom-left': { bottom: '20px', left: '20px' },
    'bottom-center': { bottom: '20px', left: '50%', transform: 'translateX(-50%)' },
    'bottom-right': { bottom: '20px', right: '20px' }
  }
  return positionMap[props.defaultPosition] || positionMap['top-right']
})

function add(options: Omit<ToastOptions, 'id'>) {
  const id = ++idCounter
  const toast: Toast = {
    id,
    type: options.type || 'info',
    title: options.title,
    message: options.message,
    duration: options.duration ?? props.defaultDuration,
    position: options.position || props.defaultPosition,
    closable: options.closable ?? true,
    remaining: options.duration ?? props.defaultDuration
  }

  if (toasts.value.length >= props.maxToasts) {
    toasts.value.shift()
  }

  toasts.value.push(toast)

  if (toast.duration > 0) {
    startTimer(toast)
  }

  return id
}

function startTimer(toast: Toast) {
  toast.timerId = window.setTimeout(() => {
    remove(toast.id)
  }, toast.remaining || toast.duration)
}

function pauseTimer(id: number) {
  const toast = toasts.value.find(t => t.id === id)
  if (toast && toast.timerId) {
    clearTimeout(toast.timerId)
    toast.paused = true
    toast.remaining = toast.remaining || toast.duration
  }
}

function resumeTimer(id: number) {
  const toast = toasts.value.find(t => t.id === id)
  if (toast && toast.paused) {
    toast.paused = false
    startTimer(toast)
  }
}

function remove(id: number) {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index !== -1) {
    const toast = toasts.value[index]
    if (toast?.timerId) {
      clearTimeout(toast.timerId)
    }
    toasts.value.splice(index, 1)
  }
}

function clear() {
  toasts.value.forEach(toast => {
    if (toast.timerId) {
      clearTimeout(toast.timerId)
    }
  })
  toasts.value = []
}

onUnmounted(() => {
  clear()
})

defineExpose({ add, remove, clear })
</script>

<style scoped>
/* ==============================================
   BaseToast 基础提示组件
   ============================================== */

.base-toast-container {
  position: fixed;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: calc(100% - 40px);
  pointer-events: none;
}

.base-toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-surface);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  position: relative;
  overflow: hidden;
  min-width: 280px;
  max-width: 420px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 类型 */
.base-toast--success {
  border-left: 4px solid var(--color-success);
}

.base-toast--success .base-toast__icon {
  color: var(--color-success);
}

.base-toast--error {
  border-left: 4px solid var(--color-error);
}

.base-toast--error .base-toast__icon {
  color: var(--color-error);
}

.base-toast--warning {
  border-left: 4px solid var(--color-warning);
}

.base-toast--warning .base-toast__icon {
  color: var(--color-warning);
}

.base-toast--info {
  border-left: 4px solid var(--color-primary);
}

.base-toast--info .base-toast__icon {
  color: var(--color-primary);
}

/* 图标 */
.base-toast__icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 内容 */
.base-toast__content {
  flex: 1;
  min-width: 0;
}

.base-toast__title {
  margin: 0 0 4px 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.base-toast__message {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  word-break: break-word;
}

/* 关闭按钮 */
.base-toast__close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--rounded);
  transition: all 0.2s ease;
}

.base-toast__close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

/* 进度条 */
.base-toast__progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--bg-tertiary);
}

.base-toast__progress-bar {
  height: 100%;
  background: currentColor;
  animation: progress linear forwards;
}

@keyframes progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

/* 过渡动画 */
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
  transform: translateX(-100%);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .base-toast-container {
    left: 12px;
    right: 12px;
    max-width: none;
  }

  .base-toast {
    min-width: auto;
    max-width: none;
  }
}
</style>
