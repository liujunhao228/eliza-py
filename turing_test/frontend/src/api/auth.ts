// 认证相关 API
import api from './index'
import type { User, LoginResponse } from '@/types'

/**
 * 用户登录/注册
 * 使用邀请码登录，如果用户不存在则自动注册
 * @param code 邀请码
 * @param nickname 用户昵称（可选，新用户注册时必需）
 */
export async function login(code: string, nickname?: string): Promise<LoginResponse> {
  const payload: { invite_code: string; nickname?: string } = { invite_code: code }
  if (nickname && nickname.trim()) {
    payload.nickname = nickname.trim()
  }
  return api.post('/auth/login', payload)
}

/**
 * 用户注册
 * 使用邀请码和用户名注册新用户
 * @deprecated 请使用 login 函数，已支持自动注册
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
