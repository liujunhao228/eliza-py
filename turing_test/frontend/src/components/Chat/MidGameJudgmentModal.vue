<template>
  <el-dialog
    v-model="dialogVisible"
    title="场中判断"
    width="600px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="mid-game-dialog"
  >
    <div class="mid-game-content">
      <!-- 主标题区域 -->
      <div class="header-section">
        <div class="title-icon">
          <el-icon><Trophy /></el-icon>
        </div>
        <h2>场中判断机会</h2>
        <p class="subtitle">立即揭晓对手身份</p>
      </div>

      <!-- 选择按钮 -->
      <div class="choice-section">
        <h3>请选择你的判断：</h3>
        <div class="choice-buttons">
          <button
            class="choice-btn human-btn"
            :disabled="isSubmitting"
            @click="handleChoice('human')"
            aria-label="判断对手是人类"
          >
            <div class="btn-icon">👤</div>
            <div class="btn-text">
              <strong>人类</strong>
              <span>我相信是人类</span>
            </div>
          </button>

          <button
            class="choice-btn ai-btn"
            :disabled="isSubmitting"
            @click="handleChoice('ai')"
            aria-label="判断对手是 AI"
          >
            <div class="btn-icon">🤖</div>
            <div class="btn-text">
              <strong>AI</strong>
              <span>我相信是 AI</span>
            </div>
          </button>
        </div>
      </div>

      <!-- 取消按钮 -->
      <div class="cancel-section">
        <button
          class="cancel-btn"
          @click="handleCancel"
          :disabled="isSubmitting"
        >
          暂不判断，继续对话
        </button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Trophy } from '@element-plus/icons-vue'

interface Emits {
  (e: 'confirm', choice: 'human' | 'ai'): void
  (e: 'cancel'): void
}

const emit = defineEmits<Emits>()

const dialogVisible = ref(true)
const isSubmitting = ref(false)

// 处理选择
function handleChoice(choice: 'human' | 'ai') {
  if (isSubmitting.value) return
  isSubmitting.value = true
  emit('confirm', choice)
}

// 处理取消
function handleCancel() {
  if (isSubmitting.value) return
  dialogVisible.value = false
  emit('cancel')
}
</script>

<style scoped>
.mid-game-dialog {
  --el-dialog-bg-color: var(--bg-surface);
  --el-dialog-border-radius: 16px;
  --el-dialog-padding-primary: 24px;
}

.mid-game-content {
  padding: 0;
}

/* 标题区域 */
.header-section {
  text-align: center;
  margin-bottom: 32px;
}

.title-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-warning-gradient);
  border-radius: 50%;
  color: white;
  font-size: 32px;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.header-section h2 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* 选择按钮区域 */
.choice-section {
  margin-bottom: 32px;
}

.choice-section h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin: 0 0 20px 0;
  text-align: center;
}

.choice-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.choice-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  background: var(--bg-surface);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--border-primary);
}

.choice-btn:hover:not(:disabled) {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.choice-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.human-btn {
  background: var(--color-success-50);
  border-color: var(--color-success-200);
}

.human-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-success-gradient);
}

.ai-btn {
  background: var(--color-error-50);
  border-color: var(--color-error-200);
}

.ai-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-error-gradient);
}

.btn-icon {
  font-size: 48px;
}

.btn-text {
  text-align: center;
}

.btn-text strong {
  display: block;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.btn-text span {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 取消按钮 */
.cancel-section {
  text-align: center;
}

.cancel-btn {
  padding: 12px 32px;
  border: 2px solid var(--border-primary);
  background: var(--bg-surface);
  color: var(--text-secondary);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

.cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 640px) {
  .mid-game-dialog {
    width: 95% !important;
    margin: 0 auto;
  }

  .choice-buttons {
    grid-template-columns: 1fr;
  }

  .header-section h2 {
    font-size: 24px;
  }

  .choice-btn {
    padding: 20px 16px;
  }
}

/* 动画效果 */
.choice-btn {
  animation: fadeInUp 0.5s ease-out;
}

.choice-btn:nth-child(2) {
  animation-delay: 0.1s;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
