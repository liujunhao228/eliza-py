<template>
  <div class="chat-input-container">
    <!-- 输入区域 -->
    <div class="input-wrapper">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        :disabled="disabled"
        :placeholder="placeholder"
        :maxlength="MAX_MESSAGE_LENGTH"
        show-word-limit
        resize="none"
        @keydown="handleKeyDown"
        @input="handleInput"
        class="custom-textarea"
        :class="{ 'is-warning': isMetaConversation }"
        :aria-label="placeholder"
      />
    </div>

    <!-- 操作按钮区域 -->
    <div class="actions-wrapper">
      <div class="left-actions">
        <!-- 提示信息 -->
        <el-tooltip
          content="使用元对话会提高风险系数"
          placement="top"
          effect="light"
          transition="fade"
        >
          <div class="tip-icon" role="button" tabindex="0" aria-label="提示信息">
            <el-icon><InfoFilled /></el-icon>
          </div>
        </el-tooltip>
      </div>

      <div class="right-actions">
        <!-- 发送按钮 -->
        <BaseButton
          type="primary"
          :disabled="disabled || !inputText.trim() || sending"
          :loading="sending"
          @click="handleSend"
          class="send-button"
          :aria-label="`${inputText ? '发送消息' : '请输入消息后发送'}`"
        >
          <template #icon>
            <el-icon><Promotion /></el-icon>
          </template>
          发送
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { InfoFilled, Promotion } from '@element-plus/icons-vue'
import { BaseButton } from '@/components/common'
import { useToast } from '@/composables/useToast'
import { MAX_MESSAGE_LENGTH, META_KEYWORDS, SENSITIVE_WORDS } from '@/utils/constants'

interface Props {
  disabled?: boolean
  sending?: boolean
  placeholder?: string
}

interface Emits {
  (e: 'send', content: string): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  sending: false,
  placeholder: '输入消息...'
})

const emit = defineEmits<Emits>()

const { warning: showWarning } = useToast()
const inputText = ref('')
const isSending = ref(false)

// 检测是否为元对话
const isMetaConversation = computed(() => {
  const content = inputText.value.toLowerCase()
  return META_KEYWORDS.some(keyword => content.includes(keyword))
})

// 检测敏感词
function checkSensitiveWords(text: string): string | null {
  for (const word of SENSITIVE_WORDS) {
    if (text.includes(word)) {
      return word
    }
  }
  return null
}

// 自动调整高度
// Element Plus 的 el-input 在 v-model 变化时会自动调整高度，无需手动调用

// 处理键盘事件
function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (!props.sending && inputText.value.trim()) {
      handleSend()
    }
  }
}

// 处理输入变化
function handleInput() {
  // 如果检测到元对话，显示警告
  if (isMetaConversation.value && !props.sending) {
    showWarning('检测到元对话内容，可能会提高风险系数')
  }
}

// 发送消息
async function handleSend() {
  if (!inputText.value.trim()) {
    showWarning('请输入消息内容')
    return
  }

  if (isSending.value || props.sending) return

  const content = inputText.value.trim()

  // 敏感词检测
  const sensitiveWord = checkSensitiveWords(content)
  if (sensitiveWord) {
    showWarning(`消息包含敏感词：${sensitiveWord}`)
    return
  }

  isSending.value = true

  try {
    emit('send', content)
    inputText.value = '' // 清空输入
  } finally {
    isSending.value = false
  }
}
</script>

<style scoped>
.chat-input-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-surface);
  padding: 16px 20px;
  border-radius: var(--rounded-lg);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-primary);
  border-top: 2px solid var(--color-primary);
  animation: slideUp 0.3s ease-out;
  min-height: 80px;
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

/* 自定义文本框样式 */
:deep(.custom-textarea) {
  --el-input-bg-color: var(--bg-surface);
  --el-input-border-color: var(--border-primary);
  --el-input-text-color: var(--text-primary);
  --el-input-focus-border-color: var(--color-primary);
  --el-input-focus-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

:deep(.custom-textarea .el-textarea__inner) {
  border-radius: 8px;
  font-size: 15px;
  line-height: 1.5;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  transition: all 0.2s ease;
  resize: none;
  min-height: 44px;
  max-height: 120px;
}

:deep(.custom-textarea .el-textarea__inner:focus) {
  background: var(--bg-surface);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

:deep(.custom-textarea .el-textarea__inner:hover) {
  background: var(--bg-tertiary);
}

/* 元对话警告样式 */
:deep(.custom-textarea.is-warning) {
  --el-input-border-color: var(--color-warning);
}

:deep(.custom-textarea.is-warning .el-textarea__inner) {
  border-color: var(--color-warning);
  background: var(--color-warning-50);
}

/* 操作按钮区域 */
.actions-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.left-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 提示图标 */
.tip-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--color-primary-100);
  color: var(--color-primary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.tip-icon:hover {
  background: var(--color-primary-200);
  transform: translateY(-1px);
}

.tip-icon:active {
  transform: translateY(0);
}

.tip-icon:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* 发送按钮 - 使用 BaseButton 组件，这里只需要覆盖特定样式 */
.send-button {
  min-width: 80px;
}

/* 响应式设计 */
/* 超小屏 - 手机竖屏 */
@media (max-width: 359px) {
  .chat-input-container {
    padding: var(--spacing-sm);
    gap: var(--spacing-xs);
    min-height: 60px;
  }

  .actions-wrapper {
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .left-actions {
    justify-content: center;
  }

  .right-actions {
    width: 100%;
  }

  .send-button {
    width: 100%;
    height: 40px;
    font-size: var(--text-sm);
  }

  :deep(.custom-textarea .el-textarea__inner) {
    font-size: var(--text-sm);
    padding: var(--spacing-sm);
    min-height: 40px;
  }

  .tip-icon {
    width: 28px;
    height: 28px;
  }
}

/* 小屏 - 手机横屏 */
@media (max-width: 479px) {
  .chat-input-container {
    padding: var(--spacing-md);
    gap: var(--spacing-sm);
    min-height: 65px;
  }

  .send-button {
    width: 100%;
    height: 42px;
  }

  :deep(.custom-textarea .el-textarea__inner) {
    min-height: 45px;
  }
}

/* 中屏 - 小平板 */
@media (max-width: 639px) {
  .chat-input-container {
    padding: var(--spacing-md);
    gap: var(--spacing-md);
    min-height: 70px;
  }

  .actions-wrapper {
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .send-button {
    width: 100%;
    height: 44px;
  }

  :deep(.custom-textarea .el-textarea__inner) {
    padding: var(--spacing-md);
    font-size: var(--text-base);
  }
}

/* 平板 - 竖屏平板 */
@media (max-width: 767px) {
  .chat-input-container {
    padding: var(--spacing-lg);
    gap: var(--spacing-md);
    min-height: 75px;
  }

  .chat-input-container {
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .send-button {
    width: auto;
    height: 46px;
  }
}

/* 平板大屏 - 横屏平板 */
@media (max-width: 1023px) {
  .chat-input-container {
    padding: var(--spacing-lg);
    min-height: 80px;
  }

  .actions-wrapper {
    gap: var(--spacing-md);
  }

  .send-button {
    width: auto;
  }
}

/* 桌面端优化 */
@media (min-width: 1440px) {
  .chat-input-container {
    min-height: 90px;
  }

  :deep(.custom-textarea .el-textarea__inner) {
    font-size: var(--text-lg);
  }
}
</style>
