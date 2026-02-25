/**
 * 输入验证和 XSS 防护工具函数
 * 提供安全的用户输入处理和验证功能
 */

import { MAX_MESSAGE_LENGTH, MIN_MESSAGE_LENGTH } from './constants'

/**
 * 清理消息内容，防止 XSS 攻击
 * @param content 原始消息内容
 * @returns 清理后的安全消息
 */
export function sanitizeMessage(content: string): string {
  if (!content) return ''

  let sanitized = content.trim()

  // 移除 script 标签及其内容
  sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')

  // 移除其他危险标签（iframe, object, embed, form 等）
  sanitized = sanitized.replace(/<(iframe|object|embed|form|input|button|textarea|select|style|link|meta|base)\b[^>]*>/gi, '')

  // 移除 javascript: 协议（包括编码变体）
  sanitized = sanitized.replace(/javascript\s*:/gi, '')
  sanitized = sanitized.replace(/&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;/gi, '')

  // 移除 data: 协议（防止 data URI 攻击）
  sanitized = sanitized.replace(/\bdata\s*:/gi, '')

  // 移除 vbscript: 协议
  sanitized = sanitized.replace(/vbscript\s*:/gi, '')

  // 移除事件处理器（onclick, onerror, onload 等）
  sanitized = sanitized.replace(/on\w+\s*=/gi, '')

  // 移除 expression() CSS 表达式（IE 攻击向量）
  sanitized = sanitized.replace(/expression\s*\([^)]*\)/gi, '')

  // 移除 url() 中的危险协议
  sanitized = sanitized.replace(/url\s*\(\s*['"]?\s*(javascript|data|vbscript)\s*:[^)]*\)/gi, '')

  // 限制消息长度
  sanitized = sanitized.substring(0, MAX_MESSAGE_LENGTH)

  return sanitized
}

/**
 * 验证消息内容
 * @param content 消息内容
 * @returns 验证结果
 */
export interface ValidationResult {
  valid: boolean
  error?: string
  sanitized?: string
}

export function validateMessage(content: string): ValidationResult {
  // 检查是否为空
  if (!content || content.trim().length === 0) {
    return { valid: false, error: '消息内容不能为空' }
  }
  
  // 检查最小长度
  if (content.trim().length < MIN_MESSAGE_LENGTH) {
    return { 
      valid: false, 
      error: `消息内容至少需要 ${MIN_MESSAGE_LENGTH} 个字符` 
    }
  }
  
  // 检查最大长度
  if (content.length > MAX_MESSAGE_LENGTH) {
    return { 
      valid: false, 
      error: `消息内容不能超过 ${MAX_MESSAGE_LENGTH} 个字符` 
    }
  }
  
  // 检查是否包含敏感词
  const containsSensitiveWord = checkSensitiveWords(content)
  if (containsSensitiveWord) {
    return { 
      valid: false, 
      error: '消息包含不当内容，请修改后重试' 
    }
  }
  
  // 清理并返回
  const sanitized = sanitizeMessage(content)
  return { valid: true, sanitized }
}

/**
 * 验证昵称格式
 * @param nickname 昵称
 * @returns 验证结果
 */
export function validateNickname(nickname: string): ValidationResult {
  // 检查是否为空
  if (!nickname || nickname.trim().length === 0) {
    return { valid: false, error: '昵称不能为空' }
  }
  
  const trimmed = nickname.trim()
  
  // 长度检查
  if (trimmed.length < 2 || trimmed.length > 20) {
    return { 
      valid: false, 
      error: '昵称长度应为 2-20 个字符' 
    }
  }
  
  // 格式检查（仅允许中文、英文、数字、#）
  const nicknameRegex = /^[\u4e00-\u9fa5a-zA-Z0-9#]+$/
  if (!nicknameRegex.test(trimmed)) {
    return { 
      valid: false, 
      error: '昵称仅支持中文、英文、数字和#符号' 
    }
  }
  
  return { valid: true, sanitized: trimmed }
}

/**
 * 验证邀请码格式
 * @param code 邀请码
 * @returns 验证结果
 */
export function validateInviteCode(code: string): ValidationResult {
  // 检查是否为空
  if (!code || code.trim().length === 0) {
    return { valid: false, error: '邀请码不能为空' }
  }
  
  const trimmed = code.trim().toUpperCase()
  
  // 格式检查（6-8 位字母数字）
  const codeRegex = /^[A-Z0-9]{6,8}$/
  if (!codeRegex.test(trimmed)) {
    return { 
      valid: false, 
      error: '邀请码格式无效（应为 6-8 位字母或数字）' 
    }
  }
  
  return { valid: true, sanitized: trimmed }
}

/**
 * 检查是否包含敏感词
 * @param content 内容
 * @returns 是否包含敏感词
 */
export function checkSensitiveWords(content: string): boolean {
  const sensitiveWords = [
    '微信', 'QQ', '电话', '手机', '邮箱', '邮件',
    'http://', 'https://', 'www.', '.com', '.cn',
    '傻', '笨', '猪', '滚', '废物', '白痴'
  ]
  
  const lowerContent = content.toLowerCase()
  return sensitiveWords.some(word => lowerContent.includes(word.toLowerCase()))
}

/**
 * HTML 实体编码，防止 XSS
 * @param str 原始字符串
 * @returns 编码后的字符串
 */
export function htmlEncode(str: string): string {
  const div = document.createElement('div')
  div.textContent = str
  return div.innerHTML
}

/**
 * HTML 实体解码
 * @param str 编码后的字符串
 * @returns 解码后的字符串
 */
export function htmlDecode(str: string): string {
  const div = document.createElement('div')
  div.innerHTML = str
  return div.textContent || ''
}

/**
 * 验证 URL 格式
 * @param url URL 字符串
 * @returns 是否有效
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

/**
 * 验证邮箱格式
 * @param email 邮箱地址
 * @returns 是否有效
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * 安全的 URL 验证（只允许 http/https 协议）
 * @param url URL 字符串
 * @returns 是否有效且安全
 */
export function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    // 只允许 http 和 https 协议
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

/**
 * 清理 URL，移除危险协议
 * @param url 原始 URL
 * @returns 安全的 URL 或空字符串
 */
export function sanitizeUrl(url: string): string {
  if (!url) return ''
  
  try {
    const parsed = new URL(url.trim())
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return parsed.href
    }
    return ''
  } catch {
    return ''
  }
}

/**
 * 创建安全的锚点链接属性
 * 为外部链接添加 rel="noopener noreferrer" 防止标签页劫持
 * @param url URL 字符串
 * @returns 链接属性对象
 */
export function getSafeLinkAttrs(url: string): { href: string; target: string; rel: string } {
  const safeUrl = sanitizeUrl(url)
  return {
    href: safeUrl,
    target: '_blank',
    rel: 'noopener noreferrer'
  }
}
