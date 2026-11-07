/**
 * README 宣传照：主站 6 个页面，JPEG 质量 78。
 * 用法：node scripts/readme_shots.mjs
 */
import { mkdirSync, writeFileSync } from 'node:fs'

const BASE = 'https://south-china-hiking.app.workbuddy.host/?sharecode=NXC6GS3IF3'
const PORT = 9337
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync('docs/screenshots', { recursive: true })

const tabs = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = tabs.find((x) => x.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
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
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true })
  return r.result?.result?.value
}

await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 860, deviceScaleFactor: 1, mobile: false })

const SHOTS = [
  { hash: '', file: 'home.jpg', label: '首页', settle: 5200 },
  { hash: 'spots', file: 'spots.jpg', label: '景点路书', settle: 4200 },
  { hash: 'route/46', file: 'route.jpg', label: '路线详情', settle: 5200 },
  { hash: 'community', file: 'community.jpg', label: '山友社区', settle: 4500 },
  { hash: 'weather', file: 'weather.jpg', label: '点位天气', settle: 5200 },
  { hash: 'camps', file: 'camps.jpg', label: '营地库', settle: 4200 }
]

for (const s of SHOTS) {
  const url = BASE + (s.hash ? `#/${s.hash}` : '')
  await send('Page.navigate', { url })
  await wait(s.settle)
  // 触发懒加载：快速滚一遍再回顶
  await ev(`window.scrollTo(0, 99999)`)
  await wait(900)
  await ev(`window.scrollTo(0, 0)`)
  await wait(700)
  const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 78 })
  writeFileSync(`docs/screenshots/${s.file}`, Buffer.from(shot.result.data, 'base64'))
  console.log('OK', s.label, '→', `docs/screenshots/${s.file}`)
}
ws.close()
console.log('全部完成')
