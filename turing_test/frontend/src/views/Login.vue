<template>
  <div class="login-container">
    <BaseCard class="login-card">
      <div class="header">
        <h1>🧪 图灵测试社交实验</h1>
        <p class="subtitle">你是一个对话者，还是被测试的 AI？</p>
      </div>

      <!-- 步骤 1：验证邀请码 -->
      <div v-if="step === 1" class="step">
        <h3>请输入邀请码</h3>
        <BaseInput
          v-model="inviteCode"
          placeholder="6 位邀请码"
          :maxlength="8"
          size="large"
          clearable
          @keydown.enter="verifyCode"
        />
        <BaseButton
          type="primary"
          size="large"
          :loading="loading"
          block
          @click="verifyCode"
        >
          验证邀请码
        </BaseButton>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      </div>

      <!-- 步骤 2：设置昵称 -->
      <div v-if="step === 2" class="step">
        <h3>设置你的昵称</h3>
        <BaseInput
          v-model="nickname"
          :placeholder="defaultNickname"
          :maxlength="20"
          :minlength="2"
          size="large"
          clearable
          @keydown.enter="registerUser"
        />
        <p class="hint-text">昵称长度 2-20 个字符，仅支持中文、英文、数字和#符号</p>
        <BaseButton
          type="primary"
          size="large"
          :loading="loading"
          block
          @click="registerUser"
        >
          开始实验
        </BaseButton>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      </div>

      <!-- 实验说明 -->
      <div class="info-box">
        <h4>📋 实验说明</h4>
        <p class="experiment-intro">
          这是一个研究性学习项目。你将随机匹配到一位对话者，
          <strong>可能是真人，也可能是 AI</strong>。
          请通过聊天判断对方身份，并在对话结束后提交你的判断。
        </p>
        <h5>🔍 匹配规则</h5>
        <ul>
          <li><strong>真人优先</strong>：系统会优先将你与等待中的真人匹配</li>
          <li><strong>AI 备选</strong>：若无真人等待或超时 30 秒，将自动匹配 AI</li>
          <li><strong>匿名对话</strong>：双方身份保密，直到实验结束才揭晓</li>
        </ul>
      </div>
    </BaseCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { login, verifyInviteCode } from '@/api/auth'
import { BaseCard, BaseInput, BaseButton } from '@/components/common'

const router = useRouter()
const userStore = useUserStore()

// 状态
const step = ref(1)
const inviteCode = ref('')
const nickname = ref('')
const loading = ref(false)
const errorMessage = ref('')

// 生成默认昵称
const defaultNickname = `访客#${Math.floor(100 + Math.random() * 900)}`

// 验证昵称格式
function validateNickname(nick: string): boolean {
  // 长度检查
  if (nick.length < 2 || nick.length > 20) {
    errorMessage.value = '昵称长度应为 2-20 个字符'
    return false
  }
  
  // 格式检查（仅允许中文、英文、数字、#）
  const nicknameRegex = /^[\u4e00-\u9fa5a-zA-Z0-9#]+$/
  if (!nicknameRegex.test(nick)) {
    errorMessage.value = '昵称仅支持中文、英文、数字和#符号'
    return false
  }
  
  return true
}

// 验证邀请码
async function verifyCode() {
  if (!inviteCode.value.trim()) {
    errorMessage.value = '请输入邀请码'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    await verifyInviteCode(inviteCode.value.trim().toUpperCase())
    step.value = 2
    // 设置默认昵称
    nickname.value = defaultNickname
    errorMessage.value = ''
  } catch (error: any) {
    errorMessage.value = error.message || '邀请码无效'
  } finally {
    loading.value = false
  }
}

// 登录/注册
async function registerUser() {
  if (!nickname.value.trim()) {
    errorMessage.value = '请输入昵称'
    return
  }

  // 验证昵称格式
  if (!validateNickname(nickname.value.trim())) {
    return
  }

  loading.value = true

  try {
    // 直接登录，如果用户不存在会自动创建，同时传递昵称
    const user = await login(inviteCode.value.trim().toUpperCase(), nickname.value.trim())
    userStore.setUser(user)
    errorMessage.value = ''
    router.push('/lobby')
  } catch (error: any) {
    errorMessage.value = error.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ==============================================
   Login 视图样式 - 使用主题系统
   ============================================== */

.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: var(--bg-primary);
}

.login-card {
  background: var(--bg-surface);
  border-radius: var(--rounded-2xl);
  box-shadow: var(--shadow-2xl);
  padding: 40px;
  max-width: 480px;
  width: 100%;
  border: 1px solid var(--border-primary);
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 28px;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
}

.step {
  margin-bottom: 30px;
}

.step h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: 20px;
  text-align: center;
}

.btn-full {
  width: 100%;
  margin-top: 16px;
  font-size: 16px;
  padding: 12px 20px;
  background: var(--color-primary-gradient);
  border: none;
  color: white;
}

.btn-full:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.error-message {
  color: var(--color-error);
  text-align: center;
  margin-top: 12px;
  font-size: 14px;
}

.hint-text {
  color: var(--text-secondary);
  text-align: center;
  margin-top: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

.info-box {
  background: var(--bg-tertiary);
  border-radius: var(--rounded-md);
  padding: 20px;
  border-left: 4px solid var(--color-primary-600);
}

.info-box h4 {
  font-size: 16px;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.info-box h5 {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 16px 0 8px 0;
}

.experiment-intro {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 16px 0;
}

.experiment-intro strong {
  color: var(--color-primary-600);
}

.info-box ul {
  margin: 0;
  padding-left: 20px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.info-box li {
  margin-bottom: 8px;
}

.info-box strong {
  color: var(--color-primary-600);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-card {
    padding: 30px;
  }

  .header h1 {
    font-size: 24px;
  }

  .subtitle {
    font-size: 14px;
  }
}
</style>
