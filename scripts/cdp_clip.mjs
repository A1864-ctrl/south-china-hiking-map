/** 截取页面指定区域的清晰截图：node scripts/cdp_clip.mjs <url> <out.png> <y> <h> [w] */
import { writeFileSync } from 'node:fs'

const PORT = process.env.CDP_PORT || 9337
const [, , url, out, y = '0', h = '900', w = '1440', scrollTo = ''] = process.argv
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = targets.find((t) => t.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const errs = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.method === 'Runtime.exceptionThrown') errs.push(m.params.exceptionDetails.text)
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

await send('Page.enable')
await send('Emulation.setDeviceMetricsOverride', { width: Number(w), height: 900, deviceScaleFactor: 1, mobile: false })
await send('Page.navigate', { url })
await wait(2600)
if (scrollTo !== '') {
  await send('Runtime.evaluate', { expression: `window.scrollTo(0, ${Number(scrollTo)})` })
  await wait(1200)
}
const shot = await send('Page.captureScreenshot', {
  format: 'png',
  captureBeyondViewport: true,
  clip: { x: 0, y: Number(y), width: Number(w), height: Number(h), scale: 1 }
})
writeFileSync(out, Buffer.from(shot.result.data, 'base64'))
console.log('saved', out, 'errors', errs.length)
ws.close()
