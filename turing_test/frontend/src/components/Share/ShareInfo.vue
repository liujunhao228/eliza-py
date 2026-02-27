<template>
  <div class="share-info">
    <!-- 分享链接 -->
    <div class="info-row link-row">
      <div class="info-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
        </svg>
        分享链接
      </div>
      <div class="link-container">
        <input
          type="text"
          :value="shareInfo.share_url"
          readonly
          class="share-link-input"
          aria-label="分享链接"
        />
        <button class="btn-copy" @click="handleCopy" aria-label="复制链接">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
          </svg>
          复制
        </button>
      </div>
    </div>

    <!-- 状态 -->
    <div class="info-row">
      <div class="info-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        状态
      </div>
      <span class="status-badge" :class="shareInfo.is_expired ? 'expired' : 'active'">
        <span class="status-dot"></span>
        {{ shareInfo.is_expired ? '已过期' : '有效' }}
      </span>
    </div>

    <!-- 过期时间 -->
    <div class="info-row" v-if="shareInfo.expires_at">
      <div class="info-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        过期时间
      </div>
      <span class="info-value">{{ formatDate(shareInfo.expires_at) }}</span>
    </div>

    <!-- 访问密码 -->
    <div class="info-row">
      <div class="info-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0110 0v4" />
        </svg>
        访问密码
      </div>
      <span class="info-value" :class="shareInfo.has_password ? 'has-password' : 'no-password'">
        <span v-if="shareInfo.has_password" class="password-indicator">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 15v2M12 9v2m0-4h.01" />
            <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          已设置
        </span>
        <span v-else class="no-password-text">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M18.36 6.64a9 9 0 11-12.73 0" />
            <line x1="12" y1="2" x2="12" y2="12" />
          </svg>
          无
        </span>
      </span>
    </div>

    <!-- 浏览次数 -->
    <div class="info-row">
      <div class="info-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        浏览次数
      </div>
      <span class="info-value view-count">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
        {{ shareInfo.view_count ?? 0 }} 次
      </span>
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
/* ===== CSS 变量 ===== */
.share-info {
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-success: #10b981;
  --color-error: #ef4444;
  --color-text-primary: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-tertiary: #9ca3af;
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f9fafb;
  --color-bg-tertiary: #f3f4f6;
  --color-border: #e5e7eb;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

.share-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

/* ===== 信息行 ===== */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.info-row.link-row {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-label svg {
  width: 16px;
  height: 16px;
  color: var(--color-primary);
}

.info-value {
  font-size: 14px;
  color: var(--color-text-primary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-value svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
}

/* ===== 链接容器 ===== */
.link-container {
  display: flex;
  gap: 8px;
}

.share-link-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-family: monospace;
  transition: all 0.2s ease;
  cursor: pointer;
}

.share-link-input:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-text-tertiary);
}

.share-link-input:focus {
  outline: none;
  border-color: var(--color-primary);
  background: var(--color-bg-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* ===== 复制按钮 ===== */
.btn-copy {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.btn-copy svg {
  width: 16px;
  height: 16px;
}

.btn-copy:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.btn-copy:active {
  transform: translateY(0);
}

/* ===== 状态徽章 ===== */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.1); }
}

.status-badge.active {
  background: linear-gradient(135deg, var(--color-green-50) 0%, var(--color-green-100) 100%);
  color: var(--color-green-800);
  border: 1px solid var(--color-green-300);
}

.status-badge.active .status-dot {
  background: var(--color-success);
}

.status-badge.expired {
  background: linear-gradient(135deg, var(--color-amber-50) 0%, var(--color-amber-100) 100%);
  color: var(--color-amber-800);
  border: 1px solid var(--color-amber-300);
}

.status-badge.expired .status-dot {
  background: var(--color-error);
  animation: none;
  opacity: 0.6;
}

/* ===== 密码状态 ===== */
.password-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-success);
}

.password-indicator svg {
  width: 16px;
  height: 16px;
  color: var(--color-success);
}

.no-password-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-tertiary);
}

.no-password-text svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
}

/* ===== 浏览次数 ===== */
.view-count {
  color: var(--color-text-primary);
}

.view-count svg {
  color: var(--color-text-tertiary);
}

/* ===== 暗色模式支持 ===== */
@media (prefers-color-scheme: dark) {
  .share-info {
    --color-primary: #60a5fa;
    --color-primary-hover: #3b82f6;
    --color-success: #34d399;
    --color-error: #f87171;
    --color-text-primary: #f9fafb;
    --color-text-secondary: #9ca3af;
    --color-text-tertiary: #6b7280;
    --color-bg-primary: #1f2937;
    --color-bg-secondary: #111827;
    --color-bg-tertiary: #030712;
    --color-border: #374151;
  }

  .status-badge.active {
    background: linear-gradient(135deg, var(--color-green-900) 0%, var(--color-green-800) 100%);
    color: var(--color-green-200);
    border-color: var(--color-green-600);
  }

  .status-badge.expired {
    background: linear-gradient(135deg, var(--color-amber-900) 0%, var(--color-amber-800) 100%);
    color: var(--color-amber-200);
    border-color: var(--color-amber-600);
  }

  .share-link-input:hover {
    background: var(--color-bg-tertiary);
  }
}

/* ===== 响应式设计 ===== */
@media (max-width: 480px) {
  .share-info {
    padding: 16px;
  }

  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .link-container {
    width: 100%;
  }

  .share-link-input {
    font-size: 12px;
    padding: 8px 10px;
  }

  .btn-copy {
    width: 100%;
    justify-content: center;
  }
}
</style>
