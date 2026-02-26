<template>
  <div class="profile-header">
    <h1>📊 我的战绩</h1>
    <BaseButton type="info" size="small" @click="handleLogout">
      🚪 退出登录
    </BaseButton>
  </div>
</template>

<script setup lang="ts">
import { BaseButton } from '@/components/common'

const emit = defineEmits<{
  logout: []
}>()

const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    emit('logout')
  }
}
</script>

<style scoped>
.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.profile-header h1 {
  font-size: 28px;
  font-weight: bold;
  color: var(--text-primary);
  margin: 0;
}
</style>
