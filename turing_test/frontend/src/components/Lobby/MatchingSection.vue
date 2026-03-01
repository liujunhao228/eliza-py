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
    <p class="status-message">正在为您寻找合适的对话者</p>

    <!-- 连接状态提示 -->
    <div v-if="isConnecting" class="connecting-tip">
      <span class="tip-icon">📡</span>
      <span class="tip-text">正在连接服务器...</span>
    </div>

    <!-- 进度条 -->
    <div class="progress-container">
      <BaseProgress
        :percentage="progress"
        :show-text="false"
        size="large"
        type="primary"
        striped
        animated
      />
      <div class="progress-text">{{ waitTime }} 秒 / {{ timeoutSeconds }} 秒</div>
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
      @click="$emit('cancel')"
      class="btn-cancel"
      size="large"
      type="info"
    >
      取消匹配
    </BaseButton>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BaseCard, BaseProgress, BaseButton } from '@/components/common'
import { MATCH_CONFIG } from '@/stores/match'

interface Props {
  /** 等待时间（秒） */
  waitTime: number
  /** 是否正在连接 WebSocket */
  isConnecting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  waitTime: 0,
  isConnecting: false
})

defineEmits<{
  (e: 'cancel'): void
}>()

// 超时时间（秒）- 从配置读取
const timeoutSeconds = MATCH_CONFIG.TIMEOUT_SECONDS

// 进度百分比
const progress = computed(() => {
  return Math.min(100, (props.waitTime / timeoutSeconds) * 100)
})
</script>

<style scoped>
.matching-section {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding: 60px 20px;
  text-align: center;
  background: var(--bg-surface);
  border-radius: var(--rounded-2xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-primary);
}

.spinner-container {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 40px;
}

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
  animation-fill-mode: forwards;
}

.pulse-ring {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 100px;
  height: 100px;
  border: 3px solid rgba(99, 102, 241, 0.3);
  border-radius: var(--rounded-full);
  animation: pulse 2s ease-in-out infinite;
  animation-fill-mode: forwards;
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

.matching-title {
  font-size: 28px;
  color: var(--text-primary);
  margin-bottom: 16px;
  font-weight: bold;
}

.status-message {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.connecting-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border-radius: var(--rounded-lg);
  margin-bottom: 24px;
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
}

.connecting-tip .tip-icon {
  font-size: 18px;
}

.connecting-tip .tip-text {
  font-size: 13px;
  color: var(--text-secondary);
}

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

.btn-cancel {
  width: 100%;
  max-width: 300px;
}

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
