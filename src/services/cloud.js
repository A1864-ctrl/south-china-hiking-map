/**
 * 云服务客户端：全局唯一实例（数据库 / 登录 / 存储 共用）。
 * endpoint + publishableKey 必传；web 端提供 WorkBuddy / 微信登录还需 oauthRelayBaseUrl。
 */
import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk'
import { PUBLIC_CONFIG } from './publicConfig.js'

export const cloud = createWorkBuddyCloud({
  endpoint: PUBLIC_CONFIG.endpoint,
  oauthRelayBaseUrl: PUBLIC_CONFIG.oauthRelayBaseUrl,
  publishableKey: PUBLIC_CONFIG.publishableKey
})

/** 把 { data, error } 信封转成抛错风格，调用点更干净 */
export function unwrap({ data, error }) {
  if (error) throw error
  return data
}

/** 当前登录用户的 id（未登录为 null） */
export async function currentUserId() {
  const { data: session } = await cloud.auth.getSession()
  return session?.user?.id || null
}
