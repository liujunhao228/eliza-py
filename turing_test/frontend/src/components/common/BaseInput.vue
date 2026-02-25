<template>
  <div :class="['base-input-wrapper', `base-input--${size}`, { 'base-input--disabled': disabled }]">
    <!-- 标签 -->
    <label v-if="label" :for="inputId" class="base-input__label">
      {{ label }}
      <span v-if="required" class="required">*</span>
    </label>

    <!-- 输入框容器 -->
    <div class="base-input__container">
      <!-- 前缀图标/内容 -->
      <span v-if="$slots.prefix || prefixIcon" class="base-input__prefix">
        <slot name="prefix">
          <component v-if="prefixIcon" :is="prefixIcon" />
        </slot>
      </span>

      <!-- 输入框 -->
      <input
        :id="inputId"
        ref="inputRef"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :maxlength="maxlength"
        :minlength="minlength"
        :min="min"
        :max="max"
        :step="step"
        :autocomplete="autocomplete"
        :class="[
          'base-input',
          {
            'base-input--has-prefix': $slots.prefix || prefixIcon,
            'base-input--has-suffix': $slots.suffix || suffixIcon || clearable || showPassword
          }
        ]"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeyDown"
      />

      <!-- 后缀图标/内容 -->
      <span v-if="$slots.suffix || suffixIcon || clearable || showPassword" class="base-input__suffix">
        <slot name="suffix">
          <component v-if="suffixIcon" :is="suffixIcon" />
          <span
            v-if="clearable && modelValue"
            class="base-input__clear"
            @click="handleClear"
            role="button"
            tabindex="0"
            @keydown.enter="handleClear"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </span>
          <span
            v-if="showPassword"
            class="base-input__password-toggle"
            @click="togglePasswordVisible"
            role="button"
            tabindex="0"
            @keydown.enter="togglePasswordVisible"
          >
            <svg v-if="passwordVisible" width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M1 12C1 12 5 4 12 4C19 4 23 12 23 12C23 12 19 20 12 20C5 20 1 12 1 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20C7 20 2.73 16.39 1 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M1 1L23 23" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 7V7.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </slot>
      </span>
    </div>

    <!-- 错误提示/辅助文字 -->
    <div v-if="error || helperText" :class="['base-input__message', { 'base-input__message--error': error }]">
      {{ error || helperText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, type Component } from 'vue'

interface Props {
  modelValue?: string | number
  type?: 'text' | 'password' | 'number' | 'email' | 'tel' | 'url' | 'search' | 'date' | 'time' | 'datetime-local'
  size?: 'small' | 'medium' | 'large'
  label?: string
  placeholder?: string
  disabled?: boolean
  readonly?: boolean
  required?: boolean
  error?: string
  helperText?: string
  prefixIcon?: Component
  suffixIcon?: Component
  clearable?: boolean
  showPassword?: boolean
  maxlength?: number
  minlength?: number
  min?: number | string
  max?: number | string
  step?: number | string
  autocomplete?: string
  inputId?: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'focus', event: FocusEvent): void
  (e: 'blur', event: FocusEvent): void
  (e: 'clear'): void
  (e: 'keydown', event: KeyboardEvent): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  type: 'text',
  size: 'medium',
  disabled: false,
  readonly: false,
  required: false,
  clearable: false,
  showPassword: false
})

const emit = defineEmits<Emits>()

const inputRef = ref<HTMLInputElement>()
const passwordVisible = ref(false)

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

function handleFocus(event: FocusEvent) {
  emit('focus', event)
}

function handleBlur(event: FocusEvent) {
  emit('blur', event)
}

function handleKeyDown(event: KeyboardEvent) {
  emit('keydown', event)
}

function handleClear() {
  emit('update:modelValue', '')
  emit('clear')
  inputRef.value?.focus()
}

function togglePasswordVisible() {
  passwordVisible.value = !passwordVisible.value
}
</script>

<style scoped>
/* ==============================================
   BaseInput 基础输入框组件
   ============================================== */

.base-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

/* 标签 */
.base-input__label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.base-input__label .required {
  color: var(--color-error);
}

/* 输入框容器 */
.base-input__container {
  position: relative;
  display: flex;
  align-items: center;
}

/* 输入框 */
.base-input {
  width: 100%;
  font-family: inherit;
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  border: 1px solid var(--border-primary);
  border-radius: var(--rounded-md);
  padding: 10px 14px;
  transition: all 0.2s ease;
}

.base-input:hover:not(:disabled) {
  border-color: var(--border-secondary);
}

.base-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.base-input:disabled {
  background: var(--bg-tertiary);
  color: var(--text-disabled);
  cursor: not-allowed;
}

/* 尺寸 */
.base-input--small .base-input {
  padding: 6px 10px;
  font-size: var(--text-sm);
  height: 32px;
}

.base-input--medium .base-input {
  padding: 8px 12px;
  height: 40px;
}

.base-input--large .base-input {
  padding: 12px 16px;
  font-size: var(--text-lg);
  height: 48px;
}

/* 前缀/后缀 */
.base-input__prefix,
.base-input__suffix {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  pointer-events: none;
}

.base-input__prefix {
  left: 12px;
}

.base-input__suffix {
  right: 12px;
  gap: 8px;
  pointer-events: auto;
}

.base-input--has-prefix {
  padding-left: 36px !important;
}

.base-input--has-suffix {
  padding-right: 36px !important;
}

.base-input--has-prefix.base-input--has-suffix {
  padding-left: 36px !important;
  padding-right: 36px !important;
}

/* 清除按钮 */
.base-input__clear,
.base-input__password-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: color 0.2s ease;
}

.base-input__clear:hover,
.base-input__password-toggle:hover {
  color: var(--text-secondary);
}

.base-input__clear:focus,
.base-input__password-toggle:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* 错误状态 */
.base-input--error .base-input,
.base-input-wrapper:has(.base-input__message--error) .base-input {
  border-color: var(--color-error);
}

.base-input--error .base-input:focus,
.base-input-wrapper:has(.base-input__message--error) .base-input:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

/* 错误/辅助文字 */
.base-input__message {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.base-input__message--error {
  color: var(--color-error);
}

/* 禁用状态 */
.base-input--disabled .base-input__label {
  color: var(--text-disabled);
}
</style>
