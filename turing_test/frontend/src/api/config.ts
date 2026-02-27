/**
 * 系统配置 API
 * 
 * 提供前端所需的配置信息，确保前后端配置同步。
 */

import api from './index'

export interface ConfigResponse {
  meta_conversation: {
    enabled: boolean
    keywords: string[]
  }
}

/**
 * 获取系统配置
 */
export async function getSystemConfig(): Promise<ConfigResponse> {
  return api.get('/config')
}
