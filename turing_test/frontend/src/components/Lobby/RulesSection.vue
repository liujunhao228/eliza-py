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
        <el-collapse-item title="1. 入场券制度" name="1">
          <div class="rule-content">
            <p>• <strong>每局消耗</strong>：2 积分入场券</p>
            <p>• <strong>初始积分</strong>：100 分</p>
            <p>• <strong>不退还</strong>：无论胜负，入场券不退还</p>
            <p>• <strong>最低轮数</strong>：至少对话 3 轮后才能结束</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="2. 判断与积分" name="2">
          <div class="rule-content">
            <p>• <strong>识别 AI 正确</strong>：+10 分</p>
            <p>• <strong>误判 AI 为真人</strong>：-15 分</p>
            <p>• <strong>识别人类正确</strong>：+10 分</p>
            <p>• <strong>误判人类为 AI</strong>：-10 分</p>
            <p>• <strong>轮数惩罚</strong>：第 4 轮开始，每轮扣除 0.5 分</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="3. 信心等级机制" name="3">
          <div class="rule-content">
            <p><strong>信心等级会影响积分倍数：</strong></p>
            <ul>
              <li>低信心 (50%-70%)：×1.0 倍数</li>
              <li>中信心 (71%-90%)：×2.5 倍数</li>
              <li>高信心 (91%-100%)：×5.0 倍数</li>
            </ul>
            <p class="warning">⚠️ 风险提示：高信心判断错误将受到 5 倍惩罚！</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="4. 元对话双刃剑机制" name="4">
          <div class="rule-content">
            <p><strong>什么是元对话？</strong></p>
            <p>指讨论身份、真人、机器、AI等话题的行为</p>
            <p><strong>每次元对话会增加倍数：</strong></p>
            <ul>
              <li>判断正确时：基础分 × (1 + 次数×0.2)</li>
              <li>判断错误时：基础分 × (1 + 次数×0.3)</li>
            </ul>
            <p class="example">
              <strong>示例：</strong>元对话 3 次，高信心判断正确<br>
              → (+10 × 5.0 × 1.6) - 2 - 1.5 = +76.5 分<br>
              → 如果判断错误：(-15 × 5.0 × 1.9) - 2 - 1.5 = -144.5 分
            </p>
            <p class="warning">🚨 高频元对话（>5次）会增加遇到钓鱼机器人的风险！</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="5. 场中判断机制" name="5">
          <div class="rule-content">
            <p>• 对话过程中可以随时进行场中判断</p>
            <p>• <strong>判断正确</strong>：双倍奖励（基础分 × 2.0）</p>
            <p>• <strong>判断错误</strong>：1.5倍惩罚（基础分 × 1.5）</p>
            <p>• 对话立即结束，无需填写后续问卷</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="6. 匹配规则" name="6">
          <div class="rule-content">
            <p>• <strong>匿名对话</strong>：双方身份保密，直到实验结束才揭晓</p>
            <p>• <strong>完全随机</strong>：你可能会遇到真人、AI 或钓鱼机器人</p>
            <p>• <strong>自由策略</strong>：不预设任何角色，你可以自由选择对话策略</p>
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

.rule-content .warning {
  margin-top: 12px;
  padding: 12px;
  background: #fef0f0;
  border-left: 4px solid #f56c6c;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 14px;
  line-height: 1.6;
}

.rule-content .example {
  margin-top: 12px;
  padding: 12px;
  background: #f0f9ff;
  border-left: 4px solid #409eff;
  border-radius: 4px;
  color: #409eff;
  font-size: 14px;
  line-height: 1.8;
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