<template>
  <router-view />
  <BaseToast ref="toastRef" />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { BaseToast, setToastInstance } from '@/components/common'

// Toast 实例引用
const toastRef = ref<InstanceType<typeof BaseToast> | null>(null)

// 在组件挂载后设置 Toast 实例
onMounted(() => {
  if (toastRef.value) {
    setToastInstance(toastRef.value)
  }
})
</script>

<style>
/* 导入主题样式 */
@import './styles/theme.css';

/* App 根元素样式 */
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  position: relative;
}

/* 全局过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
