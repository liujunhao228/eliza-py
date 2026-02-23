// 认证相关 API
import api from './index'
import type { User } from '@/types'

/**
 * 用户登录/注册
 * 使用邀请码登录，如果用户不存在则自动注册
 */
export async function login(code: string): Promise<User> {
  return api.post('/auth/login', { invite_code: code })
}

/**
 * 用户注册
 * 使用邀请码和用户名注册新用户
 */
export async function register(code: string, username: string): Promise<User> {
  return api.post('/auth/register', { invite_code: code, username })
}

/**
 * 验证邀请码
 */
export async function verifyInviteCode(code: string): Promise<any> {
  return api.get(`/auth/verify/${code}`)
}

/**
 * 获取用户信息
 */
export async function getUserInfo(userId: number): Promise<User> {
  return api.get(`/user/${userId}`)
}
