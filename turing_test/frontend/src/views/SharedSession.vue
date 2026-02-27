<template>
  <div class="shared-session-page">
    <!-- 头部导航 -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" @click="goBack" role="button" tabindex="0" @keydown.enter="goBack" @keydown.space.prevent="goBack" aria-label="返回">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <h1>
            <svg class="share-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
            </svg>
            公开分享的会话
          </h1>
        </div>
        <span class="share-badge" v-if="shareInfo && !shareInfo.is_expired">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          已验证分享
        </span>
      </div>
    </header>

    <main class="main-content">
      <!-- 加载状态 - 骨架屏 -->
      <div v-if="loadingShare" class="loading-container">
        <div class="skeleton-card skeleton-info-card"></div>
        <div class="skeleton-card skeleton-messages-card"></div>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="shareError" class="error-container">
        <div class="error-card">
          <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          <p class="error-message">{{ shareError }}</p>
          <button v-if="needsPassword" class="btn btn-primary" @click="showPasswordModal = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            输入密码
          </button>
        </div>
      </div>

      <!-- 分享信息 -->
      <template v-else-if="shareInfo">
        <!-- 过期提示 -->
        <div v-if="shareInfo.is_expired" class="expired-banner" role="alert">
          <svg class="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <path d="M12 9v4M12 17h.01" />
          </svg>
          <span>此分享已过期，无法查看详细内容</span>
        </div>

        <!-- 会话信息卡片 -->
        <div v-else class="session-info-card" :class="{ 'card-enter': !loadingShare }">
          <div class="card-header">
            <h2>会话详情</h2>
            <div class="opponent-badge" :class="shareInfo.opponent_type === 'human' ? 'human' : 'ai'">
              <svg v-if="shareInfo.opponent_type === 'human'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <rect x="4" y="4" width="16" height="16" rx="2" />
                <path d="M9 9h6M9 13h6M9 17h6" />
              </svg>
              {{ shareInfo.opponent_type === 'human' ? '真人对手' : 'AI 对手' }}
            </div>
          </div>
          
          <div class="info-grid">
            <div class="info-item">
              <div class="info-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M12 20V10M18 20V4M6 20v-4" />
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">轮数</span>
                <span class="info-value">{{ shareInfo.turn_count }} 回合</span>
              </div>
            </div>

            <div class="info-item" v-if="shareInfo.final_score !== null">
              <div class="info-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">得分</span>
                <span class="info-value score" :class="shareInfo.final_score > 0 ? 'positive' : 'negative'">
                  {{ shareInfo.final_score > 0 ? '+' : '' }}{{ shareInfo.final_score }}
                </span>
              </div>
            </div>

            <div class="info-item" v-if="shareInfo.is_correct !== null">
              <div class="info-icon">
                <svg v-if="shareInfo.is_correct" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                  <path d="M22 4L12 14.01l-3-3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M15 9l-6 6M9 9l6 6" />
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">判断结果</span>
                <span class="info-value" :class="shareInfo.is_correct ? 'correct-text' : 'incorrect-text'">
                  {{ shareInfo.is_correct ? '判断正确' : '判断错误' }}
                </span>
              </div>
            </div>

            <div class="info-item">
              <div class="info-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <path d="M16 2v4M8 2v4M3 10h18" />
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">分享时间</span>
                <span class="info-value">{{ formatDate(shareInfo.started_at) }}</span>
              </div>
            </div>

            <div class="info-item">
              <div class="info-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">浏览次数</span>
                <span class="info-value">{{ shareInfo.view_count }} 次</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 聊天记录 -->
        <div v-if="messages.length > 0" class="messages-container card-enter">
          <div class="messages-header">
            <h2>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
              聊天记录
            </h2>
            <span class="message-count">{{ messages.length }} 条消息</span>
          </div>
          
          <div class="messages-list">
            <div
              v-for="(message, index) in messages"
              :key="message.id"
              class="message"
              :class="[
                message.sender === 'user' ? 'message-user' : 'message-opponent',
                'message-enter'
              ]"
              :style="{ animationDelay: `${index * 50}ms` }"
            >
              <div class="message-avatar" :class="message.sender === 'user' ? 'user-avatar' : 'opponent-avatar'">
                <svg v-if="message.sender === 'user'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                  <path d="M9 9h6M9 13h6M9 17h6" />
                </svg>
              </div>
              
              <div class="message-body">
                <div class="message-header">
                  <span class="message-sender-name">
                    {{ message.sender === 'user' ? '你' : '对手' }}
                  </span>
                  <span v-if="message.is_meta_conversation" class="meta-tag">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                      <path d="M12 2a3 3 0 00-3 3v7a3 3 0 006 0V5a3 3 0 00-3-3z" />
                      <path d="M19 10v2a7 7 0 01-14 0v-2" />
                      <line x1="12" y1="19" x2="12" y2="23" />
                      <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                    元对话
                  </span>
                  <span class="message-time">{{ formatMessageTime(message.created_at) }}</span>
                </div>
                <div class="message-content">{{ message.content }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 加载消息状态 -->
        <div v-else-if="loadingMessages" class="loading-container">
          <div class="loading-spinner">
            <svg class="spinner" viewBox="0 0 24 24" fill="none" aria-label="加载中">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60 40" opacity="0.3" />
              <path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
            </svg>
            <span>加载聊天记录...</span>
          </div>
        </div>
      </template>
    </main>

    <!-- 页脚 -->
    <footer class="page-footer">
      <div class="footer-content">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        <p>此会话由用户分享 · 仅供学习交流</p>
      </div>
    </footer>

    <!-- 密码输入对话框 -->
    <Transition name="modal">
      <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div class="modal">
          <div class="modal-header">
            <div class="modal-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0110 0v4" />
              </svg>
              <h2 id="modal-title">需要密码</h2>
            </div>
            <button class="close-btn" @click="showPasswordModal = false" aria-label="关闭对话框">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <p class="modal-description">此分享受密码保护，请输入访问密码</p>
            <div class="input-group">
              <input
                v-model="password"
                type="password"
                placeholder="请输入密码"
                class="password-input"
                @keyup.enter="verifyPassword"
                aria-label="访问密码"
              />
              <button v-if="password" class="clear-btn" @click="password = ''" aria-label="清除密码">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p v-if="passwordError" class="password-error" role="alert">{{ passwordError }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showPasswordModal = false">取消</button>
            <button class="btn btn-primary" @click="verifyPassword" :disabled="verifying || !password">
              <svg v-if="verifying" class="btn-spinner" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60 40" opacity="0.3" />
                <path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
              </svg>
              {{ verifying ? '验证中...' : '验证' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/history'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const historyStore = useHistoryStore()
const { success, error: showError } = useToast()

const shareToken = ref<string>(route.params.token as string)

const loadingShare = ref(true)
const loadingMessages = ref(false)
const shareError = ref<string | null>(null)
const needsPassword = ref(false)
const showPasswordModal = ref(false)
const password = ref('')
const passwordError = ref<string | null>(null)
const verifying = ref(false)
const verifyAttempt = ref(0)

const shareInfo = computed(() => historyStore.currentShare)
const messages = computed(() => historyStore.currentMessages)

// SEO Meta 标签更新
function updateMetaTags() {
  // 标题
  document.title = shareInfo.value
    ? `会话 #${shareInfo.value.session_id} - ${shareInfo.value.opponent_type === 'human' ? '真人' : 'AI'}对手 - 图灵测试分享`
    : '共享会话 - 图灵测试'

  // Meta description
  let metaDescription = document.querySelector('meta[name="description"]')
  const description = shareInfo.value
    ? `图灵测试会话记录：${shareInfo.value.turn_count}轮对话，${shareInfo.value.opponent_type === 'human' ? '真人' : 'AI'}对手`
    : '查看分享的图灵测试会话记录'

  if (!metaDescription) {
    metaDescription = document.createElement('meta')
    metaDescription.setAttribute('name', 'description')
    document.head.appendChild(metaDescription)
  }
  metaDescription.setAttribute('content', description)

  // Open Graph tags
  const ogTags = [
    { property: 'og:title', content: shareInfo.value ? `会话 #${shareInfo.value.session_id}` : '共享会话' },
    { property: 'og:description', content: description },
    { property: 'og:type', content: 'website' },
    { property: 'og:site_name', content: '图灵测试' }
  ]

  ogTags.forEach(({ property, content }) => {
    let tag = document.querySelector(`meta[property="${property}"]`)
    if (!tag) {
      tag = document.createElement('meta')
      tag.setAttribute('property', property)
      document.head.appendChild(tag)
    }
    tag.setAttribute('content', content)
  })
}

// 监听 shareInfo 变化，更新 Meta 标签
watch(shareInfo, () => {
  if (shareInfo.value) {
    updateMetaTags()
  }
}, { immediate: true })

// 格式化日期
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 格式化消息时间
function formatMessageTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取分享信息
async function fetchShareInfo() {
  loadingShare.value = true
  shareError.value = null

  try {
    const info = await historyStore.fetchShareInfo(shareToken.value)
    if (info.requires_password) {
      needsPassword.value = true
      showPasswordModal.value = true
    } else if (!info.is_expired) {
      // 无需密码且未过期，加载消息
      await fetchMessages()
    } else {
      shareError.value = '此分享已过期'
      showError('此分享已过期')
    }
  } catch (e: any) {
    const msg = e.message || '加载失败'
    if (msg.includes('密码') || msg.includes('password')) {
      needsPassword.value = true
      showPasswordModal.value = true
    } else if (msg.includes('过期')) {
      shareError.value = '此分享已过期'
      showError('此分享已过期')
    } else {
      shareError.value = msg
      showError(msg)
    }
  } finally {
    loadingShare.value = false
  }
}

// 验证密码
async function verifyPassword() {
  if (!password.value) {
    passwordError.value = '请输入密码'
    return
  }

  if (verifying.value) return  // 防止重复提交
  verifyAttempt.value += 1

  // 限制重试次数
  if (verifyAttempt.value >= 5) {
    passwordError.value = '重试次数过多，请稍后再试'
    showError('重试次数过多，请稍后再试')
    return
  }

  verifying.value = true
  passwordError.value = null

  try {
    const result = await historyStore.verifySharePassword(shareToken.value, password.value)
    if (result.success) {
      showPasswordModal.value = false
      success('密码验证成功')
      await fetchMessages()
    }
  } catch (e: any) {
    passwordError.value = e.message || '密码错误'
    showError(e.message || '密码错误')
    // 限制重试次数
    if (verifyAttempt.value >= 5) {
      passwordError.value = '重试次数过多，请稍后再试'
    }
  } finally {
    verifying.value = false
  }
}

// 获取消息
async function fetchMessages() {
  loadingMessages.value = true
  try {
    await historyStore.fetchSharedMessages(shareToken.value)
  } catch (e: any) {
    const msg = e.message || '加载消息失败'
    shareError.value = msg
    showError(msg)
  } finally {
    loadingMessages.value = false
  }
}

// 返回上一页
function goBack() {
  router.back()
}

// 初始化
onMounted(() => {
  fetchShareInfo()
})
</script>

<style scoped>
/* ===== CSS 变量 ===== */
.shared-session-page {
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-success: #10b981;
  --color-error: #ef4444;
  --color-warning: #f59e0b;
  --color-text-primary: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-tertiary: #9ca3af;
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f9fafb;
  --color-bg-tertiary: #f3f4f6;
  --color-border: #e5e7eb;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
}

.shared-session-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f9fafb 0%, #e5e7eb 100%);
  padding: 0;
  margin: 0;
}

/* ===== 页面头部 ===== */
.page-header {
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border);
  padding: 16px 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(8px);
  background: rgba(255, 255, 255, 0.8);
}

.header-content {
  max-width: 1024px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-icon {
  width: 20px;
  height: 20px;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.2s ease;
  border-radius: var(--radius-sm);
  padding: 4px;
}

.back-icon:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-primary);
}

.back-icon:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.page-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.share-icon {
  width: 22px;
  height: 22px;
  color: var(--color-primary);
}

.share-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  color: #065f46;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid #a7f3d0;
}

