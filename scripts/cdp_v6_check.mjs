/**
 * 回归：营地库 → 路线详情 → 返回；路线科普；知识库第三类
 * 用法：node scripts/cdp_v6_check.mjs <base>
 */
const PORT = process.env.CDP_PORT || 9337
const base = process.argv[2] || 'http://127.0.0.1:5178'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = targets.find((t) => t.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const errs = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.method === 'Runtime.exceptionThrown')
    errs.push((m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text || '').split('\n')[0])
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
const ev = async (x) => {
  const r = await send('Runtime.evaluate', { expression: x, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) return 'ERR ' + (r.result.exceptionDetails.exception?.description || '').split('\n')[0]
  return r.result?.result?.value
}
// base 带 ?sharecode=... 时不能再拼斜杠，否则 sharecode 会被吞掉
const urlOf = (h) => (base.includes('?') ? `${base}#/${h}` : `${base}/#/${h}`)
const go = async (h, ms = 2200) => {
  await send('Page.navigate', { url: urlOf(h) })
  await wait(ms)
}
const click = async (sel) => {
  const r = await ev(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return 'no-el'; el.click(); return 'ok' })()`)
  await wait(900)
  return r
}
const dblclick = async (sel) => {
  const r = await ev(`(() => {
    const el = document.querySelector(${JSON.stringify(sel)})
    if (!el) return 'no-el'
    el.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, detail: 2 }))
    el.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }))
    return 'ok'
  })()`)
  await wait(1100)
  return r
}
const results = []
const check = (n, ok, d = '') => {
  results.push(ok)
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`)
}

/* ── 1. 营地库 → 路线详情 → 返回营地库 ── */
await go('camps')
await dblclick('.camp figure')
const hash1 = await ev(`location.hash`)
const label1 = await ev(`document.querySelector('.back')?.textContent.trim()`)
check('双击营地图片跳转到路线详情', hash1.includes('/route/'), hash1)
check('返回按钮文案跟随来源', label1 === '返回营地库', label1)

await click('.back')
await wait(800)
const hash2 = await ev(`location.hash`)
check('点返回回到营地库（双击只入栈一次）', hash2.startsWith('#/camps'), hash2)

/* 再来一次，改用浏览器后退验证历史栈 */
await dblclick('.camp figure')
await wait(600)
await ev(`history.back()`)
await wait(800)
const hash3 = await ev(`location.hash`)
check('浏览器后退也能回到营地库', hash3.startsWith('#/camps'), hash3)

/* ── 2. 从路线列表进入，返回应回到列表 ── */
await go('routes')
await wait(900)
await dblclick('.card')
const hash4 = await ev(`location.hash`)
const label4 = await ev(`document.querySelector('.back')?.textContent.trim()`)
if (hash4.includes('/route/')) {
  check('从路线列表进入时返回文案正确', label4 === '返回路线列表', label4)
  await click('.back')
  await wait(700)
  check('返回回到路线列表（保留地址）', (await ev(`location.hash`)).startsWith('#/routes'), await ev(`location.hash`))
} else {
  console.log('SKIP  列表卡片选择器未命中', hash4)
}

/* ── 3. 路线科普 ── */
await go('route/1?tab=eco')
const eco = await ev(`JSON.stringify({
  facts: [...document.querySelectorAll('.eco .facts b')].map(e=>e.textContent.trim()),
  blocks: [...document.querySelectorAll('.eco .card-block h3')].map(e=>e.textContent.replace(/\\s+/g,'').trim()),
  animals: document.querySelectorAll('.eco .animal').length,
  cautions: document.querySelectorAll('.eco .cautions li').length,
  bands: document.querySelectorAll('.eco .band').length,
  fact: document.querySelector('.eco .fact')?.textContent.slice(0, 20)
})`)
check('科普四块内容齐全', /地形地势/.test(eco) && /植被分布/.test(eco) && /动物种类/.test(eco) && /需要注意/.test(eco), eco)

const eco2 = await ev(`JSON.stringify([...document.querySelectorAll('.eco .facts b')].map(e=>e.textContent.trim()))`)
const facts2 = JSON.parse(eco2)
check('区域与地貌四项都有值', facts2.length === 4 && facts2.every((x) => x && x !== '—'), eco2)

/* 换一条不同区域的线，确认内容不同 */
await go('route/53?tab=eco')
const eco3 = await ev(`JSON.stringify({
  facts: [...document.querySelectorAll('.eco .facts b')].map(e=>e.textContent.trim()),
  animals: [...document.querySelectorAll('.eco .animal b')].map(e=>e.textContent.trim())
})`)
check('不同路线内容不同', eco3 !== eco2, eco3.slice(0, 120))

/* ── 4. 知识库第三类 ── */
await go('learn?cat=eco')
const learn = await ev(`JSON.stringify({
  cats: [...document.querySelectorAll('.cat b')].map(e=>e.textContent.trim()),
  routes: document.querySelectorAll('.toc-item').length,
  doc: !!document.querySelector('.eco'),
  title: document.querySelector('.doc-head h2')?.textContent.trim()
})`)
check('知识库出现路线科普分类', /路线科普/.test(learn), learn)

await ev(`(() => { const i = document.querySelector('.toc-search'); i.value='海岸'; i.dispatchEvent(new Event('input',{bubbles:true})); return 'ok' })()`)
await wait(600)
const filtered = await ev(`document.querySelectorAll('.toc-item').length`)
check('科普列表可搜索', filtered > 0 && filtered < 53, `搜「海岸」得 ${filtered} 条`)

console.log('EXCEPTIONS', JSON.stringify(errs))
console.log('SUMMARY', results.filter(Boolean).length + '/' + results.length)
ws.close()
