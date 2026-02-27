<template>
  <div class="game-status-bar">
    <!-- 元对话计数 -->
    <div class="status-item">
      <span class="icon">💬</span>
      <span>元对话：<strong>{{ metaCount }}</strong> 次</span>
    </div>

    <!-- 倍数显示 -->
    <div class="status-item multipliers">
      <span>判断正确：</span>
      <span class="success-multiplier">×{{ multipliers.correct }}</span>
      <span>|</span>
      <span>判断错误：</span>
      <span class="penalty-multiplier">×{{ multipliers.penalty }}</span>
    </div>

    <!-- 轮数惩罚 -->
    <div class="status-item turn-penalty" v-if="currentTurn > 3">
      <span class="icon">⚠️</span>
      <el-tooltip placement="top" :show-after="500">
        <template #content>
          <div class="tooltip-content">
            <p><strong>轮数惩罚机制：</strong></p>
            <p>• 前 3 轮：免惩罚</p>
            <p>• 第 4 轮开始：每轮扣除 0.5 分</p>
            <p>• 当前第 {{ currentTurn }} 轮，惩罚 = {{ turnPenalty.toFixed(1) }} 分</p>
          </div>
        </template>
        <span>轮数惩罚：{{ turnPenalty.toFixed(1) }} 分</span>
      </el-tooltip>
    </div>

    <!-- 高频元对话警告 -->
    <div
      class="status-item warning"
      v-if="isHighFrequency"
      :class="{ 'pulse': isHighFrequency }"
    >
      <span class="icon">🚨</span>
      <span>高频元对话警告：钓鱼机器人概率提升至 30%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'
import { useMetaConversation } from '@/composables/useMetaConversation'

const gameStore = useGameStore()
const { metaCount, multipliers, isHighFrequency } = useMetaConversation()

// 计算当前轮数（双方各发一句算一轮）
const currentTurn = computed(() => Math.ceil(gameStore.turn / 2))
const turnPenalty = computed(() => {
  const MIN_FREE_TURNS = 3
  const TURN_PENALTY_RATE = 0.5
  return Math.max(0, (currentTurn.value - MIN_FREE_TURNS) * TURN_PENALTY_RATE)
})
</script>

<style scoped>
/* ==============================================
   GameStatusBar.vue 样式 - 使用主题系统
   ============================================== */
.game-status-bar {
  background: var(--bg-tertiary);
  border-bottom: 2px solid var(--border-secondary);
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
  color: var(--color-green-500);
  font-weight: 600;
}

.penalty-multiplier {
  color: var(--color-red-500);
  font-weight: 600;
}

.turn-penalty {
  color: var(--color-amber-500);
}

.warning {
  color: var(--color-red-500);
  background: var(--color-red-50);
  padding: 8px 12px;
  border-radius: var(--rounded-sm);
  border: 1px solid var(--color-red-200);
}

.warning.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.tooltip-content {
  min-width: 200px;
  padding: 8px 0;
}

.tooltip-content p {
  margin: 4px 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.tooltip-content p strong {
  color: var(--text-primary);
  display: block;
  margin-bottom: 4px;
}
</style>
