/**
 * Toast 提示组合式 API
 * 
 * 提供便捷的 Toast 提示方法
 */

import type { ToastOptions } from '@/components/common/BaseToast.vue'

// 全局 Toast 实例引用
let toastInstance: any = null

/**
 * 设置 Toast 实例（在 App.vue 中调用）
 */
export function setToastInstance(instance: any) {
  toastInstance = instance
}

/**
 * 显示 Toast 提示
 */
export function showToast(options: Omit<ToastOptions, 'id'>) {
  if (!toastInstance) {
    console.warn('[useToast] Toast 实例未初始化，请先在 App.vue 中调用 setToastInstance')
    return
  }
  return toastInstance.add(options)
}

/**
 * 显示成功提示
 */
export function showSuccess(message: string, title?: string) {
  return showToast({
    type: 'success',
    title,
    message
  })
}

/**
 * 显示错误提示
 */
export function showError(message: string, title?: string) {
  return showToast({
    type: 'error',
    title,
    message
  })
}

/**
 * 显示警告提示
 */
export function showWarning(message: string, title?: string) {
  return showToast({
    type: 'warning',
    title,
    message
  })
}

/**
 * 显示信息提示
 */
export function showInfo(message: string, title?: string) {
  return showToast({
    type: 'info',
    title,
    message
  })
}

/**
 * 关闭指定 Toast
 */
export function closeToast(id: number) {
  if (toastInstance) {
    toastInstance.remove(id)
  }
}

/**
 * 关闭所有 Toast
 */
export function closeAllToasts() {
  if (toastInstance) {
    toastInstance.clear()
  }
}

/**
 * useToast 组合式 API
 * 
 * 在组件中使用：
 * const { success, error, warning, info } = useToast()
 * 
 * success('操作成功')
 * error('操作失败')
 */
export function useToast() {
  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showToast,
    close: closeToast,
    closeAll: closeAllToasts
  }
}

// 默认导出
export default {
  setToastInstance,
  showToast,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  closeToast,
  closeAllToasts,
  useToast
}
