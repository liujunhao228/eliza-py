<template>
  <div class="rules-section">
    <div class="header">
      <h1>🎯 实验大厅</h1>
      <p class="subtitle">准备好开始你的图灵测试了吗？</p>
    </div>

    <!-- 用户信息卡片 -->
    <div class="user-card">
      <div class="user-info">
        <div class="avatar">
          {{ userStore.nickname?.charAt(0).toUpperCase() }}
        </div>
        <div class="details">
          <div class="nickname">{{ userStore.nickname }}</div>
          <div class="stats">
            <span class="stat-item">
              <i class="el-icon-star"></i>
              积分: {{ userStore.score }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 规则说明 -->
    <div class="rules-card">
      <h2>📜 实验规则</h2>
      
      <el-collapse v-model="activeNames" accordion>
        <el-collapse-item title="1. 基本规则" name="1">
          <div class="rule-content">
            <p>• 每次对话限 6 轮，共 12 条消息（双方各 6 条）</p>
            <p>• 对话结束后，你需要判断对方是真人还是 AI</p>
            <p>• 系统会根据你的判断准确率给予积分奖励</p>
            <p>• 判断正确且高置信度可获得最高 100 分</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="2. 积分机制" name="2">
          <div class="rule-content">
            <p>• <strong>基础分</strong>：判断正确得 50 分，错误扣 20 分</p>
            <p>• <strong>置信度加成</strong>：</p>
            <ul>
              <li>高置信度（80-100%）：+30 分</li>
              <li>中置信度（50-79%）：+15 分</li>
              <li>低置信度（20-49%）：+5 分</li>
            </ul>
            <p>• <strong>流畅度奖励</strong>：根据对方回复流畅度给予额外奖励</p>
            <p>• <strong>最高得分</strong>：100 分（判断正确 + 高置信度 + 高流畅度）</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="3. 匹配规则" name="3">
          <div class="rule-content">
            <p>• <strong>真人优先</strong>：系统优先匹配等待中的真人玩家</p>
            <p>• <strong>AI 备选</strong>：若无真人或超时 30 秒，自动匹配 AI</p>
            <p>• <strong>匿名对话</strong>：双方身份保密，直到实验结束才揭晓</p>
            <p>• <strong>公平性</strong>：AI 的回复由真实的图灵测试机器人生成</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="4. 场中判断" name="4">
          <div class="rule-content">
            <p>• 在对话过程中，如果你已经确定对方身份</p>
            <p>• 可以点击"立即结束并提交判断"</p>
            <p>• <strong>注意</strong>：提前结束会按照当前轮数计算积分</p>
            <p>• 建议：充分对话后再判断，以提高准确率</p>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 开始匹配按钮 -->
    <div class="action-section">
      <el-button
        type="primary"
        size="large"
        @click="handleStartMatch"
        class="btn-start"
      >
        <span class="btn-icon">🎮</span>
        开始匹配
      </el-button>
      <p class="hint-text">点击开始匹配，寻找你的对手</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const emit = defineEmits<{
  (e: 'start-match'): void
}>()

const activeNames = ref(['1'])

function handleStartMatch() {
  emit('start-match')
}
</script>

<style scoped>
.rules-section {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 32px;
  color: #333;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 16px;
  color: #666;
  margin: 0;
}

.user-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 30px;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar {
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  color: white;
  backdrop-filter: blur(10px);
}

.details {
  flex: 1;
  color: white;
}

.nickname {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stats {
  display: flex;
  gap: 20px;
  font-size: 14px;
  opacity: 0.9;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rules-card {
  background: white;
  border-radius: 16px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.rules-card h2 {
  font-size: 22px;
  color: #333;
  margin-bottom: 20px;
}

.rule-content {
  padding: 8px 0;
  line-height: 1.8;
}

.rule-content p {
  margin: 8px 0;
  color: #606266;
}

.rule-content strong {
  color: #667eea;
}

.rule-content ul {
  margin: 8px 0;
  padding-left: 24px;
}

.rule-content li {
  margin: 4px 0;
  color: #606266;
}

.action-section {
  text-align: center;
  padding: 20px 0;
}

.btn-start {
  width: 100%;
  max-width: 400px;
  height: 56px;
  font-size: 18px;
  font-weight: bold;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 28px;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.btn-start:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(102, 126, 234, 0.5);
}

.btn-icon {
  margin-right: 8px;
  font-size: 20px;
}

.hint-text {
  margin-top: 16px;
  color: #909399;
  font-size: 14px;
}
</style>