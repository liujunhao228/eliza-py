<template>
  <BaseModal
    :modelValue="modelValue"
    title="确认结束对话"
    :closable="false"
    :show-cancel="true"
    @update:modelValue="$emit('update:modelValue', $event)"
    @cancel="$emit('cancel')"
  >
    <div class="end-session-modal">
      <!-- 警告图标 -->
      <div class="warning-icon">
        <el-icon :size="48"><WarningFilled /></el-icon>
      </div>

      <!-- 提示信息 -->
      <div class="warning-message">
        <h3>确定要结束对话吗？</h3>
        
        <div v-if="!hasMadeJudgment" class="warning-details">
          <p class="warning-text">
            <strong>您尚未做出判断，结束对话后需完成问卷：</strong>
          </p>
          <ul>
            <li>结束对话后需提交问卷以完成判断</li>
            <li>问卷中的判断将用于积分结算</li>
          </ul>
        </div>

        <div v-else class="warning-details">
          <p class="info-text">
            您已完成判断，结束对话将保存会话记录至数据库。
          </p>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="modal-actions">
        <BaseButton variant="secondary" @click="$emit('cancel')">
          继续对话
        </BaseButton>
        <BaseButton variant="danger" :loading="loading" @click="handleConfirm">
          确认结束
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const props = defineProps<{
  modelValue: boolean
  hasMadeJudgment: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'cancel'): void
  (e: 'confirm'): void
}>()

// 处理确认
const handleConfirm = () => {
  emit('confirm')
}
</script>

<style scoped>
.end-session-modal {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 8px 0;
}

.warning-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: var(--rounded-full);
  background: var(--color-warning-soft);
  color: var(--color-warning);
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-10deg); }
  75% { transform: rotate(10deg); }
}

.warning-message {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  text-align: center;
}

.warning-message h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.warning-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--rounded-md);
  border: 1px solid var(--border-primary);
}

.warning-text {
  margin: 0;
  font-size: 15px;
  color: var(--text-secondary);
}

.warning-details ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
  text-align: left;
}

.warning-details li {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 4px 0;
}

.text-danger {
  color: var(--color-danger);
  font-weight: 600;
}

.info-text {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.modal-actions {
  display: flex;
  gap: 12px;
  width: 100%;
  justify-content: center;
}

/* 响应式设计 */
@media (max-width: 639px) {
  .warning-icon {
    width: 60px;
    height: 60px;
  }

  .warning-message h3 {
    font-size: 18px;
  }

  .modal-actions {
    flex-direction: column;
  }

  .modal-actions button {
    width: 100%;
  }
}
</style>
