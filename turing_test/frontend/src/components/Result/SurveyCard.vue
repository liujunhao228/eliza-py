<template>
  <div class="survey-section">
    <h2 class="section-title">你的判断回顾</h2>
    <div class="survey-card">
      <div class="survey-item">
        <span class="survey-label">你的判断：</span>
        <span class="survey-value">{{ data.user_guess_text }}</span>
      </div>
      <div class="survey-item">
        <span class="survey-label">信心等级：</span>
        <span class="survey-value">{{ data.confidence_level_text }}</span>
      </div>
      <div class="survey-item">
        <span class="survey-label">流畅度评分：</span>
        <span class="survey-value">{{ data.fluency_rating }}/5</span>
      </div>
      <div v-if="data.reason" class="survey-item">
        <span class="survey-label">理由：</span>
        <span class="survey-value">{{ data.reason }}</span>
      </div>
      <div class="survey-item">
        <span class="survey-label">你的角色：</span>
        <span class="survey-value">{{ data.self_role_text }}</span>
      </div>
      <div v-if="data.strategy" class="survey-item">
        <span class="survey-label">策略：</span>
        <span class="survey-value">{{ data.strategy }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SurveyData } from '@/types/result'

defineProps<{
  data: SurveyData
}>()
</script>

<style scoped>
.survey-section {
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

.survey-card {
  background: var(--bg-tertiary);
  border-radius: var(--rounded-xl);
  padding: 20px;
  border: 1px solid var(--border-primary);
}

.survey-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-secondary);
}

.survey-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.survey-label {
  color: var(--text-secondary);
  font-weight: 500;
  min-width: 100px;
}

.survey-value {
  color: var(--text-primary);
  flex: 1;
  line-height: 1.5;
}
</style>
