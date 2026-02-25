import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 延迟加载页面组件
const Login = () => import('@/views/Login.vue')
const Lobby = () => import('@/views/Lobby.vue')
const Chat = () => import('@/views/Chat.vue')
const Survey = () => import('@/views/Survey.vue')
const Result = () => import('@/views/Result.vue')
const Profile = () => import('@/views/Profile.vue')

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/lobby',
    name: 'Lobby',
    component: Lobby,
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: Chat,
    meta: { requiresAuth: true }
  },
  {
    path: '/survey',
    name: 'Survey',
    component: Survey,
    meta: { requiresAuth: true }
  },
  {
    path: '/result',
    name: 'Result',
    component: Result,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const requiresAuth = to.meta.requiresAuth as boolean

  // 检查是否需要登录
  if (requiresAuth) {
    const userId = localStorage.getItem('userId')
    
    // 未登录或 userId 无效（0、null、undefined）时重定向到登录页
    if (!userId || userId === '0' || userId === 'null' || userId === 'undefined') {
      // 清除可能残留的无效数据
      localStorage.removeItem('userId')
      localStorage.removeItem('nickname')
      localStorage.removeItem('inviteCode')
      localStorage.removeItem('sessionId')
      localStorage.removeItem('opponentType')
      next({ name: 'Login' })
      return
    }
  }

  // 已登录用户访问登录页，重定向到大厅
  const userId = localStorage.getItem('userId')
  if (userId && userId !== '0' && userId !== 'null' && userId !== 'undefined' && to.name === 'Login') {
    next({ name: 'Lobby' })
    return
  }

  next()
})

export default router