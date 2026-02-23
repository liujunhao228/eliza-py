<template>
  <div class="lobby-page">
    <!-- 规则说明（未匹配时显示） -->
    <RulesSection
      v-if="!isMatching"
      @start-match="handleStartMatch"
    />

    <!-- 匹配界面（匹配时显示） -->
    <MatchingSection
      v-else
      ref="matchingSectionRef"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useGameStore } from '@/stores/game'
import { startMatching, createMatchWebSocket } from '@/api/game'
import RulesSection from '@/components/Lobby/RulesSection.vue'
import MatchingSection from '@/components/Lobby/MatchingSection.vue'
import type { MatchResponse, IWebSocketManager } from '@/types'

const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()

// 状态
const isMatching = ref(false)
const matchingSectionRef = ref<InstanceType<typeof MatchingSection>>()
const wsManager = ref<IWebSocketManager | null>(null)

// 开始匹配
async function handleStartMatch() {
  if (!userStore.userId) {
    ElMessage.error('用户信息不存在，请重新登录')
    router.push('/login')
    return
  }

  try {
    // 调用匹配 API
    const response: MatchResponse = await startMatching(userStore.userId)

    // 保存匹配信息到游戏状态
    gameStore.setSession({
      id: response.session_id || 0,
      user_id: userStore.userId || 0,
      opponent_type: response.opponent_type || 'ai',
      opponent_id: 0,
      status: 'matching',
      is_honeypot: false,
      triggered_mid_game: false,
      meta_conversation_count: 0,
      match_duration: 0,
      started_at: undefined,
      ended_at: undefined,
      created_at: new Date().toISOString()
    })

    // 切换到匹配界面
    isMatching.value = true

    // 初始化 WebSocket 监听匹配结果
    initMatchWebSocket(response.session_id || 0)

  } catch (error: any) {
    ElMessage.error(error.message || '匹配失败，请重试')
  }
}

/**
 * 初始化匹配阶段的 WebSocket 连接
 */
function initMatchWebSocket(sessionId: number): void {
  // 创建 WebSocket 管理器
  wsManager.value = createMatchWebSocket(sessionId)

  // 注册消息处理器
  wsManager.value.on('match_found', handleMatchFound)
  wsManager.value.on('match_timeout', handleMatchTimeout)
  wsManager.value.on('error', handleError)

  // 连接
  wsManager.value.connect()
}

/**
 * 处理匹配成功（不区分真人/AI，保持匿名）
 */
function handleMatchFound(data: any): void {
  console.log('[Lobby] 匹配成功:', data)

  // 更新游戏状态（不存储对手类型，保持完全匿名）
  if (gameStore.sessionId) {
    gameStore.setSession({
      id: gameStore.sessionId,
      user_id: userStore.userId || 0,
      opponent_type: 'unknown', // 不泄露对手类型
      opponent_id: data.opponent?.id || 0,
      status: 'active',
      is_honeypot: false,
      triggered_mid_game: false,
      meta_conversation_count: 0,
      match_duration: 0,
      started_at: new Date().toISOString(),
      ended_at: undefined,
      created_at: new Date().toISOString()
    })
  }

  // 跳转到聊天页面（不透露任何信息）
  ElMessage.success('匹配成功！')
  router.push('/chat')
}

/**
 * 处理匹配超时（也当作匹配成功处理，不泄露信息）
 */
function handleMatchTimeout(data: any): void {
  console.log('[Lobby] 匹配超时:', data)

  // 更新游戏状态（不存储对手类型，保持完全匿名）
  if (gameStore.sessionId) {
    gameStore.setSession({
      id: gameStore.sessionId,
      user_id: userStore.userId || 0,
      opponent_type: 'unknown', // 不泄露对手类型
      opponent_id: 0,
      status: 'active',
      is_honeypot: false,
      triggered_mid_game: false,
      meta_conversation_count: 0,
      match_duration: 0,
      started_at: new Date().toISOString(),
      ended_at: undefined,
      created_at: new Date().toISOString()
    })
  }

  // 跳转到聊天页面（不透露任何信息）
  ElMessage.success('匹配成功！')
  router.push('/chat')
}

/**
 * 处理 WebSocket 错误
 */
function handleError(error: Event): void {
  console.error('[Lobby] WebSocket 错误:', error)
  ElMessage.warning('连接不稳定，但匹配仍在进行中...')
}

// 取消匹配
function handleCancel() {
  // 断开 WebSocket 连接
  if (wsManager.value) {
    wsManager.value.disconnect()
    wsManager.value = null
  }

  isMatching.value = false

  // 重置游戏状态
  gameStore.reset()

  // 重置匹配组件
  if (matchingSectionRef.value) {
    matchingSectionRef.value.resetMatching()
  }
}
</script>

<style scoped>
.lobby-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
}
</style>
