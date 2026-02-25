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
import { createMatchWebSocket, matchAI } from '@/api/game'
import RulesSection from '@/components/Lobby/RulesSection.vue'
import MatchingSection from '@/components/Lobby/MatchingSection.vue'
import type { IWebSocketManager } from '@/types'

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
    // 切换到匹配界面
    isMatching.value = true

    // 初始化 WebSocket 监听匹配结果
    initMatchWebSocket()

  } catch (error: any) {
    ElMessage.error(error.message || '匹配失败，请重试')
  }
}

/**
 * 初始化匹配阶段的 WebSocket 连接
 */
function initMatchWebSocket(): void {
  if (!userStore.userId) return

  // 创建 WebSocket 管理器
  wsManager.value = createMatchWebSocket(userStore.userId)

  // 注册消息处理器
  wsManager.value.on('match_found', handleMatchFound)
  wsManager.value.on('match_timeout', handleMatchTimeout)
  wsManager.value.on('error', handleError)
  wsManager.value.on('status', handleStatusUpdate)
  wsManager.value.on('connected', handleConnected)
  wsManager.value.on('pong', () => {}) // 忽略心跳响应

  // 连接
  wsManager.value.connect()
}

/**
 * 处理 WebSocket 连接建立
 */
function handleConnected(data: any): void {
  console.log('[Lobby] WebSocket 连接已建立:', data)
  // 连接建立后，发送 join 消息加入匹配队列
  if (wsManager.value) {
    wsManager.value.send('join', {})
  }

  // 保存匹配信息到游戏状态
  gameStore.setSession({
    id: 0, // 初始为 0，等待匹配成功后更新
    user_id: userStore.userId || 0,
    opponent_type: 'unknown',
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
}

/**
 * 处理匹配状态更新
 */
function handleStatusUpdate(data: any): void {
  console.log('[Lobby] 匹配状态更新:', data)
  // 可以在这里更新 UI 显示队列位置等信息
}

/**
 * 处理匹配成功（不区分真人/AI，保持匿名）
 */
function handleMatchFound(data: any): void {
  console.log('[Lobby] 匹配成功:', data)

  // 更新游戏状态（不存储对手类型，保持完全匿名）
  gameStore.setSession({
    id: data.session_id || 0,
    user_id: userStore.userId || 0,
    opponent_type: 'unknown', // 不泄露对手类型
    opponent_id: data.opponent?.id || 0,
    status: 'active',
    is_honeypot: data.is_honeypot || false,
    triggered_mid_game: false,
    meta_conversation_count: 0,
    match_duration: 0,
    started_at: new Date().toISOString(),
    ended_at: undefined,
    created_at: new Date().toISOString()
  })

  // 跳转到聊天页面（不透露任何信息）
  ElMessage.success('匹配成功！')
  router.push('/chat')
}

/**
 * 处理匹配超时（也当作匹配成功处理，不泄露信息）
 */
async function handleMatchTimeout(data: any): Promise<void> {
  console.log('[Lobby] 匹配超时:', data)

  try {
    // 匹配超时后，调用后端 API 创建 AI 对战会话
    const response = await matchAI(userStore.userId || 0)

    if (response.session_id) {
      // 更新游戏状态（不存储对手类型，保持完全匿名）
      gameStore.setSession({
        id: response.session_id,
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

      // 提示用户并跳转到聊天页面
      ElMessage.info('匹配超时，已为您自动匹配 AI 对手')
      router.push('/chat')
    } else {
      ElMessage.error('创建 AI 会话失败，请重试')
      handleCancel()
    }
  } catch (error: any) {
    console.error('[Lobby] 创建 AI 会话失败:', error)
    ElMessage.error('创建 AI 会话失败，请重试')
    handleCancel()
  }
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
/* ==============================================
   Lobby 视图样式 - 使用主题系统
   ============================================== */

.lobby-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}
</style>
