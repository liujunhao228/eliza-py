<template>
  <div :class="['base-skeleton', `base-skeleton--${type}`, `base-skeleton--${animation}`]" :style="customStyle">
    <!-- 文本类型 -->
    <template v-if="type === 'text'">
      <div
        v-for="i in rows"
        :key="i"
        :class="['base-skeleton__line', { 'base-skeleton__line--last': i === rows }]"
        :style="{ width: getWidth(i) }"
      ></div>
    </template>

    <!-- 圆形头像 -->
    <div v-else-if="type === 'circle'" class="base-skeleton__circle"></div>

    <!-- 矩形卡片 -->
    <div v-else-if="type === 'rect'" class="base-skeleton__rect"></div>

    <!-- 自定义内容 -->
    <slot v-else></slot>
  </div>
</template>

<script setup lang="ts">
interface Props {
  type?: 'text' | 'circle' | 'rect' | 'custom'
  rows?: number
  animation?: 'pulse' | 'wave' | 'none'
  widths?: string[]
  customStyle?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  rows: 1,
  animation: 'pulse',
  widths: () => ['100%', '100%', '60%'],
  customStyle: () => ({})
})

function getWidth(index: number): string {
  const width = props.widths[index - 1] || props.widths[props.widths.length - 1]
  return width ?? '100%'
}
</script>

<style scoped>
/* ==============================================
   BaseSkeleton 基础骨架屏组件
   ============================================== */

.base-skeleton {
  background: var(--bg-tertiary);
  border-radius: var(--rounded-md);
  overflow: hidden;
}

/* 文本行 */
.base-skeleton__line {
  height: 16px;
  margin-bottom: 12px;
  background: linear-gradient(
    90deg,
    var(--bg-tertiary) 0%,
    var(--bg-secondary) 50%,
    var(--bg-tertiary) 100%
  );
  background-size: 200% 100%;
}

.base-skeleton__line--last {
  margin-bottom: 0;
  width: 60% !important;
}

/* 圆形 */
.base-skeleton__circle {
  width: 48px;
  height: 48px;
  border-radius: var(--rounded-full);
  background: var(--bg-tertiary);
}

/* 矩形 */
.base-skeleton__rect {
  width: 100%;
  height: 120px;
  background: var(--bg-tertiary);
  border-radius: var(--rounded-lg);
}

/* 动画效果 */
.base-skeleton--pulse .base-skeleton__line,
.base-skeleton--pulse .base-skeleton__circle,
.base-skeleton--pulse .base-skeleton__rect {
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.base-skeleton--wave .base-skeleton__line,
.base-skeleton--wave .base-skeleton__circle,
.base-skeleton--wave .base-skeleton__rect {
  animation: skeleton-wave 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes skeleton-wave {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .base-skeleton--pulse,
  .base-skeleton--wave {
    animation: none;
  }
}

/* 尺寸变体 */
.base-skeleton--small .base-skeleton__line {
  height: 12px;
  margin-bottom: 8px;
}

.base-skeleton--large .base-skeleton__line {
  height: 20px;
  margin-bottom: 16px;
}

.base-skeleton--small .base-skeleton__circle {
  width: 32px;
  height: 32px;
}

.base-skeleton--large .base-skeleton__circle {
  width: 64px;
  height: 64px;
}
</style>
