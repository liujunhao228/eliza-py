import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw, RouteMeta } from 'vue-router'
import { STORAGE_KEYS } from '@/utils/constants'

// 延迟加载页面组件
const Login = () => import('@/views/Login.vue')
const Lobby = () => import('@/views/Lobby.vue')
const Chat = () => import('@/views/Chat/index.vue')
const Survey = () => import('@/views/Survey.vue')
const Result = () => import('@/views/Result.vue')
const Profile = () => import('@/views/profile/index.vue')
const SessionDetail = () => import('@/views/SessionDetail.vue')
const SharedSession = () => import('@/views/SharedSession.vue')

/**
 * 路由名称类型
 */
export type RouteName =
  | 'Login'
  | 'Lobby'
  | 'Chat'
  | 'Survey'
  | 'Result'
  | 'Profile'
  | 'SessionDetail'
  | 'SharedSession'

/**
 * 扩展路由元信息类型
 */
interface AppRouteMeta extends RouteMeta {
  /** 是否需要登录 */
  requiresAuth: boolean
  /** 页面标题 */
  title?: string
  /** 是否保持滚动位置 */
  keepScroll?: boolean
}

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false } satisfies AppRouteMeta
  },
  {
    path: '/lobby',
    name: 'Lobby',
    component: Lobby,
    meta: { 
      requiresAuth: true,
      title: '大厅'
    } satisfies AppRouteMeta
  },
  {
    path: '/chat',
    name: 'Chat',
    component: Chat,
    meta: { 
      requiresAuth: true,
      title: '聊天'
    } satisfies AppRouteMeta
  },
  {
    path: '/survey',
    name: 'Survey',
    component: Survey,
    meta: { 
      requiresAuth: true,
      title: '问卷'
    } satisfies AppRouteMeta
  },
  {
    path: '/result',
    name: 'Result',
    component: Result,
    meta: { 
      requiresAuth: true,
      title: '结果'
    } satisfies AppRouteMeta
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: {
      requiresAuth: true,
      title: '个人中心'
    } satisfies AppRouteMeta
  },
  {
    path: '/session/:id',
    name: 'SessionDetail',
    component: SessionDetail,
    meta: {
      requiresAuth: true,
      title: '会话详情'
    } satisfies AppRouteMeta
  },
  {
    path: '/share/:token',
    name: 'SharedSession',
    component: SharedSession,
    meta: { 
      requiresAuth: false,  // 公开访问，无需登录
      title: '共享会话'
    } satisfies AppRouteMeta
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    // 如果页面设置了保持滚动位置
    if (to.meta.keepScroll && savedPosition) {
      return savedPosition
    }
    // 默认滚动到顶部
    return { top: 0 }
  }
})

/**
 * 判断路由是否需要认证
 * 使用类型守卫函数确保类型安全
 */
function isAuthRoute(meta: RouteMeta): boolean {
  return (meta as AppRouteMeta).requiresAuth === true
}

/**
 * 验证用户 ID 是否有效
 */
function isValidUserId(userId: string | null): boolean {
  if (!userId) return false
  const invalidValues = ['0', 'null', 'undefined', '']
  return !invalidValues.includes(userId)
}

/**
 * 清除用户本地存储数据
 */
function clearUserData(): void {
  localStorage.removeItem(STORAGE_KEYS.USER_ID)
  localStorage.removeItem(STORAGE_KEYS.NICKNAME)
  localStorage.removeItem(STORAGE_KEYS.INVITE_CODE)
  localStorage.removeItem(STORAGE_KEYS.SESSION_ID)
  localStorage.removeItem(STORAGE_KEYS.OPPONENT_TYPE)
}

// 路由守卫
router.beforeEach((to, _from, next) => {
  const requiresAuth = isAuthRoute(to.meta)

  // 检查是否需要登录
  if (requiresAuth) {
    const userId = localStorage.getItem(STORAGE_KEYS.USER_ID)

    // 未登录或 userId 无效时重定向到登录页
    if (!isValidUserId(userId)) {
      // 清除可能残留的无效数据
      clearUserData()
      next({ name: 'Login' })
      return
    }
  }

  // 已登录用户访问登录页，重定向到大厅
  const userId = localStorage.getItem(STORAGE_KEYS.USER_ID)
  if (isValidUserId(userId) && to.name === 'Login') {
    next({ name: 'Lobby' })
    return
  }

  next()
})

export default router
