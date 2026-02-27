/**
 * 系统配置 Store
 * 
 * 管理系统配置，确保前后端配置同步。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSystemConfig } from '@/api/config'

// 默认关键词（fallback）
const DEFAULT_KEYWORDS = [
  '真人', '机器', 'AI', '机器人', '人工智能', '程序', '算法'
]

export const useConfigStore = defineStore('config', () => {
  // 状态
  const metaKeywords = ref<string[]>(DEFAULT_KEYWORDS)
  const metaEnabled = ref<boolean>(true)
  const loaded = ref<boolean>(false)
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  // 计算属性
  const isEnabled = computed(() => metaEnabled.value)
  
  const keywords = computed(() => 
    metaEnabled.value ? metaKeywords.value : []
  )

  /**
   * 加载配置
   */
  async function loadConfig() {
    if (loading.value || loaded.value) {
      return
    }

    loading.value = true
    error.value = null

    try {
      const config = await getSystemConfig()
      metaKeywords.value = config.meta_conversation.keywords.length > 0
        ? config.meta_conversation.keywords
        : DEFAULT_KEYWORDS
      metaEnabled.value = config.meta_conversation.enabled
      loaded.value = true
    } catch (e) {
      console.error('加载配置失败，使用默认配置:', e)
      error.value = e instanceof Error ? e.message : '加载配置失败'
      // 使用默认配置，确保功能可用
      metaKeywords.value = DEFAULT_KEYWORDS
      metaEnabled.value = true
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置配置（用于测试）
   */
  function reset() {
    metaKeywords.value = DEFAULT_KEYWORDS
    metaEnabled.value = true
    loaded.value = false
    loading.value = false
    error.value = null
  }

  return {
    // 状态
    metaKeywords,
    metaEnabled,
    loaded,
    loading,
    error,
    // 计算属性
    isEnabled,
    keywords,
    // 方法
    loadConfig,
    reset,
  }
})
