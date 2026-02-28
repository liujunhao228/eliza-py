<template>
  <div class="lobby-page">
    <!-- 规则说明（未匹配时显示） -->
    <RulesSection
      v-if="!isMatching"
      @start-match="handleStartMatch"
      @logout="handleLogout"
    />

    <!-- 匹配界面（匹配时显示） -->
    <MatchingSection
      v-else
      ref="matchingSectionRef"
      @cancel="handleCancel"
      @complete="handleComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useGameStore } from '@/stores/game'
import { useToast } from '@/composables/useToast'
import { startMatching, getMatchResult } from '@/api/game/match'
import RulesSection from '@/components/Lobby/RulesSection.vue'
import MatchingSection from '@/components/Lobby/MatchingSection.vue'

const { error: showError, success: showSuccess } = useToast()
const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()

// 状态
const isMatching = ref(false)
const matchingSectionRef = ref<InstanceType<typeof MatchingSection>>()
const isCompleting = ref(false)  // 防止重复请求
const matchTimeoutTimer = ref<number | null>(null)

// 开始匹配
async function handleStartMatch() {
  if (!userStore.userId) {
    showError('用户信息不存在，请重新登录')
    router.push('/login')
    return
  }

  try {
    // 切换到匹配界面
    isMatching.value = true

    // 调用 HTTP API 加入匹配队列（混合模式：优先真人，超时 AI）
    const matchResponse = await startMatching(userStore.userId)

    // 保存游戏状态
    gameStore.setSession({
      id: matchResponse.session_id || 0,
      user_id: userStore.userId || 0,
      opponent_type: matchResponse.opponent_type || 'unknown',
      opponent_id: 0,
      status: matchResponse.opponent_type === 'waiting' ? 'matching' : 'active',
      is_honeypot: matchResponse.is_honeypot || false,
      triggered_mid_game: false,
      meta_conversation_count: 0,
      match_duration: 0,
      started_at: new Date().toISOString(),
      ended_at: undefined,
      created_at: new Date().toISOString()
    })

    // 如果直接匹配成功（真人或 AI），直接跳转
    if (matchResponse.opponent_type && matchResponse.opponent_type !== 'waiting') {
      showSuccess(matchResponse.message || '匹配成功！')
      router.push('/chat')
      return
    }

    // 否则等待用户点击"完成"按钮获取结果
    // MatchingSection 会显示等待界面

  } catch (error: any) {
    showError(error.message || '匹配失败，请重试')
    handleCancel()
  }
}

/**
 * 匹配完成（获取最终匹配结果）
 */
async function handleComplete() {
  // 防止重复请求
  if (isCompleting.value) {
    return
  }

  if (!userStore.userId) return

  try {
    // 标记为正在处理
    isCompleting.value = true

    // 获取匹配结果（可能返回真人或 AI）
    const result = await getMatchResult(userStore.userId)

    // 更新游戏状态
    gameStore.setSession({
      id: result.session_id || 0,
      user_id: userStore.userId || 0,
      opponent_type: 'unknown',  // 不泄露对手类型
      opponent_id: 0,
      status: 'active',
      is_honeypot: result.is_honeypot || false,
      triggered_mid_game: false,
      meta_conversation_count: 0,
      match_duration: 0,
      started_at: new Date().toISOString(),
      ended_at: undefined,
      created_at: new Date().toISOString()
    })

    // 跳转到聊天页面
    showSuccess(result.message || '匹配成功！')
    router.push('/chat')

  } catch (error: any) {
    console.error('[Lobby] 获取匹配结果失败:', error)
    showError(error.message || '获取匹配结果失败，请重试')
  } finally {
    isCompleting.value = false
  }
}

// 取消匹配
function handleCancel() {
  isMatching.value = false
  gameStore.reset()

  // 清除定时器
  if (matchTimeoutTimer.value) {
    window.clearTimeout(matchTimeoutTimer.value)
    matchTimeoutTimer.value = null
  }

  if (matchingSectionRef.value) {
    matchingSectionRef.value.resetMatching()
  }
}

// 退出登录
function handleLogout() {
  // 调用 store 的 logout 方法
  userStore.logout()
  gameStore.reset()
  
  // 跳转到登录页
  router.push('/login')
}
</script>

<style scoped>
.lobby-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}
</style>
