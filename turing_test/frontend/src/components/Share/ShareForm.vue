<template>
  <div class="share-form">
    <div class="form-group">
      <label>公开分享</label>
      <select v-model="localForm.is_public">
        <option :value="true">是（任何人可查看）</option>
        <option :value="false">否（需要密码）</option>
      </select>
    </div>

    <div class="form-group">
      <label>过期时间（天）</label>
      <input
        type="number"
        v-model.number="localForm.expires_days"
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
        v-model="localForm.password"
        placeholder="留空表示无需密码"
        class="form-input"
      />
      <small class="form-hint">设置密码后，访问者需要输入密码才能查看</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

interface ShareFormValue {
  is_public: boolean
  expires_days: number | undefined
  password: string
}

const props = defineProps<{
  modelValue?: ShareFormValue
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ShareFormValue]
}>()

// 内部状态
const localForm = reactive<ShareFormValue>({
  is_public: props.modelValue?.is_public ?? true,
  expires_days: props.modelValue?.expires_days,
  password: props.modelValue?.password ?? ''
})

// 同步外部变化
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      localForm.is_public = newVal.is_public
      localForm.expires_days = newVal.expires_days
      localForm.password = newVal.password
    }
  },
  { deep: true }
)

// 触发更新
watch(
  localForm,
  (newVal) => {
    emit('update:modelValue', { ...newVal })
  },
  { deep: true }
)
</script>

<style scoped>
.share-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 14px;
}

.form-group select,
.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-surface);
  color: var(--text-primary);
  transition: border-color 0.2s;
}

.form-group select:focus,
.form-group input:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

.form-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}
</style>
