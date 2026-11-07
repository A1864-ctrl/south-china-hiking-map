/** v11 游客侧检查：登录弹窗（忘记密码入口与流程）+ 关键页 console + /me 未登录门 */
import { writeFileSync } from 'node:fs'

const BASE = process.argv[2] || 'http://127.0.0.1:5178'
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
  if (m.method === 'Runtime.exceptionThrown') errs.push('EXC ' + m.params.exceptionDetails.text)
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

await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })

// 1) 登录弹窗 + 忘记密码入口
await send('Page.navigate', { url: BASE.includes('?') ? BASE + '#/' : BASE + '/' })
await wait(6000)
await ev(`document.querySelector('.side .login, .side [class*=login], .login-btn, [class*=login]')?.click()`)
await wait(1800)
console.log('[1] 弹窗出现:', await ev(`!!document.querySelector('.dlg')`))
console.log('[2] 忘记密码入口:', await ev(`document.querySelector('.linkish')?.textContent.trim()`))
await ev(`document.querySelector('.linkish')?.click()`)
await wait(500)
console.log('[3] 找回面板出现:', await ev(`!!document.querySelector('.otp')`), '| 上一步按钮:', await ev(`[...document.querySelectorAll('.linkish')].some(b=>b.textContent.includes('回到登录'))`))
// 错误路径：格式非法的邮箱
await ev(`(()=>{const i=document.querySelector('input[type=email]');i.value='bad-mail';i.dispatchEvent(new Event('input',{bubbles:true}));return 1})()`)
await ev(`document.querySelector('.otp .primary')?.click()`)
await wait(400)
console.log('[4] 非法邮箱拦截:', await ev(`document.querySelector('.err')?.textContent.trim()`))
// 回到登录
await ev(`[...document.querySelectorAll('.linkish')].find(b=>b.textContent.includes('回到登录'))?.click()`)
await wait(400)
console.log('[5] 回到登录面板:', await ev(`!!document.querySelector('.tabs')`))

// 2) /me 未登录门
await send('Page.navigate', { url: `${BASE}/#/me` })
await wait(5000)
console.log('[6] /me 未登录门:', await ev(`!!document.querySelector('.gate-card')`))

// 3) 关键页 console
for (const h of ['community', 'camps', 'weather']) {
  await send('Page.navigate', { url: `${BASE}/#/${h}` })
  await wait(3500)
}
console.log('[7] console 错误数:', errs.length, errs.slice(0, 3))

const shot = await send('Page.captureScreenshot', { format: 'png' })
writeFileSync('shots/v11-guest.png', Buffer.from(shot.result.data, 'base64'))
console.log('截图 shots/v11-guest.png')
ws.close()
