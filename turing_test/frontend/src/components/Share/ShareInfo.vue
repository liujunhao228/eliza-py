<template>
  <div class="share-info">
    <div class="info-row">
      <span class="label">分享链接：</span>
      <div class="link-container">
        <input
          type="text"
          :value="shareInfo.share_url"
          readonly
          class="share-link-input"
        />
        <button class="btn-copy" @click="handleCopy">复制</button>
      </div>
    </div>

    <div class="info-row">
      <span class="label">状态：</span>
      <span :class="shareInfo.is_expired ? 'expired' : 'active'">
        {{ shareInfo.is_expired ? '已过期' : '有效' }}
      </span>
    </div>

    <div class="info-row" v-if="shareInfo.expires_at">
      <span class="label">过期时间：</span>
      <span>{{ formatDate(shareInfo.expires_at) }}</span>
    </div>

    <div class="info-row">
      <span class="label">访问密码：</span>
      <span>{{ shareInfo.has_password ? '已设置' : '无' }}</span>
    </div>

    <div class="info-row">
      <span class="label">浏览次数：</span>
      <span>{{ shareInfo.view_count ?? 0 }} 次</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ShareInfo } from '@/api/history'

const props = defineProps<{
  shareInfo: ShareInfo
}>()

const emit = defineEmits<{
  copy: [url: string]
}>()

const handleCopy = () => {
  emit('copy', props.shareInfo.share_url)
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.share-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 15px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-row .label {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 14px;
}

.info-row span:last-child {
  font-size: 14px;
  color: var(--text-primary);
}

.link-container {
  display: flex;
  gap: 8px;
  flex: 1;
  margin-left: 10px;
}

.share-link-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
}

.btn-copy {
  padding: 6px 12px;
  background: var(--color-primary-500);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  transition: background 0.2s;
}

.btn-copy:hover {
  background: var(--color-primary-600);
}

.active {
  color: var(--color-green-600);
  font-weight: 500;
}

.expired {
  color: var(--color-red-600);
  font-weight: 500;
}
</style>
