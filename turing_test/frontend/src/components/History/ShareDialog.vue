<template>
  <Transition name="modal">
    <div class="modal-overlay" @click.self="$emit('close')" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">
            <svg class="title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
            </svg>
            <h2 id="modal-title">{{ existingShare ? '管理分享' : '创建分享' }}</h2>
          </div>
          <button class="close-btn" @click="$emit('close')" aria-label="关闭对话框">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <!-- 加载状态 - 骨架屏 -->
          <div v-if="loading && !shareInfo" class="loading-container">
            <div class="skeleton-card"></div>
          </div>

          <!-- 错误提示 -->
          <div v-else-if="error" class="error-container">
            <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <p class="error-message">{{ error }}</p>
          </div>

          <!-- 已有分享 - 显示信息 -->
          <template v-else-if="hasExistingShare && shareInfo">
            <ShareInfoCard
              :share-info="shareInfo"
              @copy="handleCopy"
            />
            <div class="actions">
              <button class="btn btn-danger" @click="confirmDelete">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                </svg>
                删除分享
              </button>
            </div>
          </template>

          <!-- 创建分享 - 显示表单 -->
          <template v-else-if="!hasExistingShare">
            <ShareForm
              v-model="form"
            />
          </template>
        </div>

        <div v-if="!hasExistingShare && !loading" class="modal-footer">
          <button class="btn btn-secondary" @click="$emit('close')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
            取消
          </button>
          <button class="btn btn-primary" @click="createShare" :disabled="loading">
            <svg v-if="loading" class="btn-spinner" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60 40" opacity="0.3" />
              <path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
            {{ loading ? '创建中...' : '创建分享' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import * as historyApi from '@/api/history'
import type { ShareInfo as ShareInfoType } from '@/api/history'
import ShareForm from '../Share/ShareForm.vue'
import ShareInfoCard from '../Share/ShareInfo.vue'

const props = defineProps<{
  sessionId: number
  existingShare?: any
}>()

const emit = defineEmits<{
  close: []
  'share-created': []
  'share-deleted': []
  notify: [{ type: string; message: string }]
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const shareInfo = ref<ShareInfoType | null>(null)
const existingShares = ref<ShareInfoType[]>([])

const hasExistingShare = computed(() => existingShares.value.length > 0)

const form = reactive({
  is_public: true,
  expires_days: undefined as number | undefined,
  password: ''
})

// 验证 URL 安全性（只允许 http/https 协议）
function isValidShareUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

// 复制链接
async function handleCopy(url: string) {
  // 验证 URL 安全性，防止 javascript: 等危险协议
  if (!isValidShareUrl(url)) {
    error.value = '无效的分享链接'
    emit('notify', { type: 'error', message: '无效的分享链接' })
    return
  }

  try {
    await navigator.clipboard.writeText(url)
    emit('notify', { type: 'success', message: '链接已复制到剪贴板' })
  } catch (e) {
    // 降级处理
    const input = document.createElement('input')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    emit('notify', { type: 'success', message: '链接已复制到剪贴板' })
  }
}

// 创建分享
async function createShare() {
  loading.value = true
  error.value = null

  try {
    const result = await historyApi.createShare(props.sessionId, {
      is_public: form.is_public,
      expires_days: form.expires_days,
      password: form.password || undefined
    })
    shareInfo.value = result
    emit('notify', { type: 'success', message: '分享链接创建成功' })
    // 刷新分享列表
    await fetchExistingShares()
    emit('share-created')
  } catch (e: any) {
    error.value = e.message || '创建失败'
    emit('notify', { type: 'error', message: error.value || '创建失败' })
  } finally {
    loading.value = false
  }
}

// 确认删除
function confirmDelete() {
  if (confirm('确定要删除此分享链接吗？删除后他人将无法访问。')) {
    deleteShare()
  }
}

// 删除分享
async function deleteShare() {
  if (!shareInfo.value?.share_id) return

  loading.value = true
  error.value = null

  try {
    await historyApi.deleteShare(shareInfo.value.share_id)
    emit('notify', { type: 'success', message: '分享链接已删除' })
    // 刷新分享列表
    await fetchExistingShares()
    shareInfo.value = null
    emit('share-deleted')
  } catch (e: any) {
    error.value = e.message || '删除失败'
    emit('notify', { type: 'error', message: error.value || '删除失败' })
  } finally {
    loading.value = false
  }
}

// 获取现有分享列表
async function fetchExistingShares() {
  try {
    // 使用静默模式，避免 401 时自动跳转登录页
    existingShares.value = await historyApi.getSessionShares(props.sessionId, { silent: true })
    // 如果有分享，设置第一个为当前显示
    if (existingShares.value.length > 0 && !shareInfo.value) {
      shareInfo.value = existingShares.value[0] || null
    }
  } catch (e: any) {
    console.error('获取分享列表失败:', e)
    // 如果是 401，区分未登录和登录过期
    if (e.code === 'UNAUTHORIZED' || e.response?.status === 401) {
      // 检查用户是否已登录（通过 userId 判断，token 现在通过 httpOnly Cookie 存储）
      const userStore = useUserStore()
      if (!userStore.isLoggedIn) {
        error.value = '请先注册或登录后再试'
        emit('notify', { type: 'info', message: '请先注册或登录' })
      } else {
        // 已登录但 401，说明 Cookie 中的 token 无效或过期
        error.value = '登录已过期，请重新登录后再试'
        emit('notify', { type: 'warning', message: '登录已过期，请重新登录' })
      }
    } else if (e.code === 'FORBIDDEN' || e.response?.status === 403) {
      error.value = '无权访问此会话'
      emit('notify', { type: 'warning', message: '无权访问此会话' })
    } else {
      error.value = '获取分享信息失败'
      emit('notify', { type: 'error', message: '获取分享信息失败' })
    }
  }
}

// 初始化
onMounted(async () => {
  await fetchExistingShares()
})
</script>

<style scoped>
/* ===== CSS 变量映射到主题系统 ===== */
.modal-overlay {
  /* 映射到主题变量 */
  --color-primary: var(--color-primary-600);
  --color-primary-hover: var(--color-primary-700);
  --color-success: var(--color-green-500);
  --color-error: var(--color-red-500);
  --color-warning: var(--color-amber-500);
  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-text-tertiary: var(--text-tertiary);
  --color-bg-primary: var(--bg-primary);
  --color-bg-secondary: var(--bg-secondary);
  --color-bg-tertiary: var(--bg-tertiary);
  --color-bg-surface: var(--bg-surface);
  --color-border: var(--border-primary);
  --shadow-sm: var(--shadow-sm);
  --shadow-md: var(--shadow-md);
  --shadow-lg: var(--shadow-lg);
  --shadow-xl: var(--shadow-xl);
  --radius-sm: var(--rounded);
  --radius-md: var(--rounded-md);
  --radius-lg: var(--rounded-lg);
  --radius-xl: var(--rounded-xl);
}

/* ===== 模态框 overlay ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 24px;
}

/* ===== 过渡动画 ===== */
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

/* ===== 模态框主体 ===== */
.modal {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-xl);
}

/* ===== 模态框头部 ===== */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-primary);
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  z-index: 10;
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
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
  color: var(--text-tertiary);
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

/* ===== 模态框主体内容 ===== */
.modal-body {
  padding: 24px;
}

/* ===== 加载状态 - 骨架屏 ===== */
.loading-container {
  padding: 20px;
}

.skeleton-card {
  height: 120px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== 错误容器 ===== */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 20px;
  text-align: center;
}

.error-icon {
  width: 48px;
  height: 48px;
  color: var(--color-error);
  margin-bottom: 16px;
}

.error-message {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

/* ===== 操作按钮区 ===== */
.actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-primary);
}

/* ===== 模态框底部 ===== */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  position: sticky;
  bottom: 0;
}

/* ===== 按钮样式 ===== */
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

.btn svg {
  width: 16px;
  height: 16px;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
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
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.btn-secondary:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-tertiary);
}

.btn-danger {
  background: var(--color-error);
  color: white;
  flex: 1;
  box-shadow: var(--shadow-sm);
}

.btn-danger:hover {
  background: var(--color-red-600);
  box-shadow: var(--shadow-md);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== 响应式设计 ===== */
@media (max-width: 640px) {
  .modal-overlay {
    padding: 16px;
  }

  .modal {
    max-width: 100%;
    border-radius: var(--radius-lg);
  }

  .modal-header {
    padding: 16px 20px;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  .modal-body {
    padding: 20px;
  }

  .modal-footer {
    padding: 16px 20px;
    flex-direction: column-reverse;
    border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  }

  .modal-footer .btn {
    width: 100%;
  }

  .actions {
    flex-direction: column;
  }

  .actions .btn {
    width: 100%;
  }
}
</style>
