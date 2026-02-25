<template>
  <span :class="[
    'base-badge',
    `base-badge--${type}`,
    `base-badge--${size}`,
    {
      'base-badge--dot': isDot,
      'base-badge--absolute': absolute,
      'base-badge--hidden': hidden
    }
  ]">
    <!-- 子元素（当 absolute 为 true 时） -->
    <slot v-if="absolute"></slot>

    <!-- 徽章内容 -->
    <span v-if="!hidden" class="base-badge__content">
      <span v-if="isDot" class="base-badge__dot"></span>
      <span v-else>{{ displayValue }}</span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  value?: string | number
  max?: number
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'small' | 'medium' | 'large'
  isDot?: boolean
  absolute?: boolean
  hidden?: boolean
  offset?: [number, number]
}

const props = withDefaults(defineProps<Props>(), {
  value: '',
  max: 99,
  type: 'danger',
  size: 'medium',
  isDot: false,
  absolute: false,
  hidden: false,
  offset: () => [0, 0]
})

const displayValue = computed(() => {
  if (props.isDot) return ''
  
  const numValue = Number(props.value)
  if (isNaN(numValue)) return props.value
  
  if (props.max && numValue > props.max) {
    return `${props.max}+`
  }
  
  return String(props.value)
})
</script>

<style scoped>
/* ==============================================
   BaseBadge 基础徽章组件
   ============================================== */

.base-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.base-badge--absolute {
  display: inline-block;
}

.base-badge--hidden .base-badge__content {
  display: none;
}

/* 徽章内容 */
.base-badge__content {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  white-space: nowrap;
  border-radius: var(--rounded-full);
  transition: all 0.2s ease;
}

/* 圆点 */
.base-badge__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

/* 尺寸 */
.base-badge--small .base-badge__content {
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
}

.base-badge--small .base-badge__dot {
  width: 6px;
  height: 6px;
}

.base-badge--medium .base-badge__content {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  font-size: 12px;
}

.base-badge--medium .base-badge__dot {
  width: 8px;
  height: 8px;
}

.base-badge--large .base-badge__content {
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  font-size: 14px;
}

.base-badge--large .base-badge__dot {
  width: 10px;
  height: 10px;
}

/* 类型 */
.base-badge--primary {
  color: var(--color-primary);
}

.base-badge--primary .base-badge__content {
  background: var(--color-primary-100);
  color: var(--color-primary-700);
}

.base-badge--success {
  color: var(--color-success);
}

.base-badge--success .base-badge__content {
  background: var(--color-green-100);
  color: var(--color-green-700);
}

.base-badge--warning {
  color: var(--color-warning);
}

.base-badge--warning .base-badge__content {
  background: var(--color-amber-100);
  color: var(--color-amber-700);
}

.base-badge--danger {
  color: var(--color-error);
}

.base-badge--danger .base-badge__content {
  background: var(--color-red-100);
  color: var(--color-red-700);
}

.base-badge--info {
  color: var(--color-gray-500);
}

.base-badge--info .base-badge__content {
  background: var(--color-gray-200);
  color: var(--color-gray-700);
}

/* 绝对定位样式 */
.base-badge--absolute.base-badge--top-right {
  position: relative;
}

.base-badge--absolute .base-badge__content {
  position: absolute;
  top: calc(-1 * var(--badge-offset-top, 0px));
  right: calc(-1 * var(--badge-offset-right, 0px));
  transform: translate(50%, -50%);
  border: 2px solid var(--bg-surface);
}

/* 动画 */
@keyframes badge-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
}

.base-badge--dot .base-badge__dot {
  animation: badge-pulse 2s ease-in-out infinite;
}
</style>
