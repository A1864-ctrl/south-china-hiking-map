<script setup>
/**
 * 登录弹窗：四种登录方式（平台云服务托管）
 * 1) 手机号验证码（默认，登录/注册一体） 2) 邮箱验证码 3) 微信（快捷/扫码） 4) WorkBuddy 账号
 * 另提供忘记密码：邮箱验证码重置（成功后自动登录）
 */
import { computed, onUnmounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()

const shown = computed(() => auth.dialogOpen)

/* ── 验证码登录 ── */
const otpKind = ref('phone') // phone | email
const phone = ref('')
const email = ref('')
const token = ref('')
const sending = ref(false)
const verifying = ref(false)
const localErr = ref('')
const countdown = ref(0)
let timer = null

const isLoggedShown = computed(() => auth.isLogged)

const PHONE_RE = /^1[3-9]\d{9}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const cred = computed(() =>
  otpKind.value === 'phone' ? { phone: phone.value.trim() } : { email: email.value.trim() }
)
const targetValid = computed(() =>
  otpKind.value === 'phone' ? PHONE_RE.test(phone.value.trim()) : EMAIL_RE.test(email.value.trim())
)

function fail(msg) {
  localErr.value = msg
}

async function send() {
  localErr.value = ''
  if (!targetValid.value) {
    fail(otpKind.value === 'phone' ? '请输入正确的 11 位手机号' : '请输入正确的邮箱地址')
    return
  }
  sending.value = true
  try {
    await auth.sendCode(cred.value)
    countdown.value = 60
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        clearInterval(timer)
        timer = null
      }
    }, 1000)
  } catch (e) {
    fail(friendly(e, '验证码发送失败'))
  } finally {
    sending.value = false
  }
}

async function submit() {
  localErr.value = ''
  const code = token.value.trim()
  if (!targetValid.value) {
    fail(otpKind.value === 'phone' ? '请输入正确的 11 位手机号' : '请输入正确的邮箱地址')
    return
  }
  if (!/^\d{4,8}$/.test(code)) {
    fail('请输入收到的验证码')
    return
  }
  verifying.value = true
  try {
    await auth.verifyCode(code)
    token.value = ''
  } catch (e) {
    fail(friendly(e, '验证码校验失败'))
  } finally {
    verifying.value = false
  }
}

/** 平台错误转可读提示：未开通的登录方式给出开通位置 */
function friendly(e, fallback) {
  const msg = e?.message || fallback || '操作失败'
  if (/未打开|未开通|not enabled|disabled|provider/i.test(msg)) {
    return `${msg} —— 该登录方式需要在 WorkBuddy「设置 → 数据管理 → 应用」的认证设置里打开`
  }
  return msg
}

function switchKind(k) {
  otpKind.value = k
  localErr.value = ''
  token.value = ''
}

/* ── 忘记密码（邮箱验证码重置，成功后自动登录） ── */
const resetting = ref(false)
const resetStep = ref(1)
const rstEmail = ref('')
const rstCode = ref('')
const rstNext = ref('')
const rstBusy = ref(false)

async function rstSend() {
  localErr.value = ''
  if (!EMAIL_RE.test(rstEmail.value.trim())) {
    fail('请输入正确的邮箱地址')
    return
  }
  rstBusy.value = true
  try {
    await auth.sendResetCode(rstEmail.value)
    resetStep.value = 2
  } catch (e) {
    fail(friendly(e, '发送失败：确认该邮箱已绑定账号'))
  } finally {
    rstBusy.value = false
  }
}

