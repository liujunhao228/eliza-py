/**
 * Toast 通知组合式函数
 * 
 * 用法:
 * ```ts
 * const toast = useToast()
 * toast.success('操作成功')
 * toast.error('操作失败')
 * ```
 */

import { ref, type Ref } from 'vue'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: number
  type: ToastType
  message: string
  duration: number
}

const toasts: Ref<Toast[]> = ref([])
let toastId = 0

/**
 * 显示 Toast
 */
function showToast(
  message: string,
  type: ToastType = 'info',
  duration: number = 3000
): number {
  const id = ++toastId
  const toast: Toast = { id, type, message, duration }

  toasts.value.push(toast)

  // 自动关闭
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }

  return id
}

/**
 * 移除 Toast
 */
function removeToast(id: number) {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index !== -1) {
    toasts.value.splice(index, 1)
  }
}

/**
 * 清空所有 Toast
 */
function clearToasts() {
  toasts.value = []
}

// 快捷方法
export function success(message: string, duration?: number) {
  return showToast(message, 'success', duration)
}

export function error(message: string, duration?: number) {
  return showToast(message, 'error', duration)
}

export function info(message: string, duration?: number) {
  return showToast(message, 'info', duration)
}

export function warning(message: string, duration?: number) {
  return showToast(message, 'warning', duration)
}

/**
 * Toast 组合式函数
 */
export function useToast() {
  return {
    toasts,
    showToast,
    removeToast,
    clearToasts,
    success,
    error,
    info,
    warning,
    // 别名，方便使用
    showSuccess: success,
    showError: error,
    showInfo: info,
    showWarning: warning
  }
}

export type { Toast, ToastType }
