/**
 * 通用 UI 组件库
 *
 * 这些组件是项目的基础 UI 构建块，
 * 可在整个项目中复用。
 */

// 基础组件
export { default as BaseButton } from './BaseButton.vue'
export { default as BaseCard } from './BaseCard.vue'
export { default as BaseInput } from './BaseInput.vue'
export { default as BaseLoading } from './BaseLoading.vue'
export { default as BaseEmpty } from './BaseEmpty.vue'
export { default as BaseModal } from './BaseModal.vue'
export { default as BaseToast, type ToastOptions, type ToastType, type ToastPosition } from './BaseToast.vue'
export { default as Toast } from './Toast.vue'
export { default as BaseProgress } from './BaseProgress.vue'
export { default as BaseBadge } from './BaseBadge.vue'
export { default as ErrorBoundary } from './ErrorBoundary.vue'

// Toast 组合式 API
export { useToast } from '../../composables/useToast'

// 组件安装函数（可选，用于全局注册）
import type { App } from 'vue'
import BaseButton from './BaseButton.vue'
import BaseCard from './BaseCard.vue'
import BaseInput from './BaseInput.vue'
import BaseLoading from './BaseLoading.vue'
import BaseEmpty from './BaseEmpty.vue'
import BaseModal from './BaseModal.vue'
import BaseProgress from './BaseProgress.vue'
import BaseBadge from './BaseBadge.vue'
import ErrorBoundary from './ErrorBoundary.vue'
import Toast from './Toast.vue'

/**
 * 全局注册所有通用组件
 *
 * 在 main.ts 中使用：
 * app.use(installCommonComponents)
 */
export function installCommonComponents(app: App) {
  app.component('BaseButton', BaseButton)
  app.component('BaseCard', BaseCard)
  app.component('BaseInput', BaseInput)
  app.component('BaseLoading', BaseLoading)
  app.component('BaseEmpty', BaseEmpty)
  app.component('BaseModal', BaseModal)
  app.component('BaseProgress', BaseProgress)
  app.component('BaseBadge', BaseBadge)
  app.component('ErrorBoundary', ErrorBoundary)
  app.component('Toast', Toast)
}

export default {
  install: installCommonComponents
}
