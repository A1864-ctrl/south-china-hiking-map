// 认证：手机验证码 / 邮箱验证码 / 微信 / WorkBuddy 四种登录（平台云服务托管）
// 资料含地区 / 性别 / 头像 / 背景与使用时长；密码支持设置 / 修改 / 邮箱找回
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { cloud } from '../services/cloud.js'

/** 登录入口用的回跳地址：站点根 + 当前业务参数（sharecode / 当前路由），根路径才能命中 index.html */
function buildRedirectTo() {
  const back = new URL(window.location.href)
  back.pathname = '/'
  for (const key of ['code', 'state', 'provider']) back.searchParams.delete(key)
  return back.toString()
}

/** 回调兑换完成后清掉 URL 上的授权参数：code/state 是一次性的，留着会让下次刷新重放已消费的 code */
function cleanAuthQuery() {
  const u = new URL(window.location.href)
  let dirty = false
  for (const key of ['code', 'state', 'provider', 'error']) {
    if (u.searchParams.has(key)) {
      u.searchParams.delete(key)
      dirty = true
    }
  }
  if (dirty) window.history.replaceState(window.history.state || null, '', u.toString())
}

/**
 * 启动时处理 OAuth 回调 / 恢复会话（每个页面入口调用一次，先于任何登录守卫）。
 * 回调按 provider 分发：workbuddy 与 wechat 各有自己的 handler，二者不可混用。
 */
async function restoreAuth() {
  const url = new URL(window.location.href)
  if (!url.searchParams.has('code') && !url.searchParams.has('error')) {
    const { data: session } = await cloud.auth.getSession()
    return { data: session || null, error: null }
  }
  const provider = url.searchParams.get('provider')
  let result
  if (provider === 'wechat') {
    result = await cloud.auth.handleWechatWebCallback.call(cloud.auth)
  } else if (provider === 'workbuddy') {
    result = await cloud.auth.handleWorkBuddyCallback.call(cloud.auth)
  } else {
    const e = new Error('授权回调缺少有效的登录方式，请重新登录')
    e.handled = true
    result = { data: null, error: e }
  }
  cleanAuthQuery()
  return result
}

/** 把手机号 / 邮箱变成默认昵称：138****8001 或邮箱前缀 */
function fallbackName(user) {
  if (user.name) return user.name
  const phone = (user.phone || '').replace(/\D/g, '')
  if (phone.length >= 8) return `${phone.slice(0, 3)}****${phone.slice(-4)}`
  if (phone) return `山友${phone.slice(-4)}`
  if (user.email) return user.email.split('@')[0]
  return '山友'
}

