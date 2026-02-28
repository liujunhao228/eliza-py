<template>
  <div class="truth-section">
    <h2 class="section-title">真相揭晓</h2>
    <div class="truth-content">
      <div class="opponent-info">
        <div class="opponent-avatar" :class="config.class">
          {{ config.avatar }}
        </div>
        <div class="opponent-details">
          <div class="opponent-type">
            <span class="type-label">对方身份：</span>
            <span class="type-value" :class="config.class">
              {{ config.text }}
            </span>
          </div>
          <div class="result-badge" :class="badgeClass">
            {{ badgeText }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { OpponentType } from '@/types'

const props = defineProps<{
  opponentType: OpponentType
  isCorrect: boolean
}>()

// 对手类型配置
const opponentTypeConfigs: Record<OpponentType, { text: string; avatar: string; class: string }> = {
  human: { text: '👤 真人', avatar: '👤', class: 'opponent-human' },
  ai: { text: '🤖 AI', avatar: '🤖', class: 'opponent-ai' },
  honeypot: { text: '🤖 AI', avatar: '🤖', class: 'opponent-ai' }, // 钓鱼机器人隐藏为 AI
  unknown: { text: '未知', avatar: '❓', class: 'opponent-unknown' },
  opponent: { text: '👤 真人', avatar: '👤', class: 'opponent-human' }  // 兼容旧数据
}

const config = computed(() => {
  return opponentTypeConfigs[props.opponentType] || opponentTypeConfigs.unknown
})

const badgeClass = computed(() => {
  return props.isCorrect ? 'badge-correct' : 'badge-wrong'
})

const badgeText = computed(() => {
  return props.isCorrect ? '判断正确！' : '判断错误'
})
</script>

<style scoped>
.truth-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 16px;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-secondary);
  padding-bottom: 8px;
}

.opponent-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.opponent-avatar {
  width: 80px;
  height: 80px;
  border-radius: var(--rounded-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  background: var(--bg-tertiary);
  border: 3px solid var(--border-secondary);
}

.opponent-avatar.opponent-human {
  background: var(--color-green-50);
  border-color: var(--color-green-500);
  color: var(--color-green-700);
}

.opponent-avatar.opponent-ai {
  background: var(--color-primary-100);
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
}

.opponent-avatar.opponent-unknown {
  background: var(--bg-surface);
  border-color: var(--border-secondary);
  color: var(--text-secondary);
}

.opponent-details {
  flex: 1;
}

.opponent-type {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 8px;
}

.type-label {
  color: var(--text-secondary);
}

.type-value {
  font-weight: bold;
}

.type-value.opponent-human {
  color: var(--color-green-700);
}

.type-value.opponent-ai {
  color: var(--color-primary-700);
}

.type-value.opponent-unknown {
  color: var(--text-secondary);
}

.result-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: var(--rounded-full);
  font-weight: bold;
  font-size: 14px;
}

.result-badge.badge-correct {
  background: var(--color-green-50);
  color: var(--color-green-700);
}

.result-badge.badge-wrong {
  background: var(--color-red-50);
  color: var(--color-red-600);
}
</style>
