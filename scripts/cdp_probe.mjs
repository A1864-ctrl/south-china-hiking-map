/**
 * 用 Chrome DevTools Protocol 做真实鼠标双击验证（headless 下也能拿到真实事件序列）。
 *
 * 用法：
 *   1) 先起一个带调试端口的 Chrome：
 *      chrome --headless=new --remote-debugging-port=9333 --no-sandbox about:blank
 *   2) node scripts/cdp_probe.mjs <url> <selector>
 *      例：node scripts/cdp_probe.mjs "http://127.0.0.1:5190/#/routes" ".grid article:nth-child(2) .cover"
 *
 * 输出：双击后 500ms 的 hash、灯箱是否打开、导航结果。
 */
const PORT = process.env.CDP_PORT || 9333
const url = process.argv[2]
const selector = process.argv[3]
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
  const page = list.find((t) => t.type === 'page')
  if (!page) throw new Error('no page target')

  const logs = []
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.method === 'Runtime.consoleAPICalled') {
      const args = (msg.params.args || []).map((a) => a.value || a.description || a.type).join(' ')
      logs.push('[console.' + msg.params.type + '] ' + args)
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails
      logs.push('[exception] ' + (d.exception && (d.exception.description || d.exception.value) || d.text))
    }
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg)
      pending.delete(msg.id)
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
  await send('Runtime.enable')
  await send('Network.enable')
  await send('Network.setCacheDisabled', { cacheDisabled: true })
  await send('Page.navigate', { url: 'about:blank' })
  await wait(400)
  await send('Page.navigate', { url })
  await wait(2600)
  const pre = await send('Runtime.evaluate', {
    expression: "JSON.stringify({lb: !!document.querySelector('.lb'), hash: location.hash, h: innerHeight, w: innerWidth})",
    returnByValue: true
  })
  console.log('pre=' + pre.result.result.value)

  await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector(${JSON.stringify(selector)})
      if (el) el.scrollIntoView({ block: 'center' })
    })()`
  })
  await wait(350)

  const rect = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector(${JSON.stringify(selector)})
      if (!el) return null
      const r = el.getBoundingClientRect()
      const cx = r.x + r.width / 2, cy = r.y + r.height / 2
      const hit = document.elementFromPoint(cx, cy)
      return { x: cx, y: cy, w: r.width, h: r.height,
               hit: hit ? (hit.className || hit.tagName) : 'none',
               top: Math.round(r.top) }
    })()`,
    returnByValue: true
  })
  const box = rect.result.result.value
  if (!box) {
    console.log('NOT_FOUND', selector)
    process.exit(1)
  }

  if (process.argv[4] === 'hover') {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y })
    await wait(400)
    const hint = await send('Runtime.evaluate', {
      expression: `(() => {
        const e = document.querySelector('.hero-zoom, .zoom-hint')
        return e ? getComputedStyle(e).opacity : 'none'
      })()`,
      returnByValue: true
    })
    console.log('hintOpacity(hover)=' + hint.result.result.value)
  }

  // 真实双击：press/release(clickCount=1) + press/release(clickCount=2)
  for (const clickCount of [1, 2]) {
    await send('Input.dispatchMouseEvent', {
      type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount
    })
    await send('Input.dispatchMouseEvent', {
      type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount
    })
  }
  await wait(800)

  const out = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      hash: location.hash,
      lightbox: !!document.querySelector('.lb'),
      lbCount: (document.querySelector('.lb-count')||{}).textContent || '',
      detail: !!document.querySelector('.hero-inner h1') || !!document.querySelector('.d-title')
    })`,
    returnByValue: true
  })
  console.log('rect=' + JSON.stringify(box))
  console.log(out.result.result.value)
  if (logs.length) console.log(logs.slice(-6).join('\n'))
  ws.close()
  process.exit(0)
}

main().catch((e) => {
  console.error('ERR', e.message)
  process.exit(1)
})
