/**
 * 用 CDP 注入登录态后截图。
 * 用法：node scripts/cdp_me.mjs <url> <out.png> [width] [height]
 */
import { writeFileSync } from 'node:fs'

const PORT = process.env.CDP_PORT || 9336
const [, , url, out, w = '1200', h = '900'] = process.argv

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = targets.find((t) => t.type === 'page')
if (!page) throw new Error('没有可用页面')

const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data)
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id)
    pending.delete(msg.id)
    msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg)
  }
})
await new Promise((r) => ws.addEventListener('open', r, { once: true }))

const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const n = ++id
    pending.set(n, { resolve, reject })
    ws.send(JSON.stringify({ id: n, method, params }))
  })

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: Number(w), height: Number(h), deviceScaleFactor: 1, mobile: false
})

await send('Page.navigate', { url: 'about:blank' })
await wait(300)
await send('Page.navigate', { url })
await wait(2400)

const session = {
  account: '19237463455',
  nickname: '扣山',
  jti: 'a1b2c3d4e5f60718',
  exp: Date.now() + 7 * 24 * 3600 * 1000 - 40 * 60 * 1000,
  loginAt: Date.now() - 40 * 60 * 1000,
  lastSeen: Date.now()
}
const users = {
  '19237463455': { account: '19237463455', nickname: '扣山', salt: 'deadbeef', hash: 'x', createdAt: Date.now() }
}
await send('Runtime.evaluate', {
  expression: `
    localStorage.setItem('yejing:users:v2', ${JSON.stringify(JSON.stringify(users))});
    localStorage.setItem('yejing:session:v2', ${JSON.stringify(JSON.stringify(session))});
    'ok'
  `,
  returnByValue: true
})

await send('Page.reload', { ignoreCache: true })
await wait(2600)

const info = await send('Runtime.evaluate', {
  expression: `JSON.stringify({
    hash: location.hash,
    num: document.querySelector('.profile .nums div:nth-child(3) b')?.textContent,
    unit: document.querySelector('.profile .nums div:nth-child(3) span')?.textContent,
    tip: document.querySelector('.session-tip')?.textContent?.trim().slice(0, 120)
  })`,
  returnByValue: true
})
console.log(info.result.result.value)

const shot = await send('Page.captureScreenshot', { format: 'png' })
writeFileSync(out, Buffer.from(shot.result.data, 'base64'))
console.log('saved', out)
ws.close()
