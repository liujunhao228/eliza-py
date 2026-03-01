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
      :wait-time="waitTime"
      :timeout-seconds="MATCH_TIMEOUT"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useGameStore } from '@/stores/game'
import { useToast } from '@/composables/useToast'
import { startMatching, getMatchResult, leaveMatch } from '@/api/game/match'
import RulesSection from '@/components/Lobby/RulesSection.vue'
import MatchingSection from '@/components/Lobby/MatchingSection.vue'

const { error: showError, success: showSuccess } = useToast()
const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()

// =============================================================================
// 匹配配置（前端）
// =============================================================================

/** 前端超时时间（秒）- 15 秒，给后端足够时间完成匹配（后端 8 秒超时 + 异步会话创建） */
const MATCH_TIMEOUT = 15

/** 轮询间隔（毫秒） */
const POLL_INTERVAL = 1000

// =============================================================================
// 状态
// =============================================================================

const isMatching = ref(false)
const waitTime = ref(0)

let pollTimer: number | null = null
let hasNavigated = false  // 防止重复跳转

// =============================================================================
// 匹配逻辑
// =============================================================================

/**
 * 开始匹配
 * 
 * 前端行为：
 * 1. 调用 POST /api/match/join 加入队列
 * 2. 如果直接返回结果（Bot 匹配），直接跳转
 * 3. 否则开始轮询，等待真人匹配或 Bot 降级
 */
async function handleStartMatch() {
  if (isMatching.value) return

  if (!userStore.userId) {
    showError('用户信息不存在，请重新登录')
    router.push('/login')
    return
  }

  isMatching.value = true
  waitTime.value = 0
  hasNavigated = false

  try {
    // 1. 加入队列
    const result = await startMatching(userStore.userId)

    // 2. 如果直接返回结果且 session_id > 0（Bot 匹配且会话已创建），直接跳转
    // 注意：session_id=0 表示匹配完成但会话尚未创建，需要进入轮询等待
    if (result.session_id && result.session_id > 0) {
      saveSession(result)
      showSuccess('匹配成功！')
      navigateToChat()
      return
    }

    // 3. 开始轮询（等待真人匹配、Bot 降级或会话创建完成）
    startPolling()

  } catch (error: any) {
    showError(error.message || '匹配失败，请重试')
    resetMatching()
  }
}

/**
 * 开始轮询
 *
 * 前端行为：
 * - 每 1 秒调用 GET /api/match/result
 * - 15 秒无结果 → 离开队列，返回大厅
 * - 有结果 → 跳转聊天
 */
function startPolling() {
  // waitTime 初始为 0，进度条从 0% 开始
  waitTime.value = 0

  pollTimer = window.setInterval(async () => {
    // 先递增等待时间
    waitTime.value++

    // 超时处理：离开队列，返回大厅
    if (waitTime.value >= MATCH_TIMEOUT) {
      stopPolling()
      await leaveMatch(userStore.userId!)
      showError('匹配超时，请重试')
      resetMatching()
      return
    }

    // 获取结果（可能来自真人匹配或 Bot 降级）
    try {
      const result = await getMatchResult(userStore.userId!)
      // 注意：session_id=0 表示匹配已完成但会话尚未创建，需要继续轮询
      // 只有 session_id > 0 才表示会话已创建完成，可以跳转
      if (result?.session_id && result.session_id > 0) {
        stopPolling()
        saveSession(result)
        showSuccess('匹配成功！')
        navigateToChat()
      }
    } catch (error) {
      // 404 表示结果还未生成，继续轮询
    }
  }, POLL_INTERVAL)
}

/**
 * 停止轮询
 */
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

/**
 * 保存会话信息
 */
function saveSession(result: { session_id: number; opponent_type: string; is_honeypot?: boolean }) {
  gameStore.setSession({
    id: result.session_id || 0,
    user_id: userStore.userId || 0,
    opponent_type: 'opponent',  // 不泄露对手身份
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
}

/**
 * 跳转到聊天页面
 */
function navigateToChat() {
  if (!hasNavigated) {
    hasNavigated = true
    router.push('/chat')
  }
}

/**
 * 重置匹配状态
 */
function resetMatching() {
  stopPolling()
  isMatching.value = false
  waitTime.value = 0
  hasNavigated = false
}

/**
 * 取消匹配
 */
async function handleCancel() {
  stopPolling()
  isMatching.value = false

  if (userStore.userId) {
    await leaveMatch(userStore.userId)
  }

  gameStore.reset()
}

/**
 * 退出登录
 */
function handleLogout() {
  userStore.logout()
  gameStore.reset()
  router.push('/login')
}

// =============================================================================
// 生命周期
// =============================================================================

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.lobby-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}
</style>
