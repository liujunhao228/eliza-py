/**
 * 日志分级系统
 * 提供统一的日志管理，支持级别过滤和格式化输出
 */

/**
 * 日志级别常量
 */
export const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  SILENT: 4
} as const

export type LogLevel = typeof LogLevel[keyof typeof LogLevel]

/**
 * 日志级别映射
 */
const LogLevelMap: Record<string, LogLevel> = {
  debug: LogLevel.DEBUG,
  info: LogLevel.INFO,
  warn: LogLevel.WARN,
  error: LogLevel.ERROR,
  silent: LogLevel.SILENT
}

/**
 * 获取当前日志级别
 */
function getCurrentLogLevel(): LogLevel {
  const envLevel = import.meta.env.VITE_LOG_LEVEL
  return LogLevelMap[envLevel?.toLowerCase()] ?? 
         (import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.WARN)
}

/**
 * 格式化日志消息
 */
function formatMessage(level: string, module: string, message: string): string {
  const timestamp = new Date().toISOString()
  const moduleTag = module ? `[${module}]` : ''
  return `[${timestamp}] [${level.toUpperCase()}] ${moduleTag} ${message}`
}

/**
 * 日志器类
 */
class Logger {
  private level: LogLevel
  private module: string

  constructor(module: string = '', level?: LogLevel) {
    this.module = module
    this.level = level ?? getCurrentLogLevel()
  }

  /**
   * 设置日志级别
   */
  setLevel(level: LogLevel | string): void {
    if (typeof level === 'string') {
      this.level = LogLevelMap[level.toLowerCase()] ?? LogLevel.DEBUG
    } else {
      this.level = level
    }
  }

  /**
   * 获取当前级别
   */
  getLevel(): LogLevel {
    return this.level
  }

  /**
   * 检查是否允许该级别的日志输出
   */
  private shouldLog(level: LogLevel): boolean {
    return level >= this.level
  }

  /**
   * 调试日志
   */
  debug(message: string, ...args: any[]): void {
    if (this.shouldLog(LogLevel.DEBUG)) {
      const formatted = formatMessage('debug', this.module, message)
      console.debug(formatted, ...args)
    }
  }

  /**
   * 信息日志
   */
  info(message: string, ...args: any[]): void {
    if (this.shouldLog(LogLevel.INFO)) {
      const formatted = formatMessage('info', this.module, message)
      console.info(formatted, ...args)
    }
  }

  /**
   * 警告日志
   */
  warn(message: string, ...args: any[]): void {
    if (this.shouldLog(LogLevel.WARN)) {
      const formatted = formatMessage('warn', this.module, message)
      console.warn(formatted, ...args)
    }
  }

  /**
   * 错误日志
   */
  error(message: string, ...args: any[]): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      const formatted = formatMessage('error', this.module, message)
      console.error(formatted, ...args)
    }
  }

  /**
   * 创建子日志器（带模块名）
   */
  createChild(module: string): Logger {
    const childModule = this.module ? `${this.module}:${module}` : module
    return new Logger(childModule, this.level)
  }
}

/**
 * 默认日志器实例
 */
export const defaultLogger = new Logger('App')

/**
 * 创建模块日志器
 * @param module 模块名称
 * @returns 日志器实例
 */
export function createLogger(module: string): Logger {
  return new Logger(module)
}

/**
 * 快捷日志函数（适用于简单场景）
 */
export const logger = {
  debug: (message: string, ...args: any[]) => defaultLogger.debug(message, ...args),
  info: (message: string, ...args: any[]) => defaultLogger.info(message, ...args),
  warn: (message: string, ...args: any[]) => defaultLogger.warn(message, ...args),
  error: (message: string, ...args: any[]) => defaultLogger.error(message, ...args),
  setLevel: (level: LogLevel | string) => defaultLogger.setLevel(level),
  createChild: (module: string) => defaultLogger.createChild(module)
}
