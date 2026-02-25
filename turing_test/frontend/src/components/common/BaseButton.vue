<template>
  <button
    :class="[
      'base-button',
      `base-button--${type}`,
      `base-button--${size}`,
      {
        'base-button--loading': loading,
        'base-button--disabled': disabled || loading,
        'base-button--block': block,
        'base-button--icon-only': iconOnly
      }
    ]"
    :disabled="disabled || loading"
    :type="nativeType"
    @click="handleClick"
  >
    <!-- 加载图标 -->
    <span v-if="loading" class="base-button__loading">
      <svg class="loading-spinner" viewBox="0 0 50 50">
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="currentColor"
          stroke-width="4"
          stroke-dasharray="80"
          stroke-dashoffset="60"
          stroke-linecap="round"
          transform="rotate(-90 25 25)"
        />
      </svg>
    </span>

    <!-- 图标 -->
    <span v-else-if="icon" class="base-button__icon">
      <component :is="icon" />
    </span>

    <!-- 文本内容 -->
    <span class="base-button__text">
      <slot></slot>
    </span>
  </button>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface Props {
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  loading?: boolean
  block?: boolean
  icon?: Component
  iconOnly?: boolean
  nativeType?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<Props>(), {
  type: 'default',
  size: 'medium',
  disabled: false,
  loading: false,
  block: false,
  iconOnly: false,
  nativeType: 'button'
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

function handleClick(event: MouseEvent) {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<style scoped>
/* ==============================================
   BaseButton 基础按钮组件
   ============================================== */

.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: inherit;
  font-weight: 500;
  text-align: center;
  text-transform: none;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: var(--rounded-md);
  transition: all 0.2s ease;
  position: relative;
}

.base-button:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.base-button:active {
  transform: translateY(0);
}

/* 尺寸 */
.base-button--small {
  padding: 6px 12px;
  font-size: var(--text-sm);
  height: 32px;
}

.base-button--medium {
  padding: 8px 16px;
  font-size: var(--text-base);
  height: 40px;
}

.base-button--large {
  padding: 12px 24px;
  font-size: var(--text-lg);
  height: 48px;
}

/* 类型 */
.base-button--primary {
  background: var(--color-primary-gradient);
  color: white;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.base-button--primary:hover:not(.base-button--disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

.base-button--success {
  background: var(--color-success-gradient);
  color: white;
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
}

.base-button--success:hover:not(.base-button--disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(34, 197, 94, 0.4);
}

.base-button--warning {
  background: var(--color-warning-gradient);
  color: white;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.base-button--warning:hover:not(.base-button--disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4);
}

.base-button--danger {
  background: var(--color-error-gradient);
  color: white;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.base-button--danger:hover:not(.base-button--disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4);
}

.base-button--info {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-secondary);
}

.base-button--info:hover:not(.base-button--disabled) {
  background: var(--bg-secondary);
  border-color: var(--border-tertiary);
}

.base-button--default {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.base-button--default:hover:not(.base-button--disabled) {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

/* 禁用状态 */
.base-button--disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none !important;
  box-shadow: none !important;
}

/* 块级按钮 */
.base-button--block {
  width: 100%;
}

/* 纯图标按钮 */
.base-button--icon-only {
  padding: 8px;
  border-radius: var(--rounded);
}

.base-button--icon-only.base-button--small {
  width: 32px;
  height: 32px;
}

.base-button--icon-only.base-button--medium {
  width: 40px;
  height: 40px;
}

.base-button--icon-only.base-button--large {
  width: 48px;
  height: 48px;
}

/* 加载动画 */
.base-button__loading {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

.base-button--large .loading-spinner {
  width: 20px;
  height: 20px;
}

.base-button--small .loading-spinner {
  width: 14px;
  height: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 图标 */
.base-button__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1em;
}

/* 文本 */
.base-button__text {
  line-height: 1.5;
}
</style>
