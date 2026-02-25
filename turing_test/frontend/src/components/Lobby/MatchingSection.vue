<template>
  <BaseCard class="matching-section">
    <!-- 匹配动画 -->
    <div class="spinner-container">
      <div class="spinner"></div>
      <div class="pulse-ring"></div>
    </div>

    <!-- 匹配标题 -->
    <h2 class="matching-title">正在匹配对手...</h2>

    <!-- 状态信息 -->
    <p class="status-message">{{ statusMessage }}</p>

    <!-- 进度条 -->
    <div class="progress-container">
      <BaseProgress :percentage="progress" :show-text="false" />
      <div class="progress-text">{{ waitTime }} 秒 / 30 秒</div>
    </div>

    <!-- 匹配提示 -->
    <div class="matching-tips">
      <div class="tip-item">
        <span class="tip-icon">🎯</span>
        <span class="tip-text">正在为您寻找合适的对话者</span>
      </div>
      <div class="tip-item">
        <span class="tip-icon">⏱️</span>
        <span class="tip-text">请耐心等待...</span>
      </div>
      <div class="tip-item">
        <span class="tip-icon">🔒</span>
        <span class="tip-text">双方身份保密</span>
      </div>
    </div>

    <!-- 取消按钮 -->
    <BaseButton
      @click="handleCancel"
      class="btn-cancel"
      size="large"
      type="info"
    >
      取消匹配
    </BaseButton>
  </BaseCard>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { BaseCard, BaseProgress, BaseButton } from '@/components/common'

const emit = defineEmits<{
  (e: 'cancel'): void
}>()

// 状态
const waitTime = ref(0)
const progress = ref(0)
let timer: number | null = null

// 状态信息（根据等待时间变化）
const statusMessage = computed(() => {
  if (waitTime.value < 5) return '正在寻找对手...'
  if (waitTime.value < 10) return '稍等片刻，马上就好...'
  if (waitTime.value < 20) return '正在为您匹配最佳对手...'
  return '正在为您匹配对手...'
})

// 开始计时
onMounted(() => {
  timer = window.setInterval(() => {
    waitTime.value++
    progress.value = Math.min(100, (waitTime.value / 30) * 100)
  }, 1000)
})

// 清理计时器
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})

// 取消匹配
function handleCancel() {
  emit('cancel')
}

// 暴露方法给父组件
defineExpose({
  resetMatching: () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    waitTime.value = 0
    progress.value = 0
  }
})
</script>

<style scoped>
/* ==============================================
   MatchingSection 样式 - 使用主题系统
   ============================================== */

.matching-section {
  max-width: 800px;
  margin: 0 auto;
  padding: 60px 20px;
  text-align: center;
  background: var(--bg-surface);
  border-radius: var(--rounded-2xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-primary);
}

/* 匹配动画容器 */
.spinner-container {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 40px;
}

/* 主旋转器 */
.spinner {
  position: absolute;
  top: 0;
  left: 0;
  width: 120px;
  height: 120px;
  border: 6px solid var(--bg-tertiary);
  border-top-color: var(--color-primary-600);
  border-radius: var(--rounded-full);
  animation: spin 1s linear infinite;
}

/* 脉冲环 */
.pulse-ring {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 100px;
  height: 100px;
  border: 3px solid rgba(99, 102, 241, 0.3);
  border-radius: var(--rounded-full);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.1;
  }
}

/* 匹配标题 */
.matching-title {
  font-size: 28px;
  color: var(--text-primary);
  margin-bottom: 16px;
  font-weight: bold;
}

/* 状态信息 */
.status-message {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 40px;
}

/* 进度条容器 */
.progress-container {
  margin: 0 auto 40px;
  width: 100%;
  max-width: 400px;
}

.progress-text {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-top: 8px;
}

/* 匹配提示 */
.matching-tips {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 40px;
  flex-wrap: wrap;
}

.tip-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.tip-icon {
  font-size: 32px;
  animation: bounce 2s ease-in-out infinite;
}

.tip-item:nth-child(2) .tip-icon {
  animation-delay: 0.3s;
}

.tip-item:nth-child(3) .tip-icon {
  animation-delay: 0.6s;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

.tip-text {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 120px;
  line-height: 1.4;
}

/* 取消按钮 - 使用 BaseButton 组件，覆盖特定样式 */
.btn-cancel {
  width: 100%;
  max-width: 300px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .matching-section {
    padding: 40px 20px;
  }

  .spinner-container {
    width: 100px;
    height: 100px;
    margin-bottom: 30px;
  }

  .spinner {
    width: 100px;
    height: 100px;
    border-width: 5px;
  }

  .pulse-ring {
    top: 8px;
    left: 8px;
    width: 84px;
    height: 84px;
    border-width: 2px;
  }

  .matching-title {
    font-size: 24px;
  }

  .matching-tips {
    gap: 20px;
  }

  .tip-icon {
    font-size: 28px;
  }

  .tip-text {
    font-size: 12px;
    max-width: 100px;
  }
}
</style>