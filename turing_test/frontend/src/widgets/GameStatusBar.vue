<template>
  <div class="game-status-bar">
    <!-- 元对话计数 -->
    <div class="status-item">
      <span class="icon">💬</span>
      <span>元对话: <strong>{{ metaCount }}</strong> 次</span>
    </div>
    
    <!-- 倍数显示 -->
    <div class="status-item multipliers">
      <span>判断正确: </span>
      <span class="success-multiplier">×{{ multipliers.correct }}</span>
      <span>|</span>
      <span>判断错误: </span>
      <span class="penalty-multiplier">×{{ multipliers.penalty }}</span>
    </div>
    
    <!-- 轮数惩罚 -->
    <div class="status-item turn-penalty" v-if="turn > 3">
      <span class="icon">⚠️</span>
      <span>轮数惩罚: {{ turnPenalty.toFixed(1) }} 分</span>
    </div>
    
    <!-- 高频元对话警告 -->
    <div 
      class="status-item warning" 
      v-if="isHighFrequency"
      :class="{ 'pulse': isHighFrequency }"
    >
      <span class="icon">🚨</span>
      <span>高频元对话警告：钓鱼机器人概率提升至30%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'
import { useMetaConversation } from '@/composables/useMetaConversation'

const gameStore = useGameStore()
const { metaCount, multipliers, isHighFrequency } = useMetaConversation()

const turn = computed(() => gameStore.turn)
const turnPenalty = computed(() => {
  const MIN_FREE_TURNS = 3
  const TURN_PENALTY_RATE = 0.5
  return Math.max(0, (turn.value - MIN_FREE_TURNS) * TURN_PENALTY_RATE)
})
</script>

<style scoped>
.game-status-bar {
  background: #f8f9fa;
  border-bottom: 2px solid #e0e0e0;
  padding: 12px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-item .icon {
  font-size: 18px;
}

.multipliers {
  justify-content: center;
  gap: 12px;
}

.success-multiplier {
  color: #67c23a;
  font-weight: 600;
}

.penalty-multiplier {
  color: #f56c6c;
  font-weight: 600;
}

.turn-penalty {
  color: #e6a23c;
}

.warning {
  color: #f56c6c;
  background: #fef0f0;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #fbc4c4;
}

.warning.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>