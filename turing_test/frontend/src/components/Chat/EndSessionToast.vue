<template>
  <Teleport to="body">
    <Transition name="slide-fade">
      <div v-if="visible" class="end-session-toast">
        <div class="toast-content">
          <!-- 图标 -->
          <div class="toast-icon">
            <el-icon :size="24"><Clock /></el-icon>
          </div>

          <!-- 文字信息 -->
          <div class="toast-message">
            <h4 class="toast-title">对话已结束</h4>
            <p class="toast-text">
              {{ countdown }} 秒后离开聊天室
            </p>
          </div>

          <!-- 进度条 -->
          <div class="toast-progress">
            <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Clock } from '@element-plus/icons-vue'

const props = defineProps<{
  duration?: number // 倒计时时长（秒）
  redirectUrl?: string // 跳转 URL
}>()

const emit = defineEmits<{
  (e: 'countdown-end'): void
}>()

const router = useRouter()

// 状态
const visible = ref(false)
const countdown = ref(props.duration ?? 5)
const elapsed = ref(0)

// 计算进度百分比
const progressPercent = computed(() => {
  const total = props.duration ?? 5
  return ((total - elapsed.value) / total) * 100
})

// 定时器
let timer: number | null = null

// 显示提示并开始倒计时
function show() {
  visible.value = true
  countdown.value = props.duration ?? 5
  elapsed.value = 0

  // 启动倒计时
  timer = window.setInterval(() => {
    elapsed.value += 1

    if (elapsed.value >= (props.duration ?? 5)) {
      // 倒计时结束
      finish()
    } else {
      countdown.value = (props.duration ?? 5) - elapsed.value
    }
  }, 1000)
}

// 倒计时结束
function finish() {
  stopTimer()
  visible.value = false
  emit('countdown-end')

  // 跳转到问卷页面
  const redirectUrl = props.redirectUrl ?? '/survey'
  router.push(redirectUrl)
}

// 停止定时器
function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// 隐藏提示
function hide() {
  stopTimer()
  visible.value = false
}

// 暴露方法给父组件
defineExpose({
  show,
  hide,
  finish
})

// 组件卸载时清理
onUnmounted(() => {
  stopTimer()
})
</script>

<style scoped>
.end-session-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: var(--bg-surface);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-primary);
  overflow: hidden;
  min-width: 320px;
  max-width: 90vw;
}

.toast-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  position: relative;
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--rounded-full);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  min-width: 0;
}

.toast-title {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.toast-text {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--bg-secondary);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-primary-gradient);
  transition: width 0.1s linear;
}

/* 过渡动画 */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.3s ease-in;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

/* 响应式设计 */
@media (max-width: 639px) {
  .end-session-toast {
    top: 10px;
    left: 10px;
    right: 10px;
    transform: none;
    min-width: auto;
    max-width: none;
  }

  .toast-content {
    padding: 12px 16px;
  }

  .toast-title {
    font-size: 15px;
  }

  .toast-text {
    font-size: 13px;
  }
}
</style>
