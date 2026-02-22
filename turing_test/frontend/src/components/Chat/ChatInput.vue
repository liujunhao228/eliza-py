<template>
  <div class="chat-input-container">
    <el-input
      v-model="inputText"
      type="textarea"
      :rows="2"
      :disabled="disabled"
      placeholder="输入消息..."
      :maxlength="500"
      show-word-limit
      @keydown.enter.prevent="handleEnter"
      resize="none"
    />
    
    <div class="input-actions">
      <div class="input-tips">
        <el-tooltip content="提示：谨慎使用元对话，会提高风险" placement="top">
          <el-icon class="tip-icon"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
      
      <el-button
        type="primary"
        :disabled="disabled || !inputText.trim() || isSending"
        :loading="isSending"
        @click="handleSend"
      >
        <template #icon>
          <el-icon><Promotion /></el-icon>
        </template>
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { QuestionFilled, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Props {
  disabled?: boolean
}

interface Emits {
  (e: 'send', content: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const inputText = ref('')
const isSending = ref(false)

// 处理回车发送
function handleEnter(event: KeyboardEvent) {
  // Shift+Enter 换行，Enter 发送
  if (!event.shiftKey) {
    handleSend()
  }
}

// 发送消息
async function handleSend() {
  const content = inputText.value.trim()
  
  if (!content) {
    return
  }

  if (props.disabled) {
    ElMessage.warning('当前不能发送消息')
    return
  }

  // 检查元对话关键词
  const metaKeywords = ['你是', '你是AI', '你是机器人', '你是人类', '你是真人', 
                        '你是人吗', '你是机器人吗', '你是AI吗',
                        '是AI吗', '是人吗', '是机器人吗',
                        '告诉我你是', '你的身份', '你是不是']
  
  const hasMetaKeyword = metaKeywords.some(keyword => 
    content.toLowerCase().includes(keyword.toLowerCase())
  )

  if (hasMetaKeyword) {
    ElMessage.warning('检测到元对话，谨慎使用会增加风险！')
  }

  isSending.value = true
  emit('send', content)
  
  // 清空输入框
  inputText.value = ''
  
  // 重置发送状态
  setTimeout(() => {
    isSending.value = false
  }, 500)
}
</script>

<style scoped>
.chat-input-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 12px;
}

.tip-icon {
  cursor: help;
  font-size: 16px;
}

/* 文本区域样式优化 */
:deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
}

:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

/* 按钮样式 */
:deep(.el-button) {
  padding: 8px 20px;
  border-radius: 8px;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .input-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .input-tips {
    justify-content: center;
  }

  :deep(.el-button) {
    width: 100%;
  }
}
</style>