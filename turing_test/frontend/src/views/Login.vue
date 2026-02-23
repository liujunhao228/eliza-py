<template>
  <div class="login-container">
    <div class="login-card">
      <div class="header">
        <h1>🧪 图灵测试社交实验</h1>
        <p class="subtitle">你是一个对话者，还是被测试的 AI？</p>
      </div>

      <!-- 步骤 1：验证邀请码 -->
      <div v-if="step === 1" class="step">
        <h3>请输入邀请码</h3>
        <el-input
          v-model="inviteCode"
          placeholder="6 位邀请码"
          maxlength="8"
          size="large"
          clearable
          @keyup.enter="verifyCode"
        />
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="verifyCode"
          class="btn-full"
        >
          验证邀请码
        </el-button>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      </div>

      <!-- 步骤 2：登录 -->
      <div v-if="step === 2" class="step">
        <h3>设置你的昵称</h3>
        <el-input
          v-model="nickname"
          placeholder="你想使用的昵称"
          maxlength="20"
          size="large"
          clearable
          @keyup.enter="registerUser"
        />
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="registerUser"
          class="btn-full"
        >
          开始实验
        </el-button>
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { login, register, verifyInviteCode } from '@/api/auth'

const router = useRouter()
const userStore = useUserStore()

// 状态
const step = ref(1)
const inviteCode = ref('')
const nickname = ref('')
const loading = ref(false)
const errorMessage = ref('')

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
    ElMessage.warning('请输入昵称')
    return
  }

  loading.value = true

  try {
    // 直接登录，如果用户不存在会自动创建
    const user = await login(inviteCode.value.trim().toUpperCase())
    userStore.setUser(user)
    ElMessage.success('登录成功！')
    router.push('/lobby')
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 40px;
  max-width: 480px;
  width: 100%;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 16px;
  color: #666;
  margin: 0;
}

.step {
  margin-bottom: 30px;
}

.step h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.btn-full {
  width: 100%;
  margin-top: 16px;
  font-size: 16px;
  padding: 12px 20px;
}

.error-message {
  color: #f56c6c;
  text-align: center;
  margin-top: 12px;
  font-size: 14px;
}

.info-box {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 20px;
  border-left: 4px solid #667eea;
}

.info-box h4 {
  font-size: 16px;
  color: #333;
  margin: 0 0 12px 0;
}

.info-box h5 {
  font-size: 14px;
  color: #666;
  margin: 16px 0 8px 0;
}

.experiment-intro {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 16px 0;
}

.experiment-intro strong {
  color: #667eea;
}

.info-box ul {
  margin: 0;
  padding-left: 20px;
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
}

.info-box li {
  margin-bottom: 8px;
}

.info-box strong {
  color: #667eea;
}
</style>
