<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>{{ existingShare ? '管理分享' : '创建分享' }}</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 加载状态 -->
        <div v-if="loading && !shareInfo" class="loading">处理中...</div>

        <!-- 错误提示 -->
        <div v-else-if="error" class="error">{{ error }}</div>

        <!-- 已有分享 - 显示信息 -->
        <template v-else-if="hasExistingShare && shareInfo">
          <ShareInfoCard
            :share-info="shareInfo"
            @copy="handleCopy"
          />
          <div class="actions">
            <button class="btn btn-danger" @click="confirmDelete">
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
        <button class="btn btn-secondary" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="createShare" :disabled="loading">
          {{ loading ? '创建中...' : '创建分享' }}
        </button>
      </div>
    </div>
  </div>
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
  z-index: 10000;
}

.modal {
  background: var(--bg-surface);
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--bg-tertiary);
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.modal-body {
  padding: 20px;
}

.loading, .error {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
}

.error {
  color: var(--color-error);
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid var(--bg-tertiary);
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--color-primary-500);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-600);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-secondary);
}

.btn-danger {
  background: var(--color-error);
  color: white;
  flex: 1;
}

.btn-danger:hover {
  background: #c82333;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