.share-badge svg {
  width: 14px;
  height: 14px;
}

/* ===== 主内容区 ===== */
.main-content {
  max-width: 1024px;
  margin: 0 auto;
  padding: 24px;
}

/* ===== 加载状态 - 骨架屏 ===== */
.loading-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 0;
}

.skeleton-card {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-md);
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-info-card {
  height: 200px;
}

.skeleton-messages-card {
  height: 400px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px;
  color: var(--color-text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  color: var(--color-primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== 错误容器 ===== */
.error-container {
  display: flex;
  justify-content: center;
  padding: 48px 24px;
}

.error-card {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  padding: 32px;
  text-align: center;
  box-shadow: var(--shadow-md);
  max-width: 400px;
  width: 100%;
}

.error-icon {
  width: 48px;
  height: 48px;
  color: var(--color-error);
  margin: 0 auto 16px;
}

.error-message {
  color: var(--color-text-secondary);
  margin-bottom: 20px;
  font-size: 14px;
}

/* ===== 过期提示 ===== */
.expired-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fcd34d;
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  color: #92400e;
  margin-bottom: 24px;
  font-size: 14px;
  font-weight: 500;
}

.warning-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* ===== 会话信息卡片 ===== */
.session-info-card {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-border);
}

.session-info-card.card-enter {
  animation: slideUp 0.4s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.card-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.opponent-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.opponent-badge.human {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.opponent-badge.ai {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  color: #3730a3;
  border: 1px solid #a5b4fc;
}

.opponent-badge svg {
  width: 14px;
  height: 14px;
}

/* ===== 信息网格 ===== */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.info-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.info-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-primary);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.info-icon svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.info-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.info-value.score.positive {
  color: var(--color-success);
}

.info-value.score.negative {
  color: var(--color-error);
}

.info-value.correct-text {
  color: var(--color-success);
}

.info-value.incorrect-text {
  color: var(--color-error);
}

/* ===== 聊天记录容器 ===== */
.messages-container {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-border);
}

.messages-container.card-enter {
  animation: slideUp 0.4s ease-out 0.1s both;
}

.messages-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.messages-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.messages-header h2 svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.message-count {
  font-size: 12px;
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  padding: 4px 10px;
  border-radius: 12px;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 消息气泡 ===== */
.message {
  display: flex;
  gap: 12px;
  max-width: 85%;
  opacity: 0;
}

.message.message-enter {
  animation: messageEnter 0.3s ease-out forwards;
}

@keyframes messageEnter {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-opponent {
  margin-right: auto;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid var(--color-border);
}

.message-avatar svg {
  width: 20px;
  height: 20px;
}

.user-avatar {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-color: #2563eb;
}

.opponent-avatar {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border-color: #059669;
}

.message-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.message-sender-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.message-user .message-sender-name {
  color: var(--color-primary);
}

.message-opponent .message-sender-name {
  color: #059669;
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-radius: 10px;
  font-weight: 500;
}

.meta-tag svg {
  width: 10px;
  height: 10px;
}

.message-time {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  max-width: 100%;
}

.message-user .message-content {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-opponent .message-content {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
}

/* ===== 页脚 ===== */
.page-footer {
  padding: 24px;
  text-align: center;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-primary);
  margin-top: 32px;
}

.footer-content {
  max-width: 1024px;
  margin: 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-tertiary);
  font-size: 13px;
  line-height: 1.5;
}

.footer-content svg {
  width: 16px;
  height: 16px;
  color: var(--color-success);
  flex-shrink: 0;
}

.footer-content p {
  margin: 0;
}

/* ===== 模态框 ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal,
.modal-leave-to .modal {
  transform: scale(0.95) translateY(-10px);
}

.modal {
  background: var(--color-bg-primary);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 440px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-title svg {
  width: 22px;
  height: 22px;
  color: var(--color-warning);
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.modal-body {
  padding: 24px;
}

.modal-description {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-bottom: 16px;
  line-height: 1.5;
}

.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input {
  width: 100%;
  padding: 12px 44px 12px 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.password-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.password-input::placeholder {
  color: var(--color-text-tertiary);
}

.clear-btn {
  position: absolute;
  right: 8px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.clear-btn svg {
  width: 14px;
  height: 14px;
}

.password-error {
  color: var(--color-error);
  font-size: 13px;
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.password-error::before {
  content: '!';
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: var(--color-error);
  color: white;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 600;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary_hover) 100%);
  color: white;
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover:not(:disabled) {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-secondary {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-text-tertiary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

/* ===== 响应式设计 ===== */
@media (max-width: 768px) {
  .page-header {
    padding: 12px 16px;
  }

  .page-header h1 {
    font-size: 16px;
  }

  .share-badge {
    display: none;
  }

  .main-content {
    padding: 16px;
  }

  .session-info-card {
    padding: 16px;
  }

  .info-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .info-item {
    padding: 12px;
  }

  .messages-container {
    padding: 16px;
  }

  .message {
    max-width: 90%;
  }

  .message-avatar {
    width: 32px;
    height: 32px;
  }

  .message-avatar svg {
    width: 18px;
    height: 18px;
  }

  .modal {
    max-width: 100%;
    margin: 0;
    border-radius: var(--radius-lg);
  }

  .modal-overlay {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .header-left h1 span {
    display: none;
  }

  .info-icon {
    width: 36px;
    height: 36px;
  }

  .info-icon svg {
    width: 18px;
    height: 18px;
  }
}

/* ===== 暗色模式支持 ===== */
@media (prefers-color-scheme: dark) {
  .shared-session-page {
    --color-primary: #60a5fa;
    --color-primary-hover: #3b82f6;
    --color-success: #34d399;
    --color-error: #f87171;
    --color-warning: #fbbf24;
    --color-text-primary: #f9fafb;
    --color-text-secondary: #9ca3af;
    --color-text-tertiary: #6b7280;
    --color-bg-primary: #1f2937;
    --color-bg-secondary: #111827;
    --color-bg-tertiary: #030712;
    --color-border: #374151;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.6);
  }

  .shared-session-page {
    background: linear-gradient(135deg, #111827 0%, #030712 100%);
  }

  .opponent-badge.human {
    background: linear-gradient(135deg, #1e3a5f 0%, #1e40af 100%);
    color: #93c5fd;
    border-color: #1e40af;
  }

  .opponent-badge.ai {
    background: linear-gradient(135deg, #312e81 0%, #3730a3 100%);
    color: #a5b4fc;
    border-color: #3730a3;
  }

  .message-user .message-content {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  }
}
</style>
