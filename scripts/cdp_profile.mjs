/**
 * 注入完整演示数据后截个人主页。
 * 用法：node scripts/cdp_profile.mjs <url> <out> [w] [h]
 */
import { writeFileSync } from 'node:fs'

const PORT = process.env.CDP_PORT || 9337
const [, , url, out, w = '1440', h = '1100'] = process.argv
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = targets.find((t) => t.type === 'page')
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
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const send = (method, params = {}) =>
  new Promise((res) => {
    const n = ++id
    pending.set(n, res)
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

const ACC = '19237463455'
const users = {
  [ACC]: {
    account: ACC,
    nickname: '扣山',
    salt: 'deadbeef',
    hash: 'x',
    bio: '走过 20 条海岸线，正在把华南的千米山爬完。',
    bg: 0,
    createdAt: Date.now() - 92 * 86400000
  }
}
const session = {
  account: ACC,
  nickname: '扣山',
  jti: 'a1b2c3d4e5f60718',
  exp: Date.now() + 7 * 24 * 3600 * 1000 - 40 * 60 * 1000,
  loginAt: Date.now() - 40 * 60 * 1000,
  lastSeen: Date.now()
}
const fav = {
  [ACC]: {
    spot: ['漓江·杨堤至兴坪', '龙脊梯田', '岳麓山', '东西冲'],
    route: ['武功山·金顶穿越', '漓江·杨堤至兴坪', '东西冲海岸线']
  }
}

const inject = `
  localStorage.setItem('yejing:users:v2', ${JSON.stringify(JSON.stringify(users))});
  localStorage.setItem('yejing:session:v2', ${JSON.stringify(JSON.stringify(session))});
  localStorage.setItem('yejing:fav:v2', ${JSON.stringify(JSON.stringify(fav))});
  'ok'
`
await send('Runtime.evaluate', { expression: inject, returnByValue: true })
await send('Page.reload', { ignoreCache: true })
await wait(2800)

// 发一条自己的动态，让「我的动态」有内容
await send('Runtime.evaluate', {
  expression: `(() => {
    const key = 'yejing:social:v2'
    const raw = localStorage.getItem(key)
    if (!raw) return 'no social'
    const st = JSON.parse(raw)
    if (st.posts.some(p => p.account === '${ACC}')) return 'already'
    st.posts.unshift({
      id: 'mine1',
      account: '${ACC}',
      author: '扣山',
      initial: '扣',
      title: '东西冲走完第七次，把潮汐和出口记下来了',
      body: '西冲出口那段铁丝网别硬翻，往回走 300 米有正规出口。礁石段选低潮前后两小时过，鞋一湿全程难受。',
      trailId: 3,
      trailName: '东西冲海岸线',
      city: '深圳',
      images: ['photos/gal/gal-r09.jpg'],
      tags: ['海岸线', '潮汐'],
      likes: ['demo_a', 'demo_b', 'demo_e'],
      comments: [{ id: 'mc1', account: 'demo_c', name: '老林', text: '铁丝网那个我也遇到过', at: Date.now() - 3600000 }],
      createdAt: Date.now() - 7200000
    })
    localStorage.setItem(key, JSON.stringify(st))
    return 'ok'
  })()`,
  returnByValue: true
})
await send('Page.reload', { ignoreCache: true })
await wait(2600)

const info = await send('Runtime.evaluate', {
  expression: `JSON.stringify({
    hash: location.hash,
    name: document.querySelector('.hero-inner h1')?.textContent,
    bio: document.querySelector('.hero-bio')?.textContent?.slice(0, 20),
    nums: [...document.querySelectorAll('.hero-nums b')].map(e => e.textContent),
    tabs: [...document.querySelectorAll('.ptabs button')].map(e => e.textContent.trim()),
    level: document.querySelector('.lv')?.textContent
  })`,
  returnByValue: true
})
console.log(info.result.result.value)

const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
writeFileSync(out, Buffer.from(shot.result.data, 'base64'))
console.log('saved', out)
ws.close()
