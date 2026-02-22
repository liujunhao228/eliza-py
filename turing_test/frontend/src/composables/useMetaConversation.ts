// 元对话检测与计数
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'

// 元对话关键词列表
const META_KEYWORDS = [
  // 身份相关
  '真人', '机器', 'AI', '机器人', '人工智能', 
  '程序', '算法', '人类', '人', '电脑', '计算',
  
  // 询问身份
  '你是', '我是', '身份', '真假', '还是', '到底',
  
  // 判断表达
  '我觉得', '我认为', '应该是', '看起来像',
  
  // 英文关键词
  'human', 'robot', 'ai', 'bot', 'real',
  'you are', 'i am', 'identity'
]

export function useMetaConversation() {
  const gameStore = useGameStore()

  // 检测是否为元对话
  function isMetaConversation(message: string): boolean {
    if (!message) return false
    
    const lowerMessage = message.toLowerCase()
    
    // 检查是否包含元对话关键词
    return META_KEYWORDS.some(keyword => 
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