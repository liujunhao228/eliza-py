<template>
  <div :class="['base-progress', `base-progress--${size}`, `base-progress--${type}`, { 'base-progress--no-text': !showText }]">
    <!-- 进度条 -->
    <div class="base-progress__track" role="progressbar" :aria-valuenow="percentage" aria-valuemin="0" aria-valuemax="100">
      <div
        class="base-progress__fill"
        :style="{ width: `${clampedPercentage}%` }"
      >
        <!-- 条纹动画 -->
        <div v-if="striped" :class="{ 'base-progress__striped': animated }"></div>
      </div>
    </div>

    <!-- 文本显示 -->
    <div v-if="showText" class="base-progress__text">
      <slot :percentage="clampedPercentage">
        {{ clampedPercentage }}%
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  percentage?: number
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'small' | 'medium' | 'large'
  showText?: boolean
  striped?: boolean
  animated?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  percentage: 0,
  type: 'primary',
  size: 'medium',
  showText: false,
  striped: false,
  animated: false
})

// 计算百分比 - 使用 computed 确保响应式更新
const clampedPercentage = computed(() => {
  return Math.max(0, Math.min(100, props.percentage))
})
</script>

<style scoped>
/* ==============================================
   BaseProgress 基础进度条组件
   ============================================== */

.base-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

/* 当不显示文本时，移除 gap 并确保进度条占满宽度 */
.base-progress--no-text {
  gap: 0;
}

/* 进度条轨道 */
.base-progress__track {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--rounded-full);
  overflow: hidden;
  position: relative;
}

/* 进度条填充 */
.base-progress__fill {
  height: 100%;
  border-radius: var(--rounded-full);
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
  min-width: 2px; /* 确保即使进度为 0 也能看到一点进度条 */
}

/* 类型 */
.base-progress--primary .base-progress__fill {
  background: var(--color-primary-gradient);
}

.base-progress--success .base-progress__fill {
  background: var(--color-success-gradient);
}

.base-progress--warning .base-progress__fill {
  background: var(--color-warning-gradient);
}

.base-progress--danger .base-progress__fill {
  background: var(--color-error-gradient);
}

.base-progress--info .base-progress__fill {
  background: var(--color-gray-400);
}

/* 尺寸 */
.base-progress--small .base-progress__track {
  height: 4px;
}

.base-progress--medium .base-progress__track {
  height: 8px;
}

.base-progress--large .base-progress__track {
  height: 12px;
}

/* 条纹效果 */
.base-progress__striped {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 16px 16px;
}

.base-progress__striped.animated {
  animation: stripes 1s linear infinite;
}

@keyframes stripes {
  from {
    background-position: 0 0;
  }
  to {
    background-position: 16px 16px;
  }
}

/* 文本显示 */
.base-progress__text {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 45px;
  text-align: right;
}

/* 圆形进度条 */
.base-progress--circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  width: 120px;
  height: 120px;
}

.base-progress--circle .base-progress__track {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: transparent;
}

.base-progress--circle .base-progress__fill {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  clip-path: circle(50% at 50% 50%);
}

.base-progress--circle .base-progress__text {
  position: absolute;
  text-align: center;
  min-width: auto;
}
</style>
