// API 基础配置
import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { API_BASE_URL, STORAGE_KEYS } from '@/utils/constants'
import { handleAxiosError } from '@/utils/error'

// 请求重试配置
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 基础重试延迟（毫秒）

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加认证 token
    const token = localStorage.getItem('accessToken')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 判断是否可以重试
 * @param error axios 错误对象
 * @returns 是否可重试
 */
function canRetry(error: AxiosError): boolean {
  // 网络错误可重试
  if (!error.response) {
    return true
  }
  
  // 仅 5xx 服务器错误和 429 限流可重试
  const status = error.response.status
  return status >= 500 || status === 429
}

/**
 * 延迟函数
 * @param ms 延迟毫秒数
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig & {
      retryCount?: number
      skipRetry?: boolean
    }

    // 检查是否已跳过重试或达到最大重试次数
    const retryCount = config.retryCount ?? 0
    const skipRetry = config.skipRetry ?? false

    // 判断是否需要重试
    if (!skipRetry && canRetry(error) && retryCount < MAX_RETRIES) {
      // 计算重试延迟（指数退避 + 随机抖动）
      const exponentialDelay = RETRY_DELAY * Math.pow(2, retryCount)
      const jitter = Math.random() * 500 // 0-500ms 随机抖动
      const retryDelay = exponentialDelay + jitter

      console.warn(
        `[API] 请求重试 ${retryCount + 1}/${MAX_RETRIES}: ${error.config?.url}`,
        `延迟 ${Math.round(retryDelay)}ms`
      )

      // 增加重试计数
      config.retryCount = retryCount + 1

      // 延迟后重试
      await delay(retryDelay)
      return api(config)
    }

    // 转换为 AppError，保留原始错误堆栈
    const appError = handleAxiosError(error)

    // 401 未授权：清除本地 token 并重定向到登录页
    if (error.response?.status === 401) {
      // 清除本地存储的 token 和用户信息
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
      localStorage.removeItem(STORAGE_KEYS.USER_ID)
      localStorage.removeItem(STORAGE_KEYS.NICKNAME)
      localStorage.removeItem(STORAGE_KEYS.INVITE_CODE)
      localStorage.removeItem(STORAGE_KEYS.USER_SCORE)
      localStorage.removeItem(STORAGE_KEYS.SESSION_ID)
      localStorage.removeItem(STORAGE_KEYS.OPPONENT_TYPE)

      // 如果当前不在登录页，跳转到登录页
      if (window.location.pathname !== '/' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/'
      }
    }

    // 附加原始错误用于调试（生产环境可移除）
    if (import.meta.env.DEV) {
      console.error('[API Error]', {
        message: appError.message,
        code: appError.code,
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        originalError: error
      })
    } else {
      console.error('[API Error]', appError.message, 'Code:', appError.code)
    }

    return Promise.reject(appError)
  }
)

export default api
