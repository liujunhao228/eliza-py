<template>
  <div :class="['base-empty', `base-empty--${size}`]">
    <!-- 图标 -->
    <div class="base-empty__icon">
      <slot name="icon">
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <circle cx="40" cy="40" r="36" stroke="var(--color-gray-300)" stroke-width="2" stroke-dasharray="8 8"/>
          <path d="M30 40L38 48L50 32" stroke="var(--color-gray-400)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </slot>
    </div>

    <!-- 标题 -->
    <h3 v-if="title" class="base-empty__title">{{ title }}</h3>

    <!-- 描述 -->
    <p v-if="description || $slots.description" class="base-empty__description">
      <slot name="description">{{ description }}</slot>
    </p>

    <!-- 操作区域 -->
    <div v-if="$slots.action" class="base-empty__action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string
  description?: string
  size?: 'small' | 'medium' | 'large'
}

withDefaults(defineProps<Props>(), {
  title: '暂无数据',
  description: '',
  size: 'medium'
})
</script>

<style scoped>
/* ==============================================
   BaseEmpty 空状态组件
   ============================================== */

.base-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

/* 尺寸 */
.base-empty--small {
  padding: 20px 16px;
}

.base-empty--small .base-empty__icon {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
}

.base-empty--small .base-empty__icon svg {
  width: 48px;
  height: 48px;
}

.base-empty--small .base-empty__title {
  font-size: var(--text-sm);
  margin-bottom: 4px;
}

.base-empty--small .base-empty__description {
  font-size: var(--text-xs);
}

.base-empty--medium {
  padding: 40px 20px;
}

.base-empty--medium .base-empty__icon {
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
}

.base-empty--medium .base-empty__icon svg {
  width: 80px;
  height: 80px;
}

.base-empty--medium .base-empty__title {
  font-size: var(--text-lg);
  margin-bottom: 8px;
}

.base-empty--medium .base-empty__description {
  font-size: var(--text-sm);
  max-width: 300px;
}

.base-empty--large {
  padding: 60px 20px;
}

.base-empty--large .base-empty__icon {
  width: 120px;
  height: 120px;
  margin-bottom: 24px;
}

.base-empty--large .base-empty__icon svg {
  width: 120px;
  height: 120px;
}

.base-empty--large .base-empty__title {
  font-size: var(--text-2xl);
  margin-bottom: 12px;
}

.base-empty--large .base-empty__description {
  font-size: var(--text-base);
  max-width: 400px;
}

/* 图标 */
.base-empty__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-gray-400);
  animation: breathe 3s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

/* 标题 */
.base-empty__title {
  margin: 0;
  font-weight: 600;
  color: var(--text-primary);
}

/* 描述 */
.base-empty__description {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.6;
}

/* 操作区域 */
.base-empty__action {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}
</style>
