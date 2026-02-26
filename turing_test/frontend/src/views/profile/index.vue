<template>
  <div class="profile-container">
    <!-- 头部 -->
    <ProfileHeader @logout="handleLogout" />

    <!-- 加载状态 -->
    <BaseLoading v-if="loading" :loading="true" text="加载中..." />

    <!-- 错误状态 -->
    <BaseEmpty
      v-else-if="error"
      :title="error"
      size="medium"
    >
      <template #action>
        <BaseButton type="primary" @click="loadData">重试</BaseButton>
      </template>
    </BaseEmpty>

    <!-- 主要内容 -->
    <div v-else class="profile-content">
      <!-- 用户信息卡片 -->
      <UserInfoCard
        :nickname="userStore.nickname"
        :inviteCode="userStore.inviteCode"
        :score="userStore.score"
      />

      <!-- 统计卡片 -->
      <StatsSection v-if="stats" :stats="stats" :score-history="scoreHistory" />

      <!-- 历史记录 -->
      <HistorySection
        :history="history"
        @go-to-history="goToHistory"
        @go-to-lobby="goToLobby"
        @view-detail="viewSessionDetail"
      />

      <!-- 返回按钮 -->
      <ActionButtons @go-to-lobby="goToLobby" />
    </div>

    <!-- 详情对话框 -->
    <SessionDetailModal
      v-model="showDetailModal"
      :session="selectedSession"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { BaseButton, BaseLoading, BaseEmpty } from '@/components/common'
import ProfileHeader from './components/ProfileHeader.vue'
import UserInfoCard from './components/UserInfoCard.vue'
import StatsSection from './components/StatsSection/index.vue'
import HistorySection from './components/HistorySection/index.vue'
import ActionButtons from './components/ActionButtons.vue'
import SessionDetailModal from './components/SessionDetailModal.vue'
import { useProfileData } from './composables/useProfileData'
import type { Session } from '@/types'

const router = useRouter()
const userStore = useUserStore()

// 使用 composable 管理数据
const { loading, error, stats, history, scoreHistory, load } = useProfileData()

// 状态
const showDetailModal = ref(false)
const selectedSession = ref<Session | null>(null)

// 加载数据
const loadData = async () => {
  const userId = userStore.userId
  if (!userId) {
    error.value = '用户未登录'
    return
  }

  try {
    await load(String(userId))
    if (stats.value) {
      userStore.setStats(stats.value)
    }
  } catch (err: any) {
    console.error('加载用户数据失败:', err)
    // error 已由 composable 设置
  }
}

// 查看对话详情
const viewSessionDetail = (session: Session) => {
  selectedSession.value = session
  showDetailModal.value = true
}

// 返回大厅
const goToLobby = () => {
  router.push('/lobby')
}

// 查看历史会话
const goToHistory = () => {
  router.push('/history')
}

// 退出登录
const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

// 生命周期
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

.profile-content {
  display: flex;
  flex-direction: column;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-container {
    padding: 15px;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }
}
</style>
