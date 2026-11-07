/**
 * 逐页加载，收集 console.error / 未捕获异常，用来查「模板引用了不存在的函数」这类静默失败。
 * 用法：node scripts/cdp_console.mjs <url1> <url2> ...
 */
const PORT = process.env.CDP_PORT || 9333
const urls = process.argv.slice(2)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
  const page = list.find((t) => t.type === 'page')
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  let logs = []

  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      logs.push((m.params.args || []).map((a) => a.value || a.description || '').join(' ').split('\n')[0])
    }
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails
      logs.push('EXC ' + ((d.exception && (d.exception.description || d.exception.value)) || d.text || '').split('\n')[0])
    }
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
  await send('Runtime.enable')
  await send('Network.enable')
  await send('Network.setCacheDisabled', { cacheDisabled: true })

  for (const url of urls) {
    logs = []
    await send('Page.navigate', { url: 'about:blank' })
    await wait(300)
    await send('Page.navigate', { url })
    await wait(2200)
    const ok = await send('Runtime.evaluate', {
      expression: "JSON.stringify({hash: location.hash, cards: document.querySelectorAll('.card').length})",
      returnByValue: true
    })
    const uniq = [...new Set(logs)].slice(0, 3)
    console.log(`${url}\n  ${ok.result.result.value}  errors=${uniq.length}${uniq.length ? '\n  ' + uniq.join('\n  ') : ''}`)
  }
  ws.close()
  process.exit(0)
}

main().catch((e) => {
  console.error('ERR', e.message)
  process.exit(1)
})
