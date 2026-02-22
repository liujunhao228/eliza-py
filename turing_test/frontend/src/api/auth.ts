// 认证相关API
import api from './index'
import type { User } from '@/types'

/**
 * 验证邀请码
 */
export async function verifyInviteCode(code: string): Promise<any> {
  return api.post('/login', { code })
}

/**
 * 用户注册/登录
 */
export async function registerUser(code: string, nickname: string): Promise<User> {
  return api.post('/register', { code, nickname })
}

/**
 * 获取用户信息
 */
export async function getUserInfo(userId: number): Promise<User> {
  return api.get(`/user/${userId}`)
}