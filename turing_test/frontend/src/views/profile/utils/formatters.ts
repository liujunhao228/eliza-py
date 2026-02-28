/**
 * 格式化函数工具集
 * 纯函数，用于日期、数字、百分比等格式化
 */

/**
 * 格式化数字（保留一位小数）
 */
export const formatNumber = (num?: number | null): string => {
  if (num === null || num === undefined) return '0'
  return num.toFixed(1)
}

/**
 * 格式化百分比
 */
export const formatPercent = (num?: number | null): string => {
  if (num === null || num === undefined) return '0%'
  return (num * 100).toFixed(1) + '%'
}

/**
 * 格式化日期
 */
export const formatDate = (dateStr?: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 格式化时长（秒转为分秒格式）
 */
export const formatDuration = (seconds?: number | null): string => {
  if (!seconds) return '0 秒'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}

/**
 * 获取对手类型标签
 */
export const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'human': '👤 真人',
    'ai': '🤖 AI',
    'honeypot': '🤖 AI',  // 钓鱼机器人隐藏为 AI
    'opponent': '👤 真人'  // 兼容旧数据：opponent 默认为真人（真人对战时）
  }
  return labels[type] || type
}

/**
 * 获取对手类型 CSS 类名
 */
export const getTypeClass = (type: string): string => {
  // honeypot 和 opponent 都使用对应的 CSS 类
  if (type === 'honeypot') return 'ai'
  if (type === 'opponent') return 'human'  // 默认使用 human 样式
  return type
}
