<template>
  <div class="matching-page">
    <div class="matching-container">
      <!-- 匹配动画 -->
      <MatchingSection
        :wait-time="waitTime"
        :is-connecting="!isConnected"
        @cancel="handleCancel"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMatch } from '@/composables/useMatch'
import { useToast } from '@/composables/useToast'
import MatchingSection from '@/components/Lobby/MatchingSection.vue'

const router = useRouter()
const { error: showError } = useToast()

const {
  status,
  waitTime,
  isConnected,
  error,
  start,
  cancel
} = useMatch()

let hasNavigated = false

// 监听状态变化，自动跳转或处理错误
watch(status, (newStatus) => {
  // 防止重复跳转
  if (hasNavigated) return

  if (newStatus === 'matched') {
    hasNavigated = true
    // 匹配成功，自动跳转到聊天页面
    router.push('/chat')
  } else if (newStatus === 'failed') {
    hasNavigated = true
    // 匹配失败，显示错误并返回大厅
    if (error.value) {
      showError(error.value)
    }
    router.push('/lobby')
  }
})

// 处理取消
const handleCancel = async () => {
  if (hasNavigated) return
  hasNavigated = true
  await cancel()
  router.push('/lobby')
}

// 组件挂载时开始匹配
await start()
</script>

<style scoped>
.matching-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}

.matching-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}
</style>
