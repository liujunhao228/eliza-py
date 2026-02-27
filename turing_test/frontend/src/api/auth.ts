// 认证相关 API
import api from './index'
import type { User, LoginResponse } from '@/types'

/**
 * 用户登录
 * @param inviteCode 邀请码（注册模式需要，登录模式可为空）
 * @param nickname 用户昵称（注册模式需要，登录模式可为空）
 * @param password 用户密码
 * @param isLoginMode 是否为登录模式（true: 用户名 + 密码登录，false: 邀请码注册/登录）
 */
export async function login(
  inviteCode: string,
  nickname: string,
  password: string,
  isLoginMode?: boolean
): Promise<LoginResponse> {
  if (isLoginMode) {
    // 登录模式：使用用户名 + 密码
    return api.post('/auth/login', {
      username: nickname,
      password: password
    })
  } else {
    // 注册/登录模式：使用邀请码 + 昵称 + 密码
    return api.post('/auth/login', {
      invite_code: inviteCode,
      nickname: nickname.trim(),
      password: password
    })
  }
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
