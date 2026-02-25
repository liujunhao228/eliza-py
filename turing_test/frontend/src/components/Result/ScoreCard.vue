<template>
  <div class="score-section">
    <h2 class="section-title">积分结果</h2>
    <div class="score-card">
      <!-- 判断结果 -->
      <div class="score-result" :class="{ correct: isCorrect, wrong: !isCorrect }">
        <span class="result-icon">{{ isCorrect ? '✅' : '❌' }}</span>
        <span class="result-text">{{ isCorrect ? '判断正确' : '判断错误' }}</span>
      </div>

      <!-- 积分变化 -->
      <div class="score-change-section">
        <div class="score-value" :class="scoreChangeClass">
          <span class="sign">{{ finalScore > 0 ? '+' : '' }}</span>
          <span class="value">{{ finalScore }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  finalScore: number
  isCorrect: boolean
}>()

const scoreChangeClass = computed(() => {
  return props.finalScore >= 0 ? 'score-positive' : 'score-negative'
})
</script>

<style scoped>
.score-section {
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

.score-card {
  background: var(--bg-tertiary);
  border-radius: var(--rounded-xl);
  padding: 32px 24px;
  border: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.score-result {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-radius: var(--rounded-lg);
  font-size: 18px;
  font-weight: 500;
}

.score-result.correct {
  background: var(--color-green-50);
  color: var(--color-green-700);
  border: 1px solid var(--color-green-200);
}

.score-result.wrong {
  background: var(--color-red-50);
  color: var(--color-red-700);
  border: 1px solid var(--color-red-200);
}

.result-icon {
  font-size: 24px;
}

.result-text {
  font-size: 18px;
  font-weight: 600;
}

.score-change-section {
  width: 100%;
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid var(--border-secondary);
}

.score-value {
  font-size: 48px;
  font-weight: bold;
}

.score-value .sign {
  font-size: 32px;
  margin-right: 4px;
}

.score-value .value {
  font-size: 56px;
}

.score-value.score-positive {
  color: var(--color-green-700);
}

.score-value.score-negative {
  color: var(--color-red-600);
}

@media (max-width: 768px) {
  .score-card {
    padding: 24px 16px;
  }

  .score-value {
    font-size: 36px;
  }

  .score-value .sign {
    font-size: 24px;
  }

  .score-value .value {
    font-size: 42px;
  }
}
</style>
