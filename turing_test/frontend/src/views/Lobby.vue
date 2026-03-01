<template>
  <div class="lobby-page">
    <!-- 规则说明 -->
    <RulesSection
      @start-match="handleStartMatch"
      @logout="handleLogout"
    />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useGameStore } from '@/stores/game'
import { useToast } from '@/composables/useToast'
import RulesSection from '@/components/Lobby/RulesSection.vue'

const { error: showError } = useToast()
const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()

/**
 * 开始匹配 - 跳转到匹配页面
 */
const handleStartMatch = () => {
  if (!userStore.userId) {
    showError('用户信息不存在，请重新登录')
    router.push('/login')
    return
  }

  // 重置游戏状态
  gameStore.reset()

  // 跳转到匹配页面，由匹配页面负责执行匹配逻辑
  router.push('/matching')
}

/**
 * 退出登录
 */
const handleLogout = () => {
  userStore.logout()
  gameStore.reset()
  router.push('/login')
}
</script>

<style scoped>
.lobby-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}
</style>
