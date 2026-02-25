<template>
  <div v-if="error" class="error-boundary">
    <div class="error-content">
      <div class="error-icon">
        <el-icon><CircleClose /></el-icon>
      </div>
      <h2 class="error-title">出错了</h2>
      <p class="error-message">{{ errorMessage }}</p>
      <p v-if="errorDetail" class="error-detail">{{ errorDetail }}</p>
      <div class="error-actions">
        <BaseButton type="primary" @click="handleRetry">
          <el-icon><Refresh /></el-icon>
          重试
        </BaseButton>
        <BaseButton type="default" @click="handleGoHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </BaseButton>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { CircleClose, Refresh, HomeFilled } from '@element-plus/icons-vue'
import { BaseButton } from '@/components/common'
import { useRouter } from 'vue-router'
import { logger } from '@/utils/logger'

interface Props {
  /** 自定义错误消息 */
  customMessage?: string
  /** 是否显示详情 */
  showDetail?: boolean
  /** 重试回调 */
  onRetry?: () => void | Promise<void>
}

const props = withDefaults(defineProps<Props>(), {
  customMessage: '',
  showDetail: false,
  onRetry: undefined
})

const router = useRouter()
const error = ref<Error | null>(null)
const errorMessage = ref<string>('')
const errorDetail = ref<string>('')

const log = logger.createChild('ErrorBoundary')

// 捕获子组件错误
onErrorCaptured((err, instance, info) => {
  log.error(`捕获组件错误:`, {
    error: err.message,
    component: (instance?.$options as any)?.name || 'Unknown',
    info
  })

  error.value = err
  errorMessage.value = props.customMessage || err.message || '页面加载失败'
  
  if (props.showDetail && import.meta.env.DEV) {
    errorDetail.value = `${info}: ${err.stack || ''}`
  }

  // 阻止错误继续传播
  return false
})

/**
 * 处理重试
 */
async function handleRetry() {
  if (props.onRetry) {
    try {
      await props.onRetry()
      error.value = null
      errorMessage.value = ''
      errorDetail.value = ''
    } catch (err) {
      log.error('重试失败:', err)
    }
    return
  }

  // 默认重试：刷新页面
  window.location.reload()
}

/**
 * 返回首页
 */
function handleGoHome() {
  error.value = null
  errorMessage.value = ''
  errorDetail.value = ''
  router.push('/')
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 40px 20px;
  background: var(--bg-surface);
  border-radius: var(--rounded-xl);
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
}

.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  max-width: 400px;
}

.error-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-error-100);
  border-radius: var(--rounded-full);
  color: var(--color-error);
  font-size: 40px;
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-10px);
  }
  75% {
    transform: translateX(10px);
  }
}

.error-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.error-message {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.error-detail {
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--bg-secondary);
  padding: 12px;
  border-radius: var(--rounded-md);
  word-break: break-all;
  text-align: left;
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .error-boundary {
    min-height: 300px;
    padding: 20px 16px;
  }

  .error-icon {
    width: 60px;
    height: 60px;
    font-size: 30px;
  }

  .error-title {
    font-size: 20px;
  }

  .error-message {
    font-size: 14px;
  }

  .error-actions {
    flex-direction: column;
    width: 100%;
  }

  .error-actions .base-button {
    width: 100%;
  }
}
</style>
