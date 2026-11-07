/**
 * v5 验证：注入完整演示数据 → 打开个人主页 → 打印结构 + 截图 + 收集 console 错误
 * 用法：node scripts/cdp_v5_me.mjs <url> <out.png> [w] [h] [scrollTo]
 */
import { writeFileSync } from 'node:fs'

const PORT = process.env.CDP_PORT || 9337
const [, , url, out, w = '1440', h = '1000', scrollTo = ''] = process.argv
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const page = targets.find((t) => t.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const errors = []

ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    errors.push((m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ').split('\n')[0])
  }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails
    errors.push('EXC ' + ((d.exception && (d.exception.description || d.exception.value)) || d.text || '').split('\n')[0])
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
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) return 'ERR:' + r.result.exceptionDetails.text
  return r.result?.result?.value
}

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: Number(w),
  height: Number(h),
  deviceScaleFactor: 1,
  mobile: Number(w) < 700
})

const ACC = '19237463455'
const now = Date.now()
const DAY = 86400000
const HOUR = 3600000

const users = {
  [ACC]: {
    account: ACC,
    nickname: '扣山',
    salt: 'deadbeef',
    hash: 'x',
    bio: '走过 20 条海岸线，正在把华南的千米山爬完。',
    bg: 0,
    createdAt: now - 92 * DAY
  }
}
const session = {
  account: ACC,
  nickname: '扣山',
  jti: 'a1b2c3d4e5f60718',
  exp: now + 7 * DAY - 40 * 60 * 1000,
  loginAt: now - 40 * 60 * 1000,
  lastSeen: now
}
const fav = {
  [ACC]: {
    spot: ['漓江·杨堤至兴坪', '龙脊梯田', '高椅岭', '黑排角', '小东江'],
    route: ['武功山·金顶穿越', '东西冲海岸线', '船底顶·罗新线', '高椅岭丹霞环线']
  }
}
const fieldUser = {
  [ACC]: {
    walked: [46, 7, 3, 23],
    gear: [],
    lists: [],
    plans: [
      {
        id: 'p_demo',
        routeId: 46,
        days: 2,
        startDate: '2026-11-07',
        party: ['阿野', '小林'],
        emergencyName: '陈姐',
        emergencyPhone: '13900001111',
        note: '车停沈子村口，粤 A 8K2X1。',
        status: 'ongoing',
        createdAt: now - 5 * HOUR,
        checkins: [
          { at: now - 5 * HOUR, type: 'go', note: '出发报备，已登记行程' },
          { at: now - 3 * HOUR, type: 'safe', note: '到达沈子村起点，开始进山' },
          { at: now - 40 * 60 * 1000, type: 'safe', note: '已到中庵，天气多云，状态良好' }
        ]
      }
    ]
  }
}

await send('Page.navigate', { url: 'about:blank' })
await wait(200)
await send('Page.navigate', { url })
await wait(2200)

await evalv(`
  localStorage.setItem('yejing:users:v2', ${JSON.stringify(JSON.stringify(users))});
  localStorage.setItem('yejing:session:v2', ${JSON.stringify(JSON.stringify(session))});
  localStorage.setItem('yejing:fav:v2', ${JSON.stringify(JSON.stringify(fav))});
  localStorage.setItem('yejing:field:user:v1', ${JSON.stringify(JSON.stringify(fieldUser))});
  'ok'
`)
await send('Page.reload', { ignoreCache: true })
await wait(2400)

