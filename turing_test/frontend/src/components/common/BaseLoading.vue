<template>
  <div v-if="loading" :class="['base-loading-overlay', { 'base-loading-overlay--fullscreen': fullscreen }]">
    <div :class="['base-loading', `base-loading--${size}`]">
      <!-- 旋转加载器 -->
      <svg class="base-loading__spinner" viewBox="0 0 50 50">
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="url(#gradient)"
          stroke-width="4"
          stroke-dasharray="80"
          stroke-dashoffset="60"
          stroke-linecap="round"
          transform="rotate(-90 25 25)"
        />
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="var(--color-primary-600)" />
            <stop offset="100%" stop-color="var(--color-purple-600)" />
          </linearGradient>
        </defs>
      </svg>

      <!-- 加载文本 -->
      <p v-if="text || $slots.default" class="base-loading__text">
        <slot>{{ text }}</slot>
      </p>
    </div>
  </div>

  <!-- 内联加载器（非全屏模式） -->
  <div v-else-if="inline" :class="['base-loading', `base-loading--${size}`, 'base-loading--inline']">
    <svg class="base-loading__spinner" viewBox="0 0 50 50">
      <circle
        cx="25"
        cy="25"
        r="20"
        fill="none"
        stroke="url(#gradient-inline)"
        stroke-width="4"
        stroke-dasharray="80"
        stroke-dashoffset="60"
        stroke-linecap="round"
        transform="rotate(-90 25 25)"
      />
      <defs>
        <linearGradient id="gradient-inline" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="var(--color-primary-600)" />
          <stop offset="100%" stop-color="var(--color-purple-600)" />
        </linearGradient>
      </defs>
    </svg>
    <p v-if="text || $slots.default" class="base-loading__text">
      <slot>{{ text }}</slot>
    </p>
  </div>
</template>

<script setup lang="ts">
interface Props {
  loading?: boolean
  text?: string
  size?: 'small' | 'medium' | 'large'
  fullscreen?: boolean
  inline?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: true,
  text: '加载中...',
  size: 'medium',
  fullscreen: false,
  inline: false
})
</script>

<style scoped>
/* ==============================================
   BaseLoading 基础加载组件
   ============================================== */

.base-loading-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(4px);
  z-index: 9999;
}

.base-loading-overlay--fullscreen {
  position: fixed;
}

.base-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.base-loading--inline {
  flex-direction: row;
  gap: 12px;
}

/* 尺寸 */
.base-loading--small .base-loading__spinner {
  width: 24px;
  height: 24px;
}

.base-loading--small .base-loading__text {
  font-size: var(--text-sm);
}

.base-loading--medium .base-loading__spinner {
  width: 40px;
  height: 40px;
}

.base-loading--medium .base-loading__text {
  font-size: var(--text-base);
}

.base-loading--large .base-loading__spinner {
  width: 60px;
  height: 60px;
}

.base-loading--large .base-loading__text {
  font-size: var(--text-lg);
}

/* 加载动画 */
.base-loading__spinner {
  animation: spin 1s linear infinite;
}

/* 确保 circle 元素动画正常播放 */
.base-loading__spinner circle {
  animation: dash 1.5s ease-in-out infinite;
}

/* 显式定义动画属性，确保不被覆盖 */
.base-loading__spinner,
.base-loading__spinner circle {
  animation-fill-mode: forwards;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}

/* 加载文本 */
.base-loading__text {
  margin: 0;
  color: var(--text-primary);
  font-weight: 500;
  text-align: center;
}

.base-loading--inline .base-loading__text {
  text-align: left;
}
</style>
