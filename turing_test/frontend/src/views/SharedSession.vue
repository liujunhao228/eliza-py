<template>
  <div class="shared-session-page">
    <div class="header">
      <h1>🔗 公开分享的会话</h1>
    </div>

    <!-- 加载状态 -->
    <div v-if="loadingShare" class="loading">加载中...</div>

    <!-- 错误提示 -->
    <div v-else-if="shareError" class="error">
      <p>{{ shareError }}</p>
      <button v-if="needsPassword" class="btn btn-primary" @click="showPasswordModal = true">
        输入密码
      </button>
    </div>

    <!-- 分享信息 -->
    <template v-else-if="shareInfo">
      <!-- 过期提示 -->
      <div v-if="shareInfo.is_expired" class="expired-banner">
        <span>⚠️ 此分享已过期，无法查看详细内容</span>
      </div>

      <div v-else class="session-info-card">
        <div class="info-row">
          <span class="label">对手类型：</span>
          <span class="value">{{ shareInfo.opponent_type === 'human' ? '真人' : 'AI' }}</span>
        </div>
        <div class="info-row">
          <span class="label">轮数：</span>
          <span class="value">{{ shareInfo.turn_count }} 回合</span>
        </div>
        <div class="info-row" v-if="shareInfo.final_score !== null">
          <span class="label">得分：</span>
          <span class="value score" :class="shareInfo.final_score > 0 ? 'positive' : 'negative'">
            {{ shareInfo.final_score > 0 ? '+' : '' }}{{ shareInfo.final_score }}
          </span>
        </div>
        <div class="info-row" v-if="shareInfo.is_correct !== null">
          <span class="label">判断结果：</span>
          <span class="value" :class="shareInfo.is_correct ? 'correct-text' : 'incorrect-text'">
            {{ shareInfo.is_correct ? '正确 ✓' : '错误 ✗' }}
          </span>
        </div>
        <div class="info-row">
          <span class="label">分享时间：</span>
          <span class="value">{{ formatDate(shareInfo.started_at) }}</span>
        </div>
        <div class="info-row">
          <span class="label">浏览次数：</span>
          <span class="value">{{ shareInfo.view_count }} 次</span>
        </div>
      </div>

      <!-- 聊天记录 -->
      <div v-if="messages.length > 0" class="messages-container">
        <h2>聊天记录</h2>
        <div
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="message.sender === 'user' ? 'message-user' : 'message-opponent'"
        >
          <div class="message-sender">
            {{ message.sender === 'user' ? '用户' : '对手' }}
            <span v-if="message.is_meta_conversation" class="meta-tag">元对话</span>
          </div>
          <div class="message-content">{{ message.content }}</div>
          <div class="message-time">{{ formatMessageTime(message.created_at) }}</div>
        </div>
      </div>

      <!-- 加载消息状态 -->
      <div v-else-if="loadingMessages" class="loading">加载消息...</div>

      <!-- 页脚 -->
      <div class="footer">
        <p>此会话由用户分享 · 仅供学习交流</p>
      </div>
    </template>

    <!-- Toast 通知 -->
    <Toast ref="toastRef" />

    <!-- 密码输入对话框 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>🔒 需要密码</h2>
        </div>
        <div class="modal-body">
          <p>此分享受密码保护，请输入访问密码</p>
          <input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            class="password-input"
            @keyup.enter="verifyPassword"
          />
          <p v-if="passwordError" class="password-error">{{ passwordError }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showPasswordModal = false">取消</button>
          <button class="btn btn-primary" @click="verifyPassword" :disabled="verifying">
            {{ verifying ? '验证中...' : '验证' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useHistoryStore } from '@/stores/history'
import Toast from '@/components/common/Toast.vue'

const route = useRoute()
const historyStore = useHistoryStore()
const toastRef = ref<InstanceType<typeof Toast> | null>(null)

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
      toastRef.value?.error('此分享已过期')
    }
  } catch (e: any) {
    const msg = e.message || '加载失败'
    if (msg.includes('密码') || msg.includes('password')) {
      needsPassword.value = true
      showPasswordModal.value = true
    } else if (msg.includes('过期')) {
      shareError.value = '此分享已过期'
      toastRef.value?.error('此分享已过期')
    } else {
      shareError.value = msg
      toastRef.value?.error(msg)
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
    toastRef.value?.error('重试次数过多，请稍后再试')
    return
  }

  verifying.value = true
  passwordError.value = null

  try {
    const result = await historyStore.verifySharePassword(shareToken.value, password.value)
    if (result.success) {
      showPasswordModal.value = false
      toastRef.value?.success('密码验证成功')
      await fetchMessages()
    }
  } catch (e: any) {
    passwordError.value = e.message || '密码错误'
    toastRef.value?.error(e.message || '密码错误')
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
    toastRef.value?.error(msg)
  } finally {
    loadingMessages.value = false
  }
}

// 初始化
onMounted(() => {
  fetchShareInfo()
})
</script>

<style scoped>
.shared-session-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  text-align: center;
  margin-bottom: 20px;
}

.loading, .error {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error {
  color: #dc3545;
}

.expired-banner {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 15px;
  text-align: center;
  color: #856404;
  margin-bottom: 20px;
}

.session-info-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .label {
  font-weight: 500;
  color: #666;
}

.info-row .value {
  color: #333;
  font-weight: 500;
}

.score.positive {
  color: #28a745;
}

.score.negative {
  color: #dc3545;
}

.correct-text {
  color: #28a745;
}

.incorrect-text {
  color: #dc3545;
}

.messages-container {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
}

.messages-container h2 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  color: #333;
}

.message {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  margin-bottom: 15px;
}

.message-user {
  margin-left: auto;
  background: #007bff;
  color: white;
}

.message-opponent {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
}

.message-sender {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}

.message-content {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 6px;
  text-align: right;
}

.footer {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.modal-body {
  padding: 20px;
}

.modal-body p {
  margin-bottom: 15px;
  color: #666;
}

.password-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.password-error {
  color: #dc3545;
  font-size: 13px;
  margin-top: 10px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
