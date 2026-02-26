/**
 * 计算工具集
 * 用于统计数据的各种计算逻辑
 */

export interface Stats {
  total_sessions?: number
  avg_turns?: number
  avg_session_duration?: number
  highest_score?: number
  lowest_score?: number
  accuracy?: number
  accuracy_with_meta?: number
  accuracy_without_meta?: number
  mid_game_accuracy?: number
  total_meta_conversations?: number
  avg_meta_per_session?: number
  max_meta_in_one_session?: number
  human_sessions?: number
  ai_sessions?: number
  low_confidence_count?: number
  mid_confidence_count?: number
  high_confidence_count?: number
}

/**
 * 计算平均信心值（加权平均）
 * 低信心 0.6, 中信心 0.8, 高信心 0.95
 */
export const calcAvgConfidence = (stats?: Stats | null): string => {
  if (!stats) return '0%'
  
  const total = (stats.low_confidence_count || 0) +
                (stats.mid_confidence_count || 0) +
                (stats.high_confidence_count || 0)
  
  if (total === 0) return '0%'

  const weightedSum = (stats.low_confidence_count || 0) * 0.6 +
                       (stats.mid_confidence_count || 0) * 0.8 +
                       (stats.high_confidence_count || 0) * 0.95
  
  const avg = weightedSum / total
  return (avg * 100).toFixed(1) + '%'
}

/**
 * 获取百分比（基于总数）
 */
export const getPercentage = (count: number, total: number): number => {
  if (total === 0) return 0
  return (count / total) * 100
}

/**
 * 获取信心等级百分比
 */
export const getConfidencePercentage = (level: 'low' | 'mid' | 'high', stats?: Stats | null): number => {
  if (!stats) return 0
  
  const total = (stats.low_confidence_count || 0) +
                (stats.mid_confidence_count || 0) +
                (stats.high_confidence_count || 0)
  
  if (total === 0) return 0

  const counts: Record<string, number> = {
    'low': stats.low_confidence_count || 0,
    'mid': stats.mid_confidence_count || 0,
    'high': stats.high_confidence_count || 0
  }
  
  return ((counts[level] ?? 0) / total) * 100
}

/**
 * 获取信心等级总数
 */
export const getTotalConfidenceCount = (stats?: Stats | null): number => {
  if (!stats) return 0
  return (stats.low_confidence_count || 0) +
         (stats.mid_confidence_count || 0) +
         (stats.high_confidence_count || 0)
}
