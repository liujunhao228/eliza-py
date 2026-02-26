<template>
  <div class="user-info-card">
    <div class="user-avatar">
      <div class="avatar-placeholder">
        {{ nickname.charAt(0).toUpperCase() }}
      </div>
    </div>
    <div class="user-details">
      <h2>{{ nickname }}</h2>
      <p>邀请码：{{ inviteCode }}</p>
      <p>当前积分：<span class="current-score">{{ score }}</span></p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  nickname: string
  inviteCode: string
  score: number
}>()
</script>

<style scoped>
.user-info-card {
  display: flex;
  align-items: center;
  background: var(--color-primary-gradient);
  color: var(--bg-surface);
  padding: 30px;
  border-radius: var(--rounded-2xl);
  margin-bottom: 30px;
  box-shadow: var(--shadow-lg);
}

.user-avatar {
  margin-right: 20px;
}

.avatar-placeholder {
  width: 80px;
  height: 80px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: var(--rounded-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
}

.user-details h2 {
  margin: 0 0 10px 0;
  font-size: 24px;
}

.user-details p {
  margin: 5px 0;
  opacity: 0.9;
  font-size: 14px;
}

.current-score {
  font-size: 28px;
  font-weight: bold;
  margin-left: 10px;
}
</style>
