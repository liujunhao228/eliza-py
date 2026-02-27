// 元对话检测与计数
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'
import { useConfigStore } from '@/stores/config'

export function useMetaConversation() {
  const gameStore = useGameStore()
  const configStore = useConfigStore()

  // 检测是否为元对话
  function isMetaConversation(message: string): boolean {
    if (!message) return false
    if (!configStore.isEnabled) return false

    const lowerMessage = message.toLowerCase()

    // 使用配置中的关键词列表
    return configStore.keywords.some(keyword =>
      lowerMessage.includes(keyword.toLowerCase())
    )
  }

  // 处理消息（检测并更新计数）
  function handleMessage(message: string, sender: 'user' | 'opponent'): boolean {
    const isMeta = isMetaConversation(message)
    
    // 如果是元对话，增加计数
    if (isMeta) {
      gameStore.incrementMetaCount()
      
      // 记录到消息中
      console.log(`[${sender}] 检测到元对话: ${message}`)
    }
    
    return isMeta
  }

  // 获取当前元对话次数
  const metaCount = computed(() => gameStore.metaConversationCount)

  // 获取当前倍数
  const multipliers = computed(() => ({
    correct: (1 + metaCount.value * 0.2).toFixed(1),
    penalty: (1 + metaCount.value * 0.3).toFixed(1)
  }))

  // 判断是否高频元对话（>5次）
  const isHighFrequency = computed(() => metaCount.value > 5)

  return {
    isMetaConversation,
    handleMessage,
    metaCount,
    multipliers,
    isHighFrequency
  }
}