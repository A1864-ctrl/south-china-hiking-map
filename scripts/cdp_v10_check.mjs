/** 线上登录弹窗检查：node scripts/cdp_v10_check.mjs <页面URL> */
import { writeFileSync } from 'node:fs'

const base = process.argv[2] || 'https://south-china-hiking.app.workbuddy.host/?sharecode=NXC6GS3IF3'
const PORT = process.env.CDP_PORT || 9337
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const tabs = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = tabs.find((x) => x.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const errs = []
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    errs.push((m.params.args || []).map((a) => a.value || a.description || '').join(' ').slice(0, 90))
  }
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m)
    pending.delete(m.id)
  }
})
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const send = (method, params = {}) =>
  new Promise((res) => {
    const n = ++id
    pending.set(n, res)
    ws.send(JSON.stringify({ id: n, method, params }))
  })
const ev = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
  return r.result?.result?.value
}

const urlOf = (h) => (base.includes('?') ? `${base}#/${h}` : `${base}/#/${h}`)
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
await send('Page.navigate', { url: urlOf('') })
await wait(4500)

const loginSel = `document.querySelector('.side .login, .side [class*=login], .login-btn, [class*=login], .nav [class*=login]')`
console.log('[1] 登录按钮存在:', await ev(`!!(${loginSel})`))
await ev(`${loginSel}?.click()`)
await wait(1300)
console.log('[2] 弹窗出现:', await ev(`!!document.querySelector('.dlg')`))
console.log('[3] Tab:', await ev(`[...document.querySelectorAll('.tabs button')].map(b => b.textContent.trim()).join(' | ')`))
console.log('[4] 手机输入框:', await ev(`!!document.querySelector('input[type=tel]')`))
console.log('[5] 微信按钮:', await ev(`document.querySelector('.alt.wechat')?.textContent.trim()`))
console.log('[6] WB 按钮:', await ev(`[...document.querySelectorAll('.alt')].map(b => b.textContent.trim()).find(s => s.includes('WorkBuddy'))`))

// 切到邮箱 Tab
await ev(`[...document.querySelectorAll('.tabs button')].find(b => b.textContent.includes('邮箱'))?.click()`)
await wait(400)
console.log('[7] 邮箱输入框:', await ev(`!!document.querySelector('input[type=email]')`))

const shot = await send('Page.captureScreenshot', { format: 'png' })
writeFileSync('shots/v10-live-login.png', Buffer.from(shot.result.data, 'base64'))
console.log('截图 shots/v10-live-login.png')
console.log('ERRS', JSON.stringify(errs.slice(0, 3)))
ws.close()
