const PORT = process.env.CDP_PORT || 9336
const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = targets.find((t) => t.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pend = new Map()
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m)
    pend.delete(m.id)
  }
})
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const send = (method, params = {}) =>
  new Promise((res) => {
    const n = ++id
    pend.set(n, res)
    ws.send(JSON.stringify({ id: n, method, params }))
  })
await send('Runtime.enable')
const r = await send('Runtime.evaluate', {
  expression: `(() => {
    const c = document.querySelector('.cta')
    const inner = document.querySelector('.inner')
    const tabs = document.querySelector('.tabs')
    const side = document.querySelector('.side')
    const box = (el) => el ? { x: Math.round(el.getBoundingClientRect().x), w: Math.round(el.getBoundingClientRect().width) } : null
    return JSON.stringify({
      innerW: inner ? Math.round(inner.getBoundingClientRect().width) : null,
      tabs: box(tabs),
      side: box(side),
      cta: box(c),
      ctaDisplay: c ? getComputedStyle(c).display : 'absent',
      viewport: innerWidth
    })
  })()`,
  returnByValue: true
})
console.log(r.result.result.value)
ws.close()