// 补两条自己的动态 + 别人的帖子下我的留言
await evalv(`(() => {
  const now = Date.now(), HOUR = 3600000, DAY = 86400000
  const key = 'yejing:social:v2'
  const raw = localStorage.getItem(key)
  const st = raw ? JSON.parse(raw) : { posts: [], buddies: [] }
  if (!st.posts) st.posts = []
  if (!st.buddies) st.buddies = []
  // 幂等：先清掉上次注入的自己的内容，再重新写一遍
  st.posts = st.posts.filter(p => p.account !== '${ACC}')
  st.buddies = (st.buddies || []).filter(b => b.account !== '${ACC}')
  st.posts.unshift({
    id: 'mine2',
    account: '${ACC}',
    author: '扣山',
    initial: '扣',
    title: '船底顶罗新线：塌方区现在要贴右壁过',
    body: '乱石坡脚往上 200 米，左侧塌方堆了两米高。重装别硬挤，先下包递过去再人过。山顶夜里 3℃，风大。',
    trailId: 1,
    trailName: '船底顶·罗新线',
    city: '韶关',
    images: ['photos/gal/gal-r01.jpg', 'photos/gal/gal-s02.jpg'],
    tags: ['高山草甸', '塌方'],
    likes: ['demo_a', 'demo_b'],
    comments: [
      { id: 'c1', account: 'demo_c', name: '老林', text: '上个月去还是通的，这么快就塌了', at: now - 5 * HOUR },
      { id: 'c2', account: '${ACC}', name: '扣山', text: '雨季之后就这样了，建议带根短绳', at: now - 4 * HOUR }
    ],
    createdAt: now - 2 * DAY
  })
  st.posts.unshift({
    id: 'mine1',
    account: '${ACC}',
    author: '扣山',
    initial: '扣',
    title: '东西冲走完第七次，把潮汐和出口记下来了',
    body: '西冲出口那段铁丝网别硬翻，往回走 300 米有正规出口。礁石段选低潮前后两小时过，鞋一湿全程难受。',
    trailId: 7,
    trailName: '东西冲海岸线',
    city: '深圳',
    images: ['photos/gal/gal-r09.jpg'],
    tags: ['海岸线', '潮汐'],
    likes: ['demo_a', 'demo_b', 'demo_e'],
    comments: [{ id: 'mc1', account: 'demo_c', name: '老林', text: '铁丝网那个我也遇到过', at: now - 1 * HOUR }],
    createdAt: now - 2 * HOUR
  })
  // 我发起的一条约伴（带两个申请）
  if (!st.buddies.some(b => b.account === '${ACC}')) {
    st.buddies.unshift({
      id: 'bmine1',
      account: '${ACC}',
      owner: '扣山',
      initial: '扣',
      destCity: '韶关',
      trailId: 1,
      trailName: '船底顶·罗新线',
      startDate: '2026-11-21',
      endDate: '2026-11-22',
      level: 3,
      budget: 380,
      genderPref: 0,
      slots: 2,
      tags: ['重装', '草甸', '日出'],
      intro: '罗新线两天，坪坑坳扎营。我走过三次，塌方段知道怎么过，收两个能背 12kg 的。',
      lat: 24.575,
      lng: 113.41,
      applicants: [
        { account: 'demo_c', name: '老林', msg: '走过联山 B 线，罗新线没走过，体力没问题', status: 0, at: now - 6 * HOUR },
        { account: 'demo_d', name: '阿岚', msg: '可以分摊帐篷和炉头', status: 1, at: now - 20 * HOUR }
      ],
      createdAt: now - 26 * HOUR
    })
  }
  // 在别人的帖子下留一条言
  const other = st.posts.find(p => p.account !== '${ACC}' && p.account !== 'me')
  if (other) {
    other.comments = (other.comments || []).filter(c => c.account !== '${ACC}')
    other.comments.push({ id: 'oc1', account: '${ACC}', name: '扣山', text: '这条线十月中去最舒服，草还没黄', at: now - 9 * HOUR })
  }
  localStorage.setItem(key, JSON.stringify(st))
  return 'ok'
})()`)

const injectRes = await evalv(`localStorage.getItem('yejing:social:v2') ? (JSON.parse(localStorage.getItem('yejing:social:v2')).posts || []).filter(p => p.account === '${ACC}').length : 'no-key'`)
console.log('INJECT_CHECK', injectRes)
await send('Page.reload', { ignoreCache: true })
await wait(2600)
console.log('AFTER_RELOAD', await evalv(`(JSON.parse(localStorage.getItem('yejing:social:v2')||'{}').posts||[]).filter(p=>p.account==='${ACC}').length`))

if (scrollTo) {
  await evalv(`document.querySelector('[data-k="${scrollTo}"]')?.scrollIntoView({block:'start'}); 'ok'`)
  await wait(900)
}

const info = await evalv(`JSON.stringify({
  hash: location.hash,
  title: document.querySelector('.who h1')?.textContent?.trim().slice(0, 20),
  tally: [...document.querySelectorAll('.cell b')].map(e => e.textContent.trim()),
  tools: [...document.querySelectorAll('.tool h3')].map(e => e.textContent.trim()),
  idx: [...document.querySelectorAll('.index nav a')].map(e => e.textContent.replace(/\\s+/g,' ').trim()),
  active: document.querySelector('.index nav a.on')?.textContent?.replace(/\\s+/g,' ').trim(),
  blocks: [...document.querySelectorAll('.block')].map(b => ({
    no: b.querySelector('.b-no')?.textContent,
    h: b.querySelector('h2')?.textContent,
    items: b.querySelectorAll('.line li').length + b.querySelectorAll('.card-route').length + b.querySelectorAll('.post').length + b.querySelectorAll('.wall-item').length + b.querySelectorAll('.tile').length
  })),
  photos: document.querySelectorAll('.wall-item').length,
  timeline: document.querySelectorAll('.line li').length,
  scrollH: document.body.scrollHeight
})`)
console.log(info)

const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
writeFileSync(out, Buffer.from(shot.result.data, 'base64'))
console.log('saved', out)
console.log('CONSOLE_ERRORS', JSON.stringify(errors))
ws.close()