/** 手机号 13812348001 → 138****8001；邮箱 a@b.com → a***@b.com */
function maskTarget(t) {
  if (!t) return ''
  if (/^\d+$/.test(t)) return `${t.slice(0, 3)}****${t.slice(-4)}`
  const [a, b] = t.split('@')
  if (!b) return t
  return `${a.slice(0, 1)}***@${b}`
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref(null) // { account, name, avatarUrl, phone, email, provider }
  const profile = ref({
    nickname: '',
    bio: '',
    bg: 0,
    createdAt: '',
    regionProvince: '',
    regionCity: '',
    gender: 0,
    avatarPath: '',
    bgPath: '',
    activeSeconds: 0
  })
  const ready = ref(false) // 会话恢复完成（含回调处理）
  const dialogOpen = ref(false)
  const dialogTab = ref('login')
  const busy = ref(false)
  const oauthError = ref('')

  /** 头像 / 自定义背景的签名 URL（本会话内缓存，过期前由心跳刷新） */
  const avatarUrl = ref('')
  const bgUrl = ref('')

  /** 验证码登录：发码后的 challenge（含 verificationId 与 verify()），页面销毁前有效 */
  let otpChallenge = null
  /** 忘记密码：邮箱验证码 challenge */
  let resetChallenge = null

  const isLogged = computed(() => !!session.value)
  const nickname = computed(() => {
    if (!isLogged.value) return ''
    return profile.value.nickname || session.value.name || '山友'
  })
  const account = computed(() => (isLogged.value ? session.value.account : ''))
  const initial = computed(() => (nickname.value ? nickname.value.slice(0, 1) : ''))
  const bio = computed(() => profile.value.bio || '')
  const bgIndex = computed(() => profile.value.bg || 0)
  const joinDate = computed(() => profile.value.createdAt || '')
  /** 脱敏后的绑定信息，供账号安全卡展示 */
  const maskedPhone = computed(() => maskTarget(session.value?.phone || ''))
  const maskedEmail = computed(() => maskTarget(session.value?.email || ''))

  function applySession(s) {
    session.value = s
      ? {
          account: s.user.id,
          name: fallbackName(s.user),
          avatarUrl: s.user.avatarUrl || '',
          phone: s.user.phone || '',
          email: s.user.email || '',
          provider: s.user.provider || ''
        }
      : null
  }

  async function signedFor(path, ttl = 3600) {
    if (!path) return ''
    try {
      const signed = await cloud.storage.createSignedUrl(path, ttl)
      return signed?.data?.signedUrl || signed?.data?.url || ''
    } catch {
      return ''
    }
  }

  async function loadProfile() {
    if (!isLogged.value) return
    const { data, error } = await cloud.database.from('user_profiles').select('*').maybeSingle()
    if (!error && data) {
      profile.value = {
        nickname: data.nickname || '',
        bio: data.bio || '',
        bg: data.bg || 0,
        createdAt: data.updated_at ? data.updated_at.slice(0, 7) : profile.value.createdAt,
        regionProvince: data.region_province || '',
        regionCity: data.region_city || '',
        gender: data.gender || 0,
        avatarPath: data.avatar_path || '',
        bgPath: data.bg_path || '',
        activeSeconds: Number(data.active_seconds || 0)
      }
      avatarUrl.value = await signedFor(profile.value.avatarPath)
      bgUrl.value = await signedFor(profile.value.bgPath)
    }
  }

  /** 应用入口调用一次：处理回调 → 恢复会话 → 拉资料 */
  async function init() {
    try {
      const { data: sessionData, error } = await restoreAuth()
      if (error) {
        oauthError.value = error.message
      } else if (sessionData) {
        applySession(sessionData)
        await loadProfile()
      }
    } catch (e) {
      oauthError.value = e?.message || '登录状态恢复失败'
    } finally {
      ready.value = true
    }
  }

  /** OAuth 类登录的公共跳转（workbuddy / wechat 都走 Relay） */
  async function signInOAuth(provider) {
    busy.value = true
    oauthError.value = ''
    try {
      const { data, error } = await cloud.auth.signInWithOAuth({
        provider,
        redirectTo: buildRedirectTo()
      })
      if (error) {
        oauthError.value = error.message
        busy.value = false
        return
      }
      window.location.assign(data.url)
    } catch (e) {
      oauthError.value = e?.message || '无法发起登录'
      busy.value = false
    }
  }

  function signInWorkBuddy() {
    return signInOAuth('workbuddy')
  }
  function signInWechat() {
    return signInOAuth('wechat')
  }

  /**
   * 发送验证码（手机 / 邮箱二选一）。SDK 会把手机号归一化成 +86 形式。
   * 返回 { isNew }：新用户验证通过后自动注册，无需单独的注册表单。
   */
  async function sendCode(cred) {
    oauthError.value = ''
    const { data, error } = await cloud.auth.signInWithOtp(cred)
    if (error) throw error
    otpChallenge = data
    return { isNew: data.isExistingUser === false }
  }

  /** 提交验证码完成登录 / 注册；成功后拉资料并广播事件（main.js 负责加载云端数据） */
  async function verifyCode(token) {
    if (!otpChallenge) throw new Error('请先获取验证码')
    const { data: sessionData, error } = await otpChallenge.verify({ token })
    if (error) throw error
    otpChallenge = null
    applySession(sessionData)
    await loadProfile()
    window.dispatchEvent(new Event('yejing:auth-logged-in'))
  }

  /* ══════════ 账号安全 ══════════ */

  /** 登录状态下改密（需要原密码；从未设过密码的账号会返回明确错误） */
  async function changePassword(oldPassword, newPassword) {
    const { error } = await cloud.auth.resetPasswordForOld({ oldPassword, newPassword })
    if (error) throw error
  }

  /** 忘记密码第一步：向邮箱发验证码 */
  async function sendResetCode(email) {
    const { data, error } = await cloud.auth.resetPasswordForEmail(email.trim())
    if (error) throw error
    resetChallenge = data
  }

  /** 忘记密码第二步：验证码 + 新密码；成功后自动登录 */
  async function completeReset(code, newPassword) {
    if (!resetChallenge) throw new Error('请先获取邮箱验证码')
    const { data: sessionData, error } = await resetChallenge.updateUser({ nonce: code.trim(), password: newPassword })
    if (error) throw error
    resetChallenge = null
    applySession(sessionData)
    await loadProfile()
    window.dispatchEvent(new Event('yejing:auth-logged-in'))
  }

  async function logout() {
    try {
      await cloud.auth.signOut()
    } catch {
      /* 忽略 */
    }
    session.value = null
    profile.value = {
      nickname: '',
      bio: '',
      bg: 0,
      createdAt: '',
      regionProvince: '',
      regionCity: '',
      gender: 0,
      avatarPath: '',
      bgPath: '',
      activeSeconds: 0
    }
    avatarUrl.value = ''
    bgUrl.value = ''
  }

  /**
   * 资料：昵称 / 签名 / 背景预设 / 地区 / 性别 / 头像与自定义背景的存储路径。
   * avatarPath / bgPath 传 null 表示清除自定义图。
   */
  async function updateProfile(patch = {}) {
    if (!isLogged.value) return
    const row = {}
    if (patch.nickname !== undefined) row.nickname = String(patch.nickname).trim().slice(0, 16)
    if (patch.bio !== undefined) row.bio = String(patch.bio).slice(0, 60)
    if (patch.bg !== undefined) row.bg = patch.bg
    if (patch.regionProvince !== undefined) row.region_province = patch.regionProvince
    if (patch.regionCity !== undefined) row.region_city = patch.regionCity
    if (patch.gender !== undefined) row.gender = patch.gender
    if (patch.avatarPath !== undefined) row.avatar_path = patch.avatarPath
    if (patch.bgPath !== undefined) row.bg_path = patch.bgPath
    const { data, error } = await cloud.database
      .from('user_profiles')
      .upsert(row, { onConflict: 'owner_id' })
      .select()
      .single()
    if (error) throw error
    profile.value = {
      ...profile.value,
      nickname: data.nickname || '',
      bio: data.bio || '',
      bg: data.bg || 0,
      regionProvince: data.region_province || '',
      regionCity: data.region_city || '',
      gender: data.gender || 0,
      avatarPath: data.avatar_path || '',
      bgPath: data.bg_path || ''
    }
    if (patch.avatarPath !== undefined) avatarUrl.value = await signedFor(profile.value.avatarPath)
    if (patch.bgPath !== undefined) bgUrl.value = await signedFor(profile.value.bgPath)
  }

  /** 累计使用时长心跳：可见状态下每 60 秒上报一次（服务端函数累加并校验） */
  async function heartbeat(secs) {
    if (!isLogged.value || !secs || secs <= 0) return
    try {
      const { data, error } = await cloud.database.rpc('bump_usage', { p_secs: secs })
      if (!error && data !== null && data !== undefined) {
        profile.value = { ...profile.value, activeSeconds: Number(data) }
      }
    } catch {
      /* 心跳失败静默：下次再报 */
    }
  }

  function openDialog(tab = 'login') {
    dialogTab.value = tab
    dialogOpen.value = true
  }
  function closeDialog() {
    dialogOpen.value = false
    busy.value = false
  }
  /** 兼容旧调用点：平台会话自动续期，无需手动 touch */
  function touch() {}
  function ensureFresh() {}

  return {
    session,
    profile,
    ready,
    oauthError,
    isLogged,
    nickname,
    account,
    initial,
    dialogOpen,
    dialogTab,
    busy,
    avatarUrl,
    bgUrl,
    maskedPhone,
    maskedEmail,
    signInWorkBuddy,
    signInWechat,
    sendCode,
    verifyCode,
    changePassword,
    sendResetCode,
    completeReset,
    heartbeat,
    logout,
    updateProfile,
    loadProfile,
    bio,
    bgIndex,
    joinDate,
    init,
    touch,
    ensureFresh,
    openDialog,
    closeDialog
  }
})
