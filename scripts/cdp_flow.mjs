/**
 * 用 CDP 跑一遍「注册 → 收藏 → 刷新仍登录」的真实流程。
 * 用法：node scripts/cdp_flow.mjs <baseUrl>
 */
const PORT = process.env.CDP_PORT || 9335
const base = process.argv[2] || 'http://127.0.0.1:5196'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
  const page = list.find((t) => t.type === 'page')
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  const logs = []

  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
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

  const js = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.result?.exceptionDetails) return { error: r.result.exceptionDetails.text }
    return r.result?.result?.value
  }

  await send('Page.enable')
  await send('Runtime.enable')
  await send('Network.enable')
  await send('Network.setCacheDisabled', { cacheDisabled: true })

  await send('Page.navigate', { url: 'about:blank' })
  await wait(300)
  await send('Page.navigate', { url: `${base}/#/route/1` })
  await wait(2200)
  await js(`localStorage.clear()`)
  await send('Page.reload', { ignoreCache: true })
  await wait(2400)

  console.log('① 初始登录态:', await js(`JSON.stringify({loginBtn: !!document.querySelector('.login'), me: !!document.querySelector('.me')})`))

  // 打开登录弹窗
  await js(`document.querySelector('.login').click()`)
  await wait(500)
  console.log('② 弹窗打开:', await js(`!!document.querySelector('[role=dialog]')`))

  // 切到注册
  await js(`document.querySelectorAll('[role=dialog] .tabs button')[1].click()`)
  await wait(300)

  // 填表：昵称 / 账号 / 密码 / 确认
  await js(`(() => {
    const inputs = [...document.querySelectorAll('[role=dialog] input')]
    const vals = ['山野阿野', '13800001234', 'hike2026', 'hike2026']
    inputs.forEach((el, i) => {
      el.value = vals[i] || ''
      el.dispatchEvent(new Event('input', { bubbles: true }))
    })
    return inputs.length
  })()`)
  await wait(200)
  await js(`document.querySelector('[role=dialog] form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))`)
  await wait(900)

  console.log('③ 注册后:', await js(`JSON.stringify({
    dialog: !!document.querySelector('[role=dialog]'),
    me: document.querySelector('.me-name')?.textContent || '',
    session: JSON.parse(localStorage.getItem('yejing:session:v2') || 'null')?.account || '',
    toast: document.querySelector('.toast')?.textContent || ''
  })`))

  // 收藏当前路线
  await js(`document.querySelector('.fav')?.click()`)
  await wait(600)
  console.log('④ 收藏后:', await js(`JSON.stringify({
    favText: document.querySelector('.fav')?.textContent.trim(),
    badge: document.querySelector('.fav-badge')?.textContent || '',
    store: JSON.parse(localStorage.getItem('yejing:fav:v2') || '{}')
  })`))

  // 刷新后是否仍登录、仍收藏（真刷新，不是同址导航）
  await send('Page.reload', { ignoreCache: true })
  await wait(2400)
  console.log('⑤ 刷新后:', await js(`JSON.stringify({
    me: document.querySelector('.me-name')?.textContent || '',
    favText: document.querySelector('.fav')?.textContent.trim(),
    badge: document.querySelector('.fav-badge')?.textContent || ''
  })`))

  // 我的收藏页
  await send('Page.navigate', { url: `${base}/#/me` })
  await wait(2200)
  await js(`document.querySelectorAll('.tabs button')[1]?.click()`)
  await wait(400)
  console.log('⑥ 我的页:', await js(`JSON.stringify({
    name: document.querySelector('.who h1')?.textContent || '',
    rows: document.querySelectorAll('.row').length,
    title: document.querySelector('.row h3')?.textContent || ''
  })`))

  // 版本页
  await send('Page.navigate', { url: `${base}/#/versions` })
  await wait(2000)
  console.log('⑦ 版本页:', await js(`JSON.stringify({
    cards: document.querySelectorAll('.vcard').length,
    rows: document.querySelectorAll('.diff-row').length
  })`))

  console.log('控制台异常:', [...new Set(logs)].slice(0, 4))
  ws.close()
  process.exit(0)
}

main().catch((e) => {
  console.error('ERR', e.message)
  process.exit(1)
})
