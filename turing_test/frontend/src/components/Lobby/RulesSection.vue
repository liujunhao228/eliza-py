<template>
  <div class="rules-section">
    <div class="header">
      <div class="header-title">
        <h1>🎯 实验大厅</h1>
        <p class="subtitle">准备好开始你的图灵测试了吗？</p>
      </div>
      <button class="btn-logout" @click="handleLogout">
        <span class="btn-icon">🚪</span>
        退出登录
      </button>
    </div>

    <!-- 用户信息卡片 -->
    <div class="user-card" @click="goToProfile">
      <div class="user-info">
        <div class="avatar">
          {{ userStore.nickname?.charAt(0).toUpperCase() }}
        </div>
        <div class="details">
          <div class="nickname">{{ userStore.nickname }}</div>
          <div class="stats">
            <span class="stat-item">
              <i class="el-icon-star"></i>
              积分：{{ userStore.score }}
            </span>
          </div>
        </div>
      </div>
      <span class="click-hint">点击查看个人中心</span>
    </div>

    <!-- 规则说明 -->
    <div class="rules-card">
      <div class="rules-header">
        <h2>📜 实验规则</h2>
        <el-button class="btn-toggle" text @click="toggleAll">
          {{ isAllExpanded ? '全部收起' : '全部展开' }}
        </el-button>
      </div>

      <el-collapse v-model="activeNames">
        <el-collapse-item title="1. 入场券" name="1">
          <div class="rule-content">
            <p>- 开始每局对话消耗<strong>2 积分</strong></p>
            <p>- 初始积分：<strong>100 分</strong></p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="2. 判断身份" name="2">
          <div class="rule-content">
            <p>- 在问卷中填写你的判断</p>
            <p>- 判断成功：获得积分</p>
            <p>- 判断错误：扣除积分</p>
            <p>- 对方错误：你<strong>获得</strong>积分</p>
            <p>- 至少对话 3 轮后才能结束对话</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="3. 信心等级" name="3">
          <div class="rule-content">
            <p>- 在问卷中填写你对判断的把握程度</p>
            <p>- 信心等级越高，奖惩倍数越高</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="4. 场中判断机制" name="4">
          <div class="rule-content">
            <p>- 对话过程中可以随时进行一次场中判断</p>
            <p>- 信心等级固定为<strong>"高"</strong></p>
            <p>- 场中判断的结果无法更改，并代替问卷中的相应部分</p>
          </div>
        </el-collapse-item>

        <el-collapse-item title="5. 元对话" name="5">
          <div class="rule-content">
            <p>- 元对话指讨论身份（比如真人/机器等话题）的行为</p>
            <p>- 基于双方发言中的关键词识别</p>
            <p>- 每次触发关键词会增加奖惩倍数</p>
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const emit = defineEmits<{
  (e: 'start-match'): void
  (e: 'logout'): void
}>()

// 默认展开前 3 个条目
const activeNames = ref(['1', '2', '3'])

// 所有条目名称
const allNames = ['1', '2', '3', '4', '5']

// 是否全部展开
const isAllExpanded = computed(() => activeNames.value.length === allNames.length)

// 全部展开/收起切换
function toggleAll() {
  if (isAllExpanded.value) {
    activeNames.value = []
  } else {
    activeNames.value = [...allNames]
  }
}

function handleStartMatch() {
  emit('start-match')
}

function handleLogout() {
  emit('logout')
}

// 跳转到个人中心
function goToProfile() {
  router.push('/profile')
}
</script>

<style scoped>
/* ==============================================
   RulesSection 样式 - 使用主题系统
   ============================================== */

.rules-section {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header-title {
  flex: 1;
}

.header h1 {
  font-size: 32px;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
}

.btn-logout {
  flex-shrink: 0;
  margin-left: 16px;
  padding: 10px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--rounded-md);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-logout:hover {
  background: var(--color-red-50);
  border-color: var(--color-red-200);
  color: var(--color-error);
}

.user-card {
  background: var(--color-primary-gradient);
  border-radius: var(--rounded-2xl);
  padding: 24px;
  margin-bottom: 30px;
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.user-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
}

.user-card:active {
  transform: translateY(-2px);
}

.click-hint {
  position: absolute;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  opacity: 0;
  transition: opacity 0.3s ease;
  display: flex;
  align-items: center;
  gap: 4px;
}

.click-hint::before {
  content: '→';
  font-size: 14px;
}

.user-card:hover .click-hint {
  opacity: 1;
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
  border-radius: var(--rounded-full);
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
  background: var(--bg-surface);
  border-radius: var(--rounded-2xl);
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-primary);
}

.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.rules-header h2 {
  font-size: 22px;
  color: var(--text-primary);
  margin: 0;
}

.btn-toggle {
  font-size: 13px !important;
  color: var(--color-primary-600) !important;
  padding: 6px 12px !important;
}

.btn-toggle:hover {
  background: var(--color-primary-50) !important;
}

/* 折叠面板样式优化 - 提高信息密度 */
:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item) {
  margin-bottom: 8px;
  border: 1px solid var(--border-primary);
  border-radius: var(--rounded-md);
  overflow: hidden;
}

:deep(.el-collapse-item__header) {
  font-size: 13px;
  padding: 10px 12px;
  line-height: 1.4;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  transition: all 0.2s;
}

:deep(.el-collapse-item__header:hover) {
  background: var(--bg-secondary);
}

:deep(.el-collapse-item__arrow) {
  font-size: 12px;
  margin-right: 8px;
}

:deep(.el-collapse-item__content) {
  padding: 10px 16px 14px;
  font-size: 13px;
  line-height: 1.8;
  background: var(--bg-surface);
}

.rule-content {
  padding: 0;
  line-height: 1.8;
}

.rule-content p {
  margin: 6px 0;
  color: var(--text-secondary);
}

.rule-content strong {
  color: var(--color-primary-600);
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
  background: var(--color-primary-gradient);
  border: none;
  border-radius: var(--rounded-full);
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
  color: white;
}

.btn-start:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(99, 102, 241, 0.5);
}

.btn-icon {
  margin-right: 8px;
  font-size: 20px;
}

.hint-text {
  margin-top: 16px;
  color: var(--text-tertiary);
  font-size: 14px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .rules-section {
    padding: 15px;
  }

  .header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .header-title {
    width: 100%;
  }

  .header h1 {
    font-size: 24px;
  }

  .btn-logout {
    width: 100%;
    margin-left: 0;
  }

  .user-card {
    padding: 20px;
    cursor: pointer;
  }

  .user-card:hover {
    transform: translateY(-2px);
  }

  .user-info {
    flex-direction: column;
    text-align: center;
  }

  .avatar {
    width: 50px;
    height: 50px;
    font-size: 20px;
  }

  .click-hint {
    position: static;
    transform: none;
    margin-top: 12px;
    opacity: 1;
    justify-content: center;
  }

  .rules-card {
    padding: 20px;
  }

  .rules-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .rules-header h2 {
    font-size: 18px;
  }

  .btn-start {
    max-width: 100%;
  }
}
</style>
