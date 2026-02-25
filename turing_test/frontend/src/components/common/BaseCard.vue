<template>
  <div
    :class="[
      'base-card',
      `base-card--${shadow}`,
      {
        'base-card--hoverable': hoverable,
        'base-card--bordered': bordered
      }
    ]"
    :style="customStyle"
  >
    <!-- 卡片头部 -->
    <div v-if="$slots.header || title" class="base-card__header">
      <slot name="header">
        <h3 class="base-card__title">{{ title }}</h3>
      </slot>
    </div>

    <!-- 卡片主体 -->
    <div class="base-card__body">
      <slot></slot>
    </div>

    <!-- 卡片底部 -->
    <div v-if="$slots.footer" class="base-card__footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string
  shadow?: 'always' | 'hover' | 'never'
  hoverable?: boolean
  bordered?: boolean
  customStyle?: Record<string, string>
}

withDefaults(defineProps<Props>(), {
  title: '',
  shadow: 'always',
  hoverable: false,
  bordered: true,
  customStyle: () => ({})
})
</script>

<style scoped>
/* ==============================================
   BaseCard 基础卡片组件
   ============================================== */

.base-card {
  background: var(--bg-surface);
  border-radius: var(--rounded-xl);
  overflow: hidden;
  transition: all 0.3s ease;
}

.base-card--bordered {
  border: 1px solid var(--border-primary);
}

/* 阴影效果 */
.base-card--shadow-always {
  box-shadow: var(--shadow-md);
}

.base-card--shadow-hover {
  box-shadow: var(--shadow-xs);
}

.base-card--shadow-hover:hover {
  box-shadow: var(--shadow-md);
}

.base-card--shadow-never {
  box-shadow: none;
}

/* 可悬浮效果 */
.base-card--hoverable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* 卡片头部 */
.base-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.base-card__title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}

/* 卡片主体 */
.base-card__body {
  padding: 20px;
}

/* 卡片底部 */
.base-card__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .base-card__header,
  .base-card__body,
  .base-card__footer {
    padding: 12px 16px;
  }

  .base-card__title {
    font-size: var(--text-base);
  }
}
</style>
