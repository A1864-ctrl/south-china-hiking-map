/**
 * v5 交互回归：路况提交→审核→挂载、平安打卡、装备库、目录跳转、灯箱、编辑资料
 * 用法：node scripts/cdp_v5_flow.mjs <base>
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
  if (m.method === 'Runtime.exceptionThrown') {
    errs.push((m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text || '').split('\n')[0])
  }
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
const ev = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) return 'ERR ' + (r.result.exceptionDetails.exception?.description || '').split('\n')[0]
  return r.result?.result?.value
}
const go = async (hash, ms = 2200) => {
  await send('Page.navigate', { url: `${base}/#/${hash}` })
  await wait(ms)
}
const click = async (sel) => {
  const r = await ev(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return 'no-el'; el.click(); return 'ok' })()`)
  await wait(700)
  return r
}
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`)
}

/* ── 1. 路况上报：提交 → 待审核 → 通过 → 挂到路线 ── */
await go('reports')
const before = await ev(`document.querySelectorAll('.report').length`)
await ev(`(() => {
  const sel = document.querySelector('.form select')
  sel.value = sel.options[1].value
  sel.dispatchEvent(new Event('change', { bubbles: true }))
  return 'ok'
})()`)
await wait(400)
await click('.form .type:nth-child(3)')
await ev(`(() => {
  const ta = document.querySelector('.form textarea')
  ta.value = '测试上报：岩壁下方有蜂群，上午活动频繁，建议快速通过不要停留。'
  ta.dispatchEvent(new Event('input', { bubbles: true }))
  return 'ok'
})()`)
await wait(300)
await click('.form .submit')
const pendingAfter = await ev(`document.querySelectorAll('.report.pending').length`)
check('路况提交后进入待审核', pendingAfter > 0, `pending=${pendingAfter}`)

await ev(`(() => {
  const rows = [...document.querySelectorAll('.report')]
  const row = rows.find(r => r.querySelector('.r-note')?.textContent.includes('测试上报'))
  if (!row) return 'no-row'
  const b = row.querySelector('.audit .mini.ok')
  if (!b) return 'no-btn'
  b.click()
  return 'ok'
})()`)
await wait(600)
const approvedText = await ev(`document.querySelector('.list-head .filters button.on')?.textContent || ''`)
await click('.list-head .filters button:first-child')
const hasNew = await ev(`[...document.querySelectorAll('.report .r-note')].some(e => e.textContent.includes('测试上报'))`)
check('审核通过后进入已挂载列表', hasNew, approvedText.trim())

const importedRouteId = await ev(`(() => {
  const st = JSON.parse(localStorage.getItem('yejing:field:reports:v1') || '[]')
  const r = st.find(x => x.note && x.note.includes('测试上报'))
  return r ? r.routeId : 0
})()`)
check('记录了路线 id', !!importedRouteId, `routeId=${importedRouteId}`)

await go(`route/${importedRouteId}?tab=live`)
const onRoute = await ev(`[...document.querySelectorAll('.r-n')].some(e => e.textContent.includes('测试上报'))`)
check('路况已挂到对应路线详情', onRoute)

/* ── 2. 安全报备：一键打卡 + 结束 ── */
await go('safety')
const ckBefore = await ev(`document.querySelectorAll('.timeline li').length`)
await click('.q-btns button:nth-child(2)')
const ckAfter = await ev(`document.querySelectorAll('.timeline li').length`)
check('平安打卡新增一条记录', ckAfter === ckBefore + 1, `${ckBefore} → ${ckAfter}`)

await click('.p-acts .btn.primary')
const planGone = await ev(`!document.querySelector('.p-head')`)
check('下山后报备关闭', planGone)

/* ── 3. 装备库：勾选 + 保存清单 ── */
await go('gear-lab')
const w0 = await ev(`document.querySelector('.stats div:nth-child(3) b')?.textContent`)
await ev(`(() => { const t = document.querySelectorAll('.gear .tick')[0]; t.click(); return 'ok' })()`)
await wait(500)
const w1 = await ev(`document.querySelector('.stats div:nth-child(3) b')?.textContent`)
check('勾选装备后总重变化', w0 !== w1, `${w0} → ${w1}`)

await click('.gear-lab-save, .save .primary')
const savedCount = await ev(`document.querySelectorAll('.s-row').length`)
check('保存清单成功', savedCount > 0, `saved=${savedCount}`)

/* ── 4. 个人主页：目录跳转 + 灯箱 ── */
await go('me')
await ev(`window.scrollTo(0, 0)`)
await wait(300)
const y0 = await ev(`window.scrollY`)
await click('.index nav a:nth-child(5)')
await wait(900)
const y1 = await ev(`window.scrollY`)
const act = await ev(`document.querySelector('.index nav a.on span')?.textContent`)
check('点目录跳转到照片墙', y1 > y0 + 200, `scrollY ${Math.round(y0)} → ${Math.round(y1)}, active=${act}`)

await click('.wall-item')
const lbOpen = await ev(`!!document.querySelector('.lb')`)
check('照片墙点开大图', lbOpen)
await ev(`document.querySelector('.lb .x')?.click()`)
await wait(500)

/* 编辑资料 */
await click('.who-acts button')
const dlg = await ev(`!!document.querySelector('.dlg')`)
check('打开编辑资料弹层', dlg)
await ev(`(() => {
  const i = document.querySelectorAll('.dlg input')[1]
  i.value = '正在把华南的千米山一座座走完。'
  i.dispatchEvent(new Event('input', { bubbles: true }))
  return 'ok'
})()`)
await click('.dlg-acts .primary')
const bio = await ev(`document.querySelector('.bio')?.textContent`)
check('签名保存后立即生效', (bio || '').includes('千米山'), bio)

/* 约伴：同意申请 */
const applyOk = await ev(`(() => {
  const b = document.querySelector('.apply .mini.ok')
  if (!b) return 'none'
  b.click()
  return 'clicked'
})()`)
await wait(600)
const passed = await ev(`document.querySelectorAll('.apply em.passed').length`)
check('同意约伴申请', applyOk === 'clicked' && passed > 0, `passed=${passed}`)

console.log('EXCEPTIONS', JSON.stringify(errs))
console.log('SUMMARY', results.filter((r) => r.ok).length + '/' + results.length)
ws.close()
