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
          <div class="share-info">
            <div class="info-row">
              <span class="label">分享链接：</span>
              <div class="link-container">
                <input
                  ref="shareLinkInput"
                  type="text"
                  :value="shareInfo.share_url"
                  readonly
                  class="share-link-input"
                />
                <button class="btn-copy" @click="copyLink">复制</button>
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
              <span>{{ shareInfo.view_count }} 次</span>
            </div>
          </div>

          <div class="actions">
            <button class="btn btn-copy-link" @click="copyLink">
              复制链接
            </button>
            <button class="btn btn-danger" @click="confirmDelete">
              删除分享
            </button>
          </div>
        </template>

        <!-- 创建分享表单 -->
        <template v-else-if="!hasExistingShare">
          <div class="form-group">
            <label>公开分享</label>
            <select v-model="form.is_public">
              <option :value="true">是（任何人可查看）</option>
              <option :value="false">否（需要密码）</option>
            </select>
          </div>

          <div class="form-group">
            <label>过期时间（天）</label>
            <input
              type="number"
              v-model.number="form.expires_days"
              min="1"
              max="365"
              placeholder="留空表示永久有效"
              class="form-input"
            />
          </div>

          <div class="form-group">
            <label>访问密码</label>
            <input
              type="password"
              v-model="form.password"
              placeholder="留空表示无需密码"
              class="form-input"
            />
            <small class="form-hint">设置密码后，访问者需要输入密码才能查看</small>
          </div>
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
import * as historyApi from '@/api/history'
import type { ShareInfo } from '@/api/history'

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
const shareInfo = ref<ShareInfo | null>(null)
const shareLinkInput = ref<HTMLInputElement | null>(null)
const existingShares = ref<ShareInfo[]>([])

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
async function copyLink() {
  if (shareInfo.value?.share_url) {
    // 验证 URL 安全性，防止 javascript: 等危险协议
    if (!isValidShareUrl(shareInfo.value.share_url)) {
      error.value = '无效的分享链接'
      return
    }

    try {
      await navigator.clipboard.writeText(shareInfo.value.share_url)
      emit('notify', { type: 'success', message: '链接已复制到剪贴板' })
    } catch (e) {
      // 降级处理
      const input = shareLinkInput.value
      if (input) {
        input.select()
        document.execCommand('copy')
        emit('notify', { type: 'success', message: '链接已复制到剪贴板' })
      }
    }
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
    existingShares.value = await historyApi.getSessionShares(props.sessionId)
    // 如果有分享，设置第一个为当前显示
    if (existingShares.value.length > 0 && !shareInfo.value) {
      shareInfo.value = existingShares.value[0] || null
    }
  } catch (e: any) {
    console.error('获取分享列表失败:', e)
  }
}

// 格式化日期
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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
  z-index: 1000;
}

.modal {
  background: white;
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
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.loading, .error {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #dc3545;
}

.share-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-row .label {
  font-weight: 500;
  color: #666;
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
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
  background: white;
}

.btn-copy {
  padding: 6px 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.btn-copy:hover {
  background: #0056b3;
}

.active {
  color: #28a745;
  font-weight: 500;
}

.expired {
  color: #dc3545;
  font-weight: 500;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 6px;
  color: #333;
}

.form-group select,
.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #666;
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

.btn-copy-link {
  background: #007bff;
  color: white;
  flex: 1;
}

.btn-danger {
  background: #dc3545;
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