async function rstComplete() {
  localErr.value = ''
  const code = rstCode.value.trim()
  const next = rstNext.value
  if (!/^\d{4,8}$/.test(code)) {
    fail('请输入邮箱里的验证码')
    return
  }
  if (next.length < 8 || !/[a-zA-Z]/.test(next) || !/\d/.test(next)) {
    fail('新密码至少 8 位，且同时包含字母和数字')
    return
  }
  rstBusy.value = true
  try {
    await auth.completeReset(code, next)
    resetting.value = false
    resetStep.value = 1
    rstEmail.value = ''
    rstCode.value = ''
    rstNext.value = ''
  } catch (e) {
    fail(friendly(e, '重置失败：验证码可能已过期'))
  } finally {
    rstBusy.value = false
  }
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

async function goWechat() {
  localErr.value = ''
  await auth.signInWechat()
}
async function goWorkBuddy() {
  localErr.value = ''
  await auth.signInWorkBuddy()
}
</script>

<template>
  <div v-if="shown" class="mask" @click.self="auth.closeDialog" @keydown.esc="auth.closeDialog">
    <div class="dlg" role="dialog" aria-label="登录">
      <button class="close" aria-label="关闭" @click="auth.closeDialog">×</button>

      <template v-if="!isLoggedShown">
        <span class="mark">
          <svg viewBox="0 0 24 24" width="24" height="24">
            <path d="M12 12a4 4 0 100-8 4 4 0 000 8zm-7 8a7 7 0 1114 0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </span>
        <h3>登录野径</h3>
        <p class="sub">
          登录后：收藏、帖子、路况、报备、装备库全部上云，换设备登录都在；
          别人也能看到你发的帖子和路况。
        </p>

        <template v-if="!resetting">
          <!-- 验证码登录：手机 / 邮箱 -->
          <div class="tabs" role="tablist">
            <button :class="{ on: otpKind === 'phone' }" @click="switchKind('phone')">手机验证码</button>
            <button :class="{ on: otpKind === 'email' }" @click="switchKind('email')">邮箱验证码</button>
          </div>

          <form class="otp" @submit.prevent="submit">
            <label v-if="otpKind === 'phone'" class="row">
              <span class="lab">手机号</span>
              <input v-model="phone" type="tel" maxlength="11" placeholder="用于接收短信验证码" autocomplete="tel" />
            </label>
            <label v-else class="row">
              <span class="lab">邮箱</span>
              <input v-model="email" type="email" maxlength="60" placeholder="用于接收邮箱验证码" autocomplete="email" />
            </label>
            <label class="row">
              <span class="lab">验证码</span>
              <input v-model="token" type="text" inputmode="numeric" maxlength="8" placeholder="请输入验证码" autocomplete="one-time-code" />
              <button type="button" class="send" :disabled="sending || countdown > 0 || !targetValid" @click="send">
                {{ sending ? '发送中…' : countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
              </button>
            </label>
            <button type="submit" class="primary" :disabled="verifying">
              {{ verifying ? '登录中…' : '登录 / 注册' }}
            </button>
          </form>
          <p class="fine code-note">未注册也能直接登录：验证通过后自动创建账号，全程无需密码。</p>

          <div class="divider"><i></i><span>或一键登录</span><i></i></div>

          <button class="alt wechat" :disabled="auth.busy" @click="goWechat">
            <svg viewBox="0 0 24 24" width="17" height="17">
              <path
                d="M9.6 4.2c-3.6 0-6.6 2.4-6.6 5.4 0 1.7 1 3.2 2.4 4.2l-.6 2 2.2-1.1c.8.2 1.6.4 2.6.4h.4a5 5 0 01-.2-1.4c0-3 2.9-5.4 6.4-5.4h.3c-.6-2.3-3.3-4.1-6.9-4.1zM7.4 7.2a.8.8 0 110 1.6.8.8 0 010-1.6zm4.4 0a.8.8 0 110 1.6.8.8 0 010-1.6zm3.4 3c-2.9 0-5.2 1.9-5.2 4.3 0 2.4 2.3 4.3 5.2 4.3.6 0 1.2-.1 1.8-.3l1.8.9-.5-1.7c1.2-.8 2-2 2-3.2 0-2.4-2.3-4.3-5.1-4.3zm-1.7 2.1a.7.7 0 110 1.4.7.7 0 010-1.4zm3.4 0a.7.7 0 110 1.4.7.7 0 010-1.4z"
                fill="currentColor"
              />
            </svg>
            微信登录
          </button>
          <button class="alt" :disabled="auth.busy" @click="goWorkBuddy">
            <svg viewBox="0 0 24 24" width="15" height="15">
              <path d="M12 12a4 4 0 100-8 4 4 0 000 8zm-7 8a7 7 0 1114 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            </svg>
            {{ auth.busy ? '正在跳转…' : '使用 WorkBuddy 登录' }}
          </button>

          <p v-if="localErr || auth.oauthError" class="err">{{ localErr || auth.oauthError }}</p>
          <p class="fine">
            验证码与授权均由平台官方通道完成，本站拿不到你的密码。
            授权完成后会自动回到当前页面。
            <button type="button" class="linkish" @click="resetting = true; localErr = ''">忘记密码？</button>
          </p>
        </template>

        <!-- 忘记密码：邮箱验证码重置 -->
        <template v-else>
          <form v-if="resetStep === 1" class="otp" @submit.prevent="rstSend">
            <p class="sub left">输入账号绑定的邮箱，平台会发一个验证码（手机号找回暂未开放）。</p>
            <label class="row">
              <span class="lab">邮箱</span>
              <input v-model="rstEmail" type="email" maxlength="60" placeholder="you@example.com" autocomplete="email" />
            </label>
            <button type="submit" class="primary" :disabled="rstBusy">
              {{ rstBusy ? '发送中…' : '发送验证码' }}
            </button>
          </form>
          <form v-else class="otp" @submit.prevent="rstComplete">
            <label class="row">
              <span class="lab">验证码</span>
              <input v-model="rstCode" type="text" inputmode="numeric" maxlength="8" placeholder="查看邮箱收件箱" />
            </label>
            <label class="row">
              <span class="lab">新密码</span>
              <input v-model="rstNext" type="password" maxlength="40" placeholder="至少 8 位，含字母和数字" autocomplete="new-password" />
            </label>
            <button type="submit" class="primary" :disabled="rstBusy">
              {{ rstBusy ? '提交中…' : '重置并登录' }}
            </button>
          </form>
          <p v-if="localErr" class="err">{{ localErr }}</p>
          <p class="fine">
            <button type="button" class="linkish" @click="resetting = false; resetStep = 1; localErr = ''">← 回到登录</button>
          </p>
        </template>
      </template>

      <template v-else>
        <span class="mark on">{{ auth.initial }}</span>
        <h3>{{ auth.nickname }}</h3>
        <p class="sub">已登录。收藏、帖子、报备、装备库已同步到云端。</p>
        <button class="primary ghost" @click="auth.closeDialog">留在本页</button>
        <button class="primary ghost danger" @click="auth.logout(); auth.closeDialog()">退出登录</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 4000;
  background: rgba(20, 30, 24, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.dlg {
  position: relative;
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 10px;
  padding: 28px 28px 24px;
  text-align: center;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}
.close {
  position: absolute;
  right: 10px;
  top: 10px;
  border: none;
  background: none;
  font-size: 1.2rem;
  color: var(--gray-light);
  cursor: pointer;
  line-height: 1;
}
.mark {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: var(--forest-soft);
  color: var(--forest);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.mark.on {
  font-family: var(--serif);
  font-size: 1.4rem;
  font-weight: 600;
}
h3 {
  font-family: var(--serif);
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 8px;
}
.sub {
  font-size: 0.76rem;
  color: var(--gray);
  line-height: 1.85;
  margin-bottom: 14px;
}
.sub.left {
  text-align: left;
  margin-bottom: 10px;
}
.tabs {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 12px;
}
.tabs button {
  flex: 1;
  border: none;
  background: #fcfaf5;
  padding: 8px 0;
  font-size: 0.74rem;
  color: var(--gray);
  cursor: pointer;
  transition: 0.16s;
}
.tabs button + button {
  border-left: 1px solid var(--line);
}
.tabs button.on {
  background: var(--forest);
  color: #fff;
}
.otp {
  text-align: left;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0 10px;
  margin-bottom: 9px;
  background: #fcfaf5;
  transition: 0.16s;
}
.row:focus-within {
  border-color: var(--forest-light);
  background: #fff;
}
.lab {
  flex: 0 0 auto;
  font-size: 0.7rem;
  color: var(--gray);
  white-space: nowrap;
}
.row input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.8rem;
  padding: 10px 0;
  color: var(--ink);
  font-family: inherit;
}
.send {
  flex: 0 0 auto;
  border: none;
  background: none;
  color: var(--forest);
  font-size: 0.7rem;
  cursor: pointer;
  padding: 4px 0 4px 8px;
  white-space: nowrap;
}
.send:disabled {
  color: var(--gray-light);
  cursor: not-allowed;
}
.primary {
  width: 100%;
  border: none;
  background: var(--forest);
  color: #fff;
  border-radius: 6px;
  padding: 11px 0;
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  cursor: pointer;
  margin-top: 2px;
}
.primary:hover {
  background: var(--forest-dark);
}
.primary:disabled {
  opacity: 0.6;
  cursor: wait;
}
.primary.ghost {
  background: #fff;
  color: var(--ink-soft);
  border: 1px solid var(--line);
  margin-bottom: 8px;
}
.primary.ghost:hover {
  border-color: var(--forest-light);
  color: var(--forest);
  background: #fff;
}
.primary.ghost.danger {
  color: #a9462f;
  border-color: #e0c5be;
}
.divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 15px 0 12px;
  color: var(--gray-light);
}
.divider i {
  flex: 1;
  height: 1px;
  background: var(--line);
}
.divider span {
  font-size: 0.62rem;
  letter-spacing: 0.12em;
}
.alt {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  border-radius: 6px;
  padding: 10px 0;
  font-size: 0.78rem;
  cursor: pointer;
  margin-bottom: 8px;
  transition: 0.16s;
}
.alt:hover {
  border-color: var(--forest-light);
  color: var(--forest);
}
.alt.wechat {
  color: #1a7f37;
}
.alt.wechat:hover {
  border-color: #1a7f37;
  background: #f2faf5;
  color: #1a7f37;
}
.alt:disabled {
  opacity: 0.6;
  cursor: wait;
}
.err {
  font-size: 0.7rem;
  color: #a9462f;
  margin-top: 8px;
  line-height: 1.7;
}
.fine {
  font-size: 0.62rem;
  color: var(--gray-light);
  line-height: 1.8;
  margin-top: 10px;
}
.code-note {
  margin-top: 6px;
}
.linkish {
  border: none;
  background: none;
  padding: 0;
  font-size: inherit;
  color: var(--forest);
  cursor: pointer;
  text-decoration: underline;
  font-family: inherit;
}
</style>
