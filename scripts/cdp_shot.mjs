/**
 * 用 CDP 截当前（含登录态）页面：node scripts/cdp_shot.mjs <url> <out.jpg> [width] [height]
 */
import { writeFileSync } from 'node:fs'

const PORT = process.env.CDP_PORT || 9335
const [url, out, w = '1440', h = '900'] = process.argv.slice(2)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
  const page = list.find((t) => t.type === 'page')
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (m.id && pending.has(m.id)) {
      pending.get(m.id)(m)
      pending.delete(m.id)
    }
  })
  await new Promise((r) => ws.addEventListener('open', r))
  const send = (method, params = {}) =>
    new Promise((resolve) => {
      const mid = ++id
      pending.set(mid, resolve)
      ws.send(JSON.stringify({ id: mid, method, params }))
    })

  await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', {
    width: Number(w), height: Number(h), deviceScaleFactor: 1, mobile: false
  })
  await send('Page.navigate', { url: 'about:blank' })
  await wait(300)
  await send('Page.navigate', { url })
  await wait(2600)
  const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 86 })
  writeFileSync(out, Buffer.from(shot.result.data, 'base64'))
  console.log('saved', out)
  ws.close()
  process.exit(0)
}

main().catch((e) => {
  console.error('ERR', e.message)
  process.exit(1)
})
