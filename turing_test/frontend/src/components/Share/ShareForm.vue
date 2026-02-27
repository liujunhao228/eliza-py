<template>
  <div class="share-form">
    <!-- 公开分享选项 -->
    <div class="form-group">
      <label class="form-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M9 12l2 2 4-4m5.612-4.012A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.388-3.012z" />
        </svg>
        公开分享
      </label>
      <div class="toggle-group">
        <button
          type="button"
          class="toggle-option"
          :class="{ active: localForm.is_public }"
          @click="localForm.is_public = true"
          role="radio"
          :aria-checked="localForm.is_public"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <span>任何人可查看</span>
        </button>
        <button
          type="button"
          class="toggle-option"
          :class="{ active: !localForm.is_public }"
          @click="localForm.is_public = false"
          role="radio"
          :aria-checked="!localForm.is_public"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
          <span>需要密码</span>
        </button>
      </div>
    </div>

    <!-- 过期时间 -->
    <div class="form-group">
      <label class="form-label" for="expires-days">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        过期时间
      </label>
      <div class="input-with-addon">
        <input
          id="expires-days"
          type="number"
          v-model.number="localForm.expires_days"
          min="1"
          max="365"
          placeholder="留空表示永久有效"
          class="form-input"
        />
        <span class="input-addon">天</span>
      </div>
      <p class="form-hint">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4M12 8h.01" />
        </svg>
        设置分享链接的有效天数，过期后将无法访问
      </p>
    </div>

    <!-- 访问密码 -->
    <div class="form-group">
      <label class="form-label" for="password">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0110 0v4" />
        </svg>
        访问密码
      </label>
      <div class="input-group">
        <input
          id="password"
          :type="showPassword ? 'text' : 'password'"
          v-model="localForm.password"
          placeholder="留空表示无需密码"
          class="form-input"
          :class="{ 'with-toggle': localForm.password }"
        />
        <button
          v-if="localForm.password"
          type="button"
          class="toggle-password"
          @click="showPassword = !showPassword"
          aria-label="切换密码显示"
        >
          <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        </button>
      </div>
      <p class="form-hint">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        设置密码后，访问者需要输入密码才能查看分享的内容
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, ref } from 'vue'

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

const showPassword = ref(false)

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
/* ===== CSS 变量映射到主题系统 ===== */
.share-form {
  /* 映射到主题变量 */
  --color-primary: var(--color-primary-600);
  --color-primary-hover: var(--color-primary-700);
  --color-success: var(--color-green-500);
  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-text-tertiary: var(--text-tertiary);
  --color-bg-primary: var(--bg-surface);
  --color-bg-secondary: var(--bg-secondary);
  --color-bg-tertiary: var(--bg-tertiary);
  --color-border: var(--border-primary);
  --color-border-focus: var(--color-primary-600);
  --shadow-sm: var(--shadow-sm);
  --shadow-md: var(--shadow-md);
  --radius-sm: var(--rounded);
  --radius-md: var(--rounded-md);
  --radius-lg: var(--rounded-lg);
}

.share-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 表单组 ===== */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 14px;
}

.form-label svg {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
}

/* ===== 切换按钮组 ===== */
.toggle-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: var(--color-bg-tertiary);
  padding: 4px;
  border-radius: var(--radius-lg);
}

.toggle-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: transparent;
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-option svg {
  width: 24px;
  height: 24px;
  color: var(--color-text-secondary);
  transition: color 0.2s ease;
}

.toggle-option span {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
  transition: color 0.2s ease;
}

.toggle-option:hover {
  background: var(--color-bg-primary);
}

.toggle-option:hover svg,
.toggle-option:hover span {
  color: var(--color-text-primary);
}

.toggle-option.active {
  background: var(--color-bg-primary);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.toggle-option.active svg,
.toggle-option.active span {
  color: var(--color-primary);
}

.toggle-option:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* ===== 输入框 ===== */
.input-with-addon {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input::placeholder {
  color: var(--color-text-tertiary);
}

.form-input[type="number"] {
  -moz-appearance: textfield;
}

.form-input[type="number"]::-webkit-inner-spin-button,
.form-input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.input-addon {
  padding: 10px 14px;
  background: var(--color-bg-tertiary);
  border: 2px solid var(--color-border);
  border-left: none;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 500;
}

.input-with-addon:has(.form-input:focus) .input-addon {
  border-color: var(--color-border-focus);
}

.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.input-group .form-input.with-toggle {
  padding-right: 44px;
}

.toggle-password {
  position: absolute;
  right: 8px;
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

.toggle-password:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.toggle-password svg {
  width: 18px;
  height: 18px;
}

/* ===== 表单提示 ===== */
.form-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.form-hint svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}

/* ===== 暗色模式支持 ===== */
@media (prefers-color-scheme: dark) {
  .share-form {
    --color-primary: var(--color-primary-400);
    --color-primary-hover: var(--color-primary-500);
    --color-text-primary: var(--text-primary);
    --color-text-secondary: var(--text-secondary);
    --color-text-tertiary: var(--text-tertiary);
    --color-bg-primary: var(--bg-primary);
    --color-bg-secondary: var(--bg-secondary);
    --color-bg-tertiary: var(--bg-tertiary);
    --color-border: var(--border-primary);
    --color-border-focus: var(--color-primary-400);
  }
}

/* ===== 响应式设计 ===== */
@media (max-width: 480px) {
  .toggle-group {
    grid-template-columns: 1fr;
  }

  .toggle-option {
    flex-direction: row;
    justify-content: flex-start;
    padding: 10px 12px;
  }

  .toggle-option svg {
    width: 20px;
    height: 20px;
  }
}
</style>
