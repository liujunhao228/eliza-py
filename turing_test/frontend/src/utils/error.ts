/**
 * 统一错误处理模块
 * 提供标准化的错误类型和错误处理函数
 */

/**
 * 错误代码常量
 */
export const ErrorCode = {
  // 通用错误
  UNKNOWN: 'UNKNOWN_ERROR',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT_ERROR',

  // 认证错误
  UNAUTHORIZED: 'UNAUTHORIZED',
  INVALID_TOKEN: 'INVALID_TOKEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',

  // 用户输入错误
  INVALID_INPUT: 'INVALID_INPUT',
  VALIDATION_ERROR: 'VALIDATION_ERROR',

  // 业务错误
  USER_NOT_FOUND: 'USER_NOT_FOUND',
  SESSION_NOT_FOUND: 'SESSION_NOT_FOUND',
  INVALID_INVITE_CODE: 'INVALID_INVITE_CODE',
  INSUFFICIENT_SCORE: 'INSUFFICIENT_SCORE',
  CONFLICT: 'CONFLICT',

  // WebSocket 错误
  WS_CONNECTION_FAILED: 'WS_CONNECTION_FAILED',
  WS_DISCONNECTED: 'WS_DISCONNECTED',
  WS_MESSAGE_ERROR: 'WS_MESSAGE_ERROR',

  // 用户操作
  USER_CANCEL: 'USER_CANCEL'
} as const

export type ErrorCode = typeof ErrorCode[keyof typeof ErrorCode]

/**
 * 应用错误类
 */
export class AppError extends Error {
  code: ErrorCode
  detail?: string
  statusCode?: number
  
  constructor(
    code: ErrorCode,
    message: string,
    detail?: string,
    statusCode?: number
  ) {
    super(message)
    this.name = 'AppError'
    this.code = code
    this.detail = detail
    this.statusCode = statusCode
  }
  
  /**
   * 转换为普通对象（便于序列化）
   */
  toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      detail: this.detail,
      statusCode: this.statusCode
    }
  }
}

/**
 * 用户取消操作错误
 */
export class UserCancelError extends AppError {
  constructor(message: string = '用户取消操作') {
    super(ErrorCode.USER_CANCEL, message)
    this.name = 'UserCancelError'
  }
}

/**
 * 网络错误
 */
export class NetworkError extends AppError {
  constructor(message: string = '网络错误，请稍后重试') {
    super(ErrorCode.NETWORK_ERROR, message)
    this.name = 'NetworkError'
  }
}

/**
 * 认证错误
 */
export class UnauthorizedError extends AppError {
  constructor(message: string = '未授权，请重新登录') {
    super(ErrorCode.UNAUTHORIZED, message)
    this.name = 'UnauthorizedError'
  }
}

/**
 * 验证错误
 */
export class ValidationError extends AppError {
  constructor(message: string, detail?: string) {
    super(ErrorCode.VALIDATION_ERROR, message, detail)
    this.name = 'ValidationError'
  }
}

/**
 * 错误消息映射
 */
export const ERROR_MESSAGES: Record<ErrorCode, string> = {
  [ErrorCode.UNKNOWN]: '发生未知错误，请稍后重试',
  [ErrorCode.NETWORK_ERROR]: '网络错误，请稍后重试',
  [ErrorCode.TIMEOUT]: '请求超时，请检查网络连接',
  [ErrorCode.UNAUTHORIZED]: '未授权，请重新登录',
  [ErrorCode.INVALID_TOKEN]: '令牌无效',
  [ErrorCode.TOKEN_EXPIRED]: '令牌已过期，请重新登录',
  [ErrorCode.INVALID_INPUT]: '输入无效',
  [ErrorCode.VALIDATION_ERROR]: '验证失败',
  [ErrorCode.USER_NOT_FOUND]: '用户不存在',
  [ErrorCode.SESSION_NOT_FOUND]: '会话不存在',
  [ErrorCode.INVALID_INVITE_CODE]: '邀请码无效',
  [ErrorCode.INSUFFICIENT_SCORE]: '积分不足',
  [ErrorCode.CONFLICT]: '请求冲突，请稍后重试',
  [ErrorCode.WS_CONNECTION_FAILED]: 'WebSocket 连接失败',
  [ErrorCode.WS_DISCONNECTED]: 'WebSocket 连接已断开',
  [ErrorCode.WS_MESSAGE_ERROR]: 'WebSocket 消息处理错误',
  [ErrorCode.USER_CANCEL]: '操作已取消'
}

/**
 * 从 API 响应创建错误
 * @param response API 响应数据
 * @returns AppError 实例
 */
export function createErrorFromResponse(response: {
  code?: string
  message?: string
  detail?: string
  status?: number
}): AppError {
  const code = (response.code as ErrorCode) || ErrorCode.UNKNOWN
  const message = response.message || ERROR_MESSAGES[code] || '操作失败'
  
  return new AppError(code, message, response.detail, response.status)
}

/**
 * 处理 axios 错误
 * @param error axios 错误对象
 * @returns AppError 实例
 */
export function handleAxiosError(error: any): AppError {
  // 网络错误
  if (!error.response) {
    if (error.message?.includes('timeout')) {
      return new AppError(
        ErrorCode.TIMEOUT,
        '请求超时，请检查网络连接'
      )
    }
    return new NetworkError('网络错误，请稍后重试')
  }
  
  // HTTP 错误
  const { status, data } = error.response
  
  switch (status) {
    case 401:
      return new UnauthorizedError()
    case 404:
      return new AppError(
        ErrorCode.SESSION_NOT_FOUND,
        '请求的资源不存在'
      )
    case 409:
      return new AppError(
        ErrorCode.CONFLICT,
        data?.message || '请求冲突'
      )
    case 422:
      return new ValidationError(
        data?.message || '验证失败',
        data?.detail
      )
    case 500:
      return new AppError(
        ErrorCode.UNKNOWN,
        '服务器错误，请稍后重试',
        undefined,
        status
      )
    default:
      return createErrorFromResponse({
        code: data?.code,
        message: data?.message || data?.detail || error.message,
        detail: data?.detail,
        status
      })
  }
}

/**
 * 判断是否为用户取消错误
 * @param error 错误对象
 * @returns 是否为用户取消
 */
export function isUserCancel(error: unknown): boolean {
  return error instanceof UserCancelError || 
         (error instanceof AppError && error.code === ErrorCode.USER_CANCEL)
}

/**
 * 获取错误显示消息
 * @param error 错误对象
 * @param defaultMessage 默认消息
 * @returns 显示消息
 */
export function getErrorMessage(error: unknown, defaultMessage?: string): string {
  if (error instanceof AppError) {
    return error.message
  }
  
  if (error instanceof Error) {
    return error.message
  }
  
  if (typeof error === 'string') {
    return error
  }
  
  return defaultMessage || ERROR_MESSAGES[ErrorCode.UNKNOWN]
}

/**
 * 安全地执行异步函数，返回 [error, data] 元组
 * @param promise 异步 Promise
 * @returns [错误，数据] 元组
 */
export async function safeExecute<T>(
  promise: Promise<T>
): Promise<[AppError, null] | [null, T]> {
  try {
    const data = await promise
    return [null, data]
  } catch (error) {
    return [error instanceof AppError ? error : handleAxiosError(error), null]
  }
}
