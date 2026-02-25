<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div
        v-if="modelValue"
        :class="['base-modal-overlay', { 'base-modal-overlay--click-outside': closeOnClickOutside }]"
        @click="handleClickOutside"
      >
        <transition name="modal-slide">
          <div
            v-show="modelValue"
            :class="[
              'base-modal',
              `base-modal--${size}`,
              {
                'base-modal--center': center,
                'base-modal--fullscreen': fullscreen
              }
            ]"
            :style="customStyle"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="title ? 'modal-title' : undefined"
            @click.stop
          >
            <!-- 头部 -->
            <div v-if="showHeader" class="base-modal__header">
              <h2 v-if="title" id="modal-title" class="base-modal__title">{{ title }}</h2>
              <slot name="header">
                <button
                  v-if="closable"
                  class="base-modal__close"
                  @click="handleClose"
                  aria-label="关闭对话框"
                >
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M5 5L15 15M15 5L5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </button>
              </slot>
            </div>

            <!-- 主体 -->
            <div class="base-modal__body">
              <slot></slot>
            </div>

            <!-- 底部 -->
            <div v-if="$slots.footer || showFooter" class="base-modal__footer">
              <slot name="footer">
                <slot name="footer-buttons">
                  <button
                    v-if="showCancel"
                    class="base-modal__cancel"
                    @click="handleCancel"
                  >
                    {{ cancelText }}
                  </button>
                  <button
                    v-if="showConfirm"
                    class="base-modal__confirm"
                    @click="handleConfirm"
                    :disabled="confirmLoading"
                  >
                    {{ confirmText }}
                  </button>
                </slot>
              </slot>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
interface Props {
  modelValue?: boolean
  title?: string
  size?: 'small' | 'medium' | 'large' | 'fullscreen'
  closable?: boolean
  closeOnClickOutside?: boolean
  center?: boolean
  fullscreen?: boolean
  showHeader?: boolean
  showFooter?: boolean
  showCancel?: boolean
  showConfirm?: boolean
  cancelText?: string
  confirmText?: string
  confirmLoading?: boolean
  customStyle?: Record<string, string>
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
  (e: 'cancel'): void
  (e: 'confirm'): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  title: '',
  size: 'medium',
  closable: true,
  closeOnClickOutside: true,
  center: true,
  fullscreen: false,
  showHeader: true,
  showFooter: false,
  showCancel: true,
  showConfirm: true,
  cancelText: '取消',
  confirmText: '确定',
  confirmLoading: false,
  customStyle: () => ({})
})

const emit = defineEmits<Emits>()

function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}

function handleCancel() {
  emit('cancel')
  emit('update:modelValue', false)
}

function handleConfirm() {
  if (!props.confirmLoading) {
    emit('confirm')
  }
}

function handleClickOutside() {
  if (props.closeOnClickOutside) {
    handleClose()
  }
}
</script>

<style scoped>
/* ==============================================
   BaseModal 基础对话框组件
   ============================================== */

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-slide-enter-active,
.modal-slide-leave-active {
  transition: all 0.3s ease;
}

.modal-slide-enter-from,
.modal-slide-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-20px);
}

.base-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.base-modal {
  background: var(--bg-surface);
  border-radius: var(--rounded-xl);
  box-shadow: var(--shadow-2xl);
  max-width: 100%;
  max-height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 尺寸 */
.base-modal--small {
  width: 100%;
  max-width: 400px;
}

.base-modal--medium {
  width: 100%;
  max-width: 560px;
}

.base-modal--large {
  width: 100%;
  max-width: 800px;
}

.base-modal--fullscreen {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  border-radius: 0;
}

.base-modal--center {
  margin: auto;
}

/* 头部 */
.base-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.base-modal__title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.base-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--rounded);
  transition: all 0.2s ease;
}

.base-modal__close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.base-modal__close:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* 主体 */
.base-modal__body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

/* 底部 */
.base-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.base-modal__cancel,
.base-modal__confirm {
  padding: 8px 20px;
  font-size: var(--text-base);
  font-weight: 500;
  border-radius: var(--rounded-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.base-modal__cancel {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.base-modal__cancel:hover {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

.base-modal__confirm {
  background: var(--color-primary-gradient);
  color: white;
  border: none;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.base-modal__confirm:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

.base-modal__confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .base-modal-overlay {
    padding: 12px;
    align-items: flex-end;
  }

  .base-modal--small,
  .base-modal--medium,
  .base-modal--large {
    max-width: 100%;
    max-height: 90vh;
    border-radius: var(--rounded-xl) var(--rounded-xl) 0 0;
  }

  .modal-slide-enter-from,
  .modal-slide-leave-to {
    transform: translateY(100%);
  }
}
</style>
