/**
 * 山野工具数据层：路况上报 / 安全报备 / 装备库 / 走过的路线 / 照片墙
 * ─ 路况是「社区数据」：云端 trail_reports，公开读，登录后可写；他人「确认」即视为审核通过
 * ─ 报备 / 装备库 / 清单 / 走过的路线 / 照片是「个人数据」：登录后云端按账号隔离
 * ─ 游客沿用本机 localStorage；登录后一次性把本机数据迁到云端
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth.js'
import { cloud } from '../services/cloud.js'
import { routes } from '../data/routes.js'

const REPORTS_KEY = 'yejing:field:reports:v1'
const USER_KEY = 'yejing:field:user:v1'
const WALL_KEY = 'yejing:wall:v1'
const MIGRATED_KEY = 'yejing:field:migrated'
export const WALL_LIMIT = 12
const HOUR = 3600000
const DAY = 86400000

export const REPORT_TYPES = [
  { k: 'slide', name: '塌方', icon: '⛰', tone: '#a9462f', tip: '土石堆积、路基冲毁、需绕行' },
  { k: 'weed', name: '杂草', icon: '🌿', tone: '#4a7c59', tip: '路径被草覆盖、岔口难辨' },
  { k: 'water', name: '水源干涸', icon: '💧', tone: '#2f6f9e', tip: '溪流断流、原水点不可用' },
  { k: 'bee', name: '蜂群', icon: '🐝', tone: '#a97a17', tip: '岩壁 / 树洞有蜂巢活动' },
  { k: 'closed', name: '封路', icon: '⛔', tone: '#6b7280', tip: '景区封闭、施工禁行' },
  { k: 'animal', name: '野兽', icon: '🐗', tone: '#6b5b3e', tip: '野猪、蛇类频繁出没' }
]

export const REPORT_LEVEL = [
  { v: 1, name: '提示', tone: '#4a7c59' },
  { v: 2, name: '影响通行', tone: '#a97a17' },
  { v: 3, name: '禁止通行', tone: '#a9462f' }
]

export const GEAR_CATS = [
  { k: 'pack', name: '背负', tone: '#2d5a3d' },
  { k: 'sleep', name: '睡眠', tone: '#4a5a7a' },
  { k: 'wear', name: '穿着', tone: '#8a6d2f' },
  { k: 'cook', name: '炊具', tone: '#a9462f' },
  { k: 'safe', name: '安全', tone: '#c0392b' },
  { k: 'other', name: '其他', tone: '#6b7280' }
]

const SEED_GEAR = [
  { name: '格里高利 38L 背包', cat: 'pack', weight: 1250, count: 1 },
  { name: '三季双人帐', cat: 'sleep', weight: 2100, count: 1 },
  { name: '羽绒睡袋 -5℃', cat: 'sleep', weight: 980, count: 1 },
  { name: '充气睡垫', cat: 'sleep', weight: 480, count: 1 },
  { name: '硬壳冲锋衣', cat: 'wear', weight: 420, count: 1 },
  { name: '抓绒中层', cat: 'wear', weight: 380, count: 1 },
  { name: '速干裤', cat: 'wear', weight: 260, count: 2 },
  { name: '越野跑鞋', cat: 'wear', weight: 620, count: 1 },
  { name: '炉头 + 气罐', cat: 'cook', weight: 380, count: 1 },
  { name: '钛锅 750ml', cat: 'cook', weight: 160, count: 1 },
  { name: '头灯 + 备用电池', cat: 'safe', weight: 130, count: 1 },
  { name: '急救包', cat: 'safe', weight: 310, count: 1 },
  { name: '登山杖', cat: 'other', weight: 480, count: 2 },
  { name: '1.5L 水袋', cat: 'other', weight: 120, count: 1 }
]

function readJSON(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || 'null') ?? fallback
  } catch {
    return fallback
  }
}
function writeJSON(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val))
  } catch {
    /* ignore */
  }
}

const routeById = Object.fromEntries(routes.map((r) => [r.id, r]))
export function routeNameOf(id) {
  return routeById[id] ? routeById[id].name : '未知路线'
}
export function routeOf(id) {
  return routeById[id] || null
}

const now = () => Date.now()
const toMs = (ts) => {
  const t = new Date(ts).getTime()
  return Number.isFinite(t) ? t : now()
}

function seedReports() {
  const t = now()
  return [
    { id: 'r1', routeId: 1, type: 'slide', level: 3, note: '乱石坡脚往上 200 米，左侧塌方堆了 2 米高，要贴着右侧岩壁过，重装很危险。', by: '山野阿野', at: t - 6 * HOUR, status: 'approved', confirm: 7 },
    { id: 'r2', routeId: 6, type: 'water', level: 2, note: '高洋尾沙滩后的溪流已断流，最后一个补水点在平海古城，全程要背 3L。', by: '海风', at: t - 20 * HOUR, status: 'approved', confirm: 12 },
    { id: 'r3', routeId: 7, type: 'bee', level: 2, note: '穿鼻岩下方岩壁有一窝胡蜂，上午 10 点最活跃，队伍快速通过别停留。', by: '走海岸的人', at: t - 2 * DAY, status: 'approved', confirm: 9 },
    { id: 'r4', routeId: 46, type: 'weed', level: 1, note: '发云界到金顶这段草长得比人高，路迹不明显，跟着丝带走。', by: '阿野', at: t - 3 * DAY, status: 'approved', confirm: 15 },
    { id: 'r5', routeId: 34, type: 'water', level: 3, note: '千家洞溪流干涸，D1 营地无水源，必须从月岩林场背足 4L。', by: '湘南老驴', at: t - 4 * DAY, status: 'approved', confirm: 5 },
    { id: 'r6', routeId: 51, type: 'slide', level: 2, note: '药王庙往上石海段有小落石，中午化冻时最频繁，戴头盔快速通过。', by: '太白', at: t - 5 * DAY, status: 'approved', confirm: 3 },
    { id: 'r7', routeId: 23, type: 'animal', level: 1, note: '桃花岭后山有野猪带崽，傍晚别走那段机耕道。', by: '长沙山友', at: t - 7 * DAY, status: 'approved', confirm: 4 },
    { id: 'r8', routeId: 53, type: 'closed', level: 3, note: '南宗垭口至雨崩段 8 月起分段施工，需按现场指引绕行，预留 1 小时。', by: '梅里', at: t - 9 * DAY, status: 'approved', confirm: 6 },
    { id: 'r9', routeId: 18, type: 'weed', level: 1, note: '林道尽头之后草深过膝，建议长裤 + 绑腿。', by: '连州阿强', at: t - 30 * HOUR, status: 'pending', confirm: 0 }
  ]
}

export const useFieldStore = defineStore('field', () => {
  const auth = useAuthStore()

  const reports = ref(readJSON(REPORTS_KEY, null) || seedReports())
  const allUser = ref(readJSON(USER_KEY, {}) || {})
  const allWall = ref(readJSON(WALL_KEY, {}) || {})
  const loaded = ref(false)
  const photosSigned = ref({}) // storage_path -> signedUrl

  function persistReports() {
    writeJSON(REPORTS_KEY, reports.value)
  }
  function persistUser() {
    writeJSON(USER_KEY, allUser.value)
  }
  function persistWall() {
    writeJSON(WALL_KEY, allWall.value)
  }

  /* ── 本机桶（游客） ── */
  function bucket() {
    const acc = auth.account || '__guest'
    if (!allUser.value[acc]) allUser.value[acc] = { plans: [], gear: [], lists: [], walked: [] }
    const b = allUser.value[acc]
    if (!b.plans) b.plans = []
    if (!b.gear) b.gear = []
    if (!b.lists) b.lists = []
    if (!b.walked) b.walked = []
    return b
  }
  function wallBucket() {
    const acc = auth.account || '__guest'
    if (!allWall.value[acc]) allWall.value[acc] = []
    return allWall.value[acc]
  }

  /* ══════════ 云端拉取 ══════════ */
  async function load() {
    if (!auth.isLogged) {
      loaded.value = true
      return
    }
    try {
      const [rRes, pRes, cRes, gRes, lRes, wRes, phRes] = await Promise.all([
        cloud.database.from('trail_reports').select('*').order('created_at', { ascending: false }).limit(100),
        cloud.database.from('safety_plans').select('*').order('created_at', { ascending: false }).limit(20),
        cloud.database.from('safety_checkins').select('*').order('created_at', { ascending: true }),
        cloud.database.from('gear_items').select('*').order('created_at', { ascending: true }),
        cloud.database.from('gear_lists').select('*').order('created_at', { ascending: false }),
        cloud.database.from('walked_routes').select('route_id, created_at').order('created_at', { ascending: false }),
        cloud.database.from('photos').select('*').order('created_at', { ascending: false }).limit(12)
      ])
      if (rRes.error) return

      reports.value = (rRes.data || []).map((r) => ({
        id: 'r' + r.id,
        account: r.owner_id || '',
        routeId: r.route_id,
        type: r.type,
        level: r.level,
        note: r.note,
        by: r.owner_name || '山友',
        at: toMs(r.created_at),
        status: r.status,
        confirm: r.confirm_count
      }))

      const ckBy = {}
      for (const c of cRes.data || []) {
        ;(ckBy[c.plan_id] ||= []).push({ at: toMs(c.created_at), type: c.type, note: c.note || '' })
      }
      const plans = (pRes.data || []).map((p) => ({
        id: 'p' + p.id,
        routeId: p.route_id,
        days: p.days,
        startDate: p.start_date,
        party: p.party || [],
        emergencyName: p.emergency_name || '',
        emergencyPhone: p.emergency_phone || '',
        note: p.note || '',
        status: p.status,
        checkins: (ckBy[p.id] || []).slice().sort((a, b) => b.at - a.at),
        createdAt: toMs(p.created_at)
      }))

      const gear = (gRes.data || []).map((g) => ({
        id: 'g' + g.id,
        name: g.name,
        cat: g.cat,
        weight: g.weight,
        count: g.count,
        owned: g.owned
      }))

      const lists = (lRes.data || []).map((l) => ({
        id: 'l' + l.id,
        name: l.name,
        routeId: l.route_id,
        routeName: l.route_name || routeNameOf(l.route_id),
        items: l.items || [],
        base: l.base,
        at: toMs(l.created_at)
      }))

      const walkedIds = (wRes.data || []).map((w) => w.route_id)

      // 个人数据整桶替换（云端为唯一事实来源）
      allUser.value = {
        ...allUser.value,
        [auth.account]: { plans, gear, lists, walked: walkedIds }
      }
      persistUser()

      // 照片：拉行 + 签名 URL
      const rows = (phRes.data || []).map((p) => ({
        id: 'w' + p.id,
        src: '',
        path: p.storage_path,
        title: p.title || '未命名照片',
        at: toMs(p.created_at)
      }))
      if (rows.length) {
        const paths = rows.map((r) => r.path)
        const signed = await cloud.storage.createSignedUrls(paths, 3600)
        if (!signed.error && Array.isArray(signed.data)) {
          for (const s of signed.data) {
            const row = rows.find((r) => r.path === s.path)
            if (row) row.src = s.signedUrl || s.url || ''
          }
        }
      }
      allWall.value = { ...allWall.value, [auth.account]: rows }
      persistWall()
      photosSigned.value = {}
      loaded.value = true
    } catch {
      /* 离线：沿用本地缓存 */
      loaded.value = true
    }
  }

  /* ══════════ 计算视图 ══════════ */
  const myPlans = computed(() => (auth.isLogged ? bucket().plans : bucket().plans))
  const myGear = computed(() => bucket().gear)
  const myLists = computed(() => bucket().lists)
  const myWalked = computed(() => bucket().walked.map((id) => routeById[id]).filter(Boolean))
  const myPhotos = computed(() => {
    if (auth.isLogged) return allWall.value[auth.account] || []
    return wallBucket()
  })

  /* ══════════ 路况 ══════════ */
  const approvedReports = computed(() =>
    reports.value.filter((r) => r.status === 'approved').sort((a, b) => b.at - a.at)
  )
  const pendingReports = computed(() => reports.value.filter((r) => r.status === 'pending'))

  function reportsFor(routeId) {
    return approvedReports.value.filter((r) => r.routeId === Number(routeId))
  }
  function reportCountOf(routeId) {
    return reports.value.filter((r) => r.routeId === Number(routeId) && r.status === 'approved').length
  }
  function worstOf(routeId) {
    const list = reportsFor(routeId)
    if (!list.length) return null
    return list.reduce((a, b) => (b.level > a.level ? b : a))
  }

  async function addReport({ routeId, type, level, note }) {
    const payload = {
      route_id: Number(routeId),
      type,
      level: Number(level) || 1,
      note: String(note || '').trim(),
      owner_name: auth.nickname
    }
    if (!auth.isLogged) {
      const r = {
        id: 'r' + now().toString(36),
        routeId: Number(routeId),
        type,
        level: Number(level) || 1,
        note: String(note || '').trim(),
        by: auth.nickname || '匿名山友',
        at: now(),
        status: 'pending',
        confirm: 0
      }
      reports.value = [r, ...reports.value]
      persistReports()
      return r
    }
    const { data, error } = await cloud.database.from('trail_reports').insert(payload).select().single()
    if (error) throw error
    const r = {
      id: 'r' + data.id,
      routeId: data.route_id,
      type: data.type,
      level: data.level,
      note: data.note,
      by: data.owner_name || auth.nickname,
      at: toMs(data.created_at),
      status: data.status,
      confirm: data.confirm_count
    }
    reports.value = [r, ...reports.value]
    return r
  }

  /** 确认（= 审核）：任何登录山友点「我也遇到」即计入，第一位确认者让它挂到路线上 */
  async function confirmReport(id) {
    const numeric = Number(String(id).replace(/^r/, ''))
    if (!auth.isLogged) return
    const { data, error } = await cloud.database.rpc('vote_report', { p_report_id: numeric })
    if (error) return
    reports.value = reports.value.map((r) =>
      r.id === id ? { ...r, status: 'approved', confirm: Number(data) || r.confirm + 1 } : r
    )
    persistReports()
  }

  /** 驳回/撤回：删除自己的待审核条目 */
  async function rejectReport(id) {
    if (!auth.isLogged) return
    const numeric = Number(String(id).replace(/^r/, ''))
    const { error } = await cloud.database.from('trail_reports').delete().eq('id', numeric)
    if (error) return
    reports.value = reports.value.filter((r) => r.id !== id)
    persistReports()
  }

  /** 兼容旧调用：演示「通过并挂载」现在等价于作者自己确认一次 */
  async function approveReport(id) {
    await confirmReport(id)
  }

  /* ══════════ 安全报备 ══════════ */
  const activePlan = computed(() => {
    const list = myPlans.value
    for (let i = list.length - 1; i >= 0; i--) {
      if (list[i].status === 'plan' || list[i].status === 'ongoing') return list[i]
    }
    return null
  })

  async function addPlan({ routeId, startDate, days, party, emergencyName, emergencyPhone, note }) {
    if (!auth.isLogged) throw new Error('登录后才能报备')
    const { data, error } = await cloud.database
      .from('safety_plans')
      .insert({
        route_id: Number(routeId),
        start_date: startDate,
        days: Number(days) || 1,
        party: (party || []).filter(Boolean),
        emergency_name: String(emergencyName || '').trim(),
        emergency_phone: String(emergencyPhone || '').trim(),
        note: String(note || '').trim(),
        owner_name: auth.nickname
      })
      .select()
      .single()
    if (error) throw error
    const p = {
      id: 'p' + data.id,
      routeId: data.route_id,
      days: data.days,
      startDate: data.start_date,
      party: data.party || [],
      emergencyName: data.emergency_name || '',
      emergencyPhone: data.emergency_phone || '',
      note: data.note || '',
      status: data.status,
      checkins: [{ at: toMs(data.created_at), type: 'go', note: '出发报备，已登记行程' }],
      createdAt: toMs(data.created_at)
    }
    bucket().plans.push(p)
    persistUser()
    await cloud.database.from('safety_checkins').insert({ plan_id: data.id, type: 'go', note: '出发报备，已登记行程' })
    return p
  }

  async function checkin(id, note, type = 'safe') {
    const numeric = Number(String(id).replace(/^p/, ''))
    if (auth.isLogged) {
      const { error } = await cloud.database.from('safety_checkins').insert({
        plan_id: numeric,
        type,
        note: String(note || '').trim() || (type === 'safe' ? '平安打卡' : '已安全下山')
      })
      if (error) return
    }
    const p = bucket().plans.find((x) => x.id === id)
    if (!p) return
    p.checkins.push({ at: now(), type, note: String(note || '').trim() || (type === 'safe' ? '平安打卡' : '已安全下山') })
    persistUser()
  }

  async function closePlan(id) {
    const numeric = Number(String(id).replace(/^p/, ''))
    if (auth.isLogged) {
      await cloud.database.from('safety_plans').update({ status: 'done' }).eq('id', numeric)
      await cloud.database.from('safety_checkins').insert({ plan_id: numeric, type: 'done', note: '已下山，报备关闭' })
    }
    const p = bucket().plans.find((x) => x.id === id)
    if (!p) return
    p.status = 'done'
    p.checkins.push({ at: now(), type: 'done', note: '已下山，报备关闭' })
    persistUser()
  }

  function planById(id) {
    return myPlans.value.find((p) => p.id === id) || null
  }

  /* ══════════ 装备库 ══════════ */
  function ensureGear() {
    const b = bucket()
    if (!b.gear.length && !auth.isLogged) {
      b.gear = SEED_GEAR.map((g, i) => ({ ...g, id: 'g' + (i + 1), owned: i < 8 }))
      persistUser()
    }
  }

  function gearWeight() {
    return myGear.value.filter((g) => g.owned).reduce((a, g) => a + g.weight * (g.count || 1), 0)
  }
  function gearByCat() {
    const out = {}
    for (const c of GEAR_CATS) out[c.k] = myGear.value.filter((g) => g.cat === c.k)
    return out
  }
  async function toggleOwned(id) {
    const g = bucket().gear.find((x) => x.id === id)
    if (!g) return
    g.owned = !g.owned
    persistUser()
    if (auth.isLogged) {
      await cloud.database.from('gear_items').update({ owned: g.owned }).eq('id', Number(String(id).replace(/^g/, '')))
    }
  }
  async function addGear({ name, cat, weight, count }) {
    const g = { id: 'g' + now().toString(36), name: String(name).trim(), cat: cat || 'other', weight: Number(weight) || 0, count: Number(count) || 1, owned: true }
    bucket().gear.push(g)
    persistUser()
    if (auth.isLogged) {
      const { data, error } = await cloud.database
        .from('gear_items')
        .insert({ name: g.name, cat: g.cat, weight: g.weight, count: g.count, owned: true })
        .select()
        .single()
      if (!error && data) g.id = 'g' + data.id
    }
    return g
  }
  async function removeGear(id) {
    const b = bucket()
    b.gear = b.gear.filter((g) => g.id !== id)
    persistUser()
    if (auth.isLogged) {
      await cloud.database.from('gear_items').delete().eq('id', Number(String(id).replace(/^g/, '')))
    }
  }

  async function saveList({ name, routeId, items, baseWeight }) {
    const l = {
      id: 'l' + now().toString(36),
      name: String(name || '未命名清单').trim(),
      routeId: Number(routeId) || 0,
      routeName: routeNameOf(routeId),
      items: (items || []).map((i) => ({ name: i.name, cat: i.cat || 'other', weight: i.weight || 0, count: 1 })),
      base: Number(baseWeight) || 0,
      at: now()
    }
    bucket().lists.unshift(l)
    persistUser()
    if (auth.isLogged) {
      const { data, error } = await cloud.database
        .from('gear_lists')
        .insert({
          name: l.name,
          route_id: l.routeId || null,
          route_name: l.routeName,
          items: l.items,
          base: l.base,
          owner_name: auth.nickname
        })
        .select()
        .single()
      if (!error && data) l.id = 'l' + data.id
    }
    return l
  }
  async function removeList(id) {
    const b = bucket()
    b.lists = b.lists.filter((l) => l.id !== id)
    persistUser()
    if (auth.isLogged) {
      await cloud.database.from('gear_lists').delete().eq('id', Number(String(id).replace(/^l/, '')))
    }
  }

  /* ══════════ 走过的路线 ══════════ */
  function isWalked(id) {
    return bucket().walked.includes(Number(id))
  }
  async function toggleWalked(id) {
    const b = bucket()
    const n = Number(id)
    const i = b.walked.indexOf(n)
    if (i >= 0) b.walked.splice(i, 1)
    else b.walked.unshift(n)
    persistUser()
    if (auth.isLogged) {
      if (i >= 0) await cloud.database.from('walked_routes').delete().match({ route_id: n })
      else await cloud.database.from('walked_routes').insert({ route_id: n })
    }
    return i < 0
  }
  const walkStats = computed(() => {
    const list = myWalked.value
    return {
      count: list.length,
      km: +list.reduce((a, r) => a + r.distance, 0).toFixed(1),
      climb: list.reduce((a, r) => a + r.climb, 0),
      days: list.reduce((a, r) => a + (r.days === '半天' ? 0.5 : r.days === '3小时' ? 0.3 : parseFloat(r.days) || 1), 0)
    }
  })

  /* ══════════ 照片墙（登录 → 云存储；游客 → 本机） ══════════ */
  async function addPhoto({ src, title }) {
    if (!auth.isLogged) {
      const list = wallBucket()
      if (list.length >= WALL_LIMIT) throw new Error(`最多存 ${WALL_LIMIT} 张，先删掉几张`)
      const item = { id: 'w' + now().toString(36), src, title: String(title || '').trim() || '未命名照片', at: now() }
      list.unshift(item)
      allWall.value = { ...allWall.value }
      try {
        persistWall()
      } catch {
        list.shift()
        allWall.value = { ...allWall.value }
        throw new Error('本机存储空间不足，删掉几张再试')
      }
      return item
    }
    // 云端：src 是压缩后的 dataURL，转 Blob 上传到 shared/<uid>/photos/
    const blob = await (await fetch(src)).blob()
    const ext = (blob.type || 'image/jpeg').includes('png') ? 'png' : 'jpg'
    const path = cloud.storage.sharedPath(auth.account, `photos/${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}.${ext}`)
    const up = await cloud.storage.upload(path, blob, { contentType: blob.type || 'image/jpeg', upsert: false })
    if (up.error) throw new Error(up.error.message || '上传失败')
    const { data, error } = await cloud.database
      .from('photos')
      .insert({ storage_path: path, title: String(title || '').trim() || '未命名照片' })
      .select()
      .single()
    if (error) throw error
    const signed = await cloud.storage.createSignedUrl(path, 3600)
    const item = {
      id: 'w' + data.id,
      src: signed?.data?.signedUrl || signed?.data?.url || src,
      path,
      title: data.title,
      at: toMs(data.created_at)
    }
    wallBucket().unshift(item)
    persistWall()
    return item
  }

  async function removePhoto(id) {
    if (auth.isLogged) {
      const numeric = Number(String(id).replace(/^w/, ''))
      const row = wallBucket().find((x) => x.id === id)
      if (row?.path) {
        await cloud.storage.remove([row.path])
        await cloud.database.from('photos').delete().eq('id', numeric)
      }
    }
    const acc = auth.account || '__guest'
    const list = wallBucket()
    const i = list.findIndex((x) => x.id === id)
    if (i < 0) return
    list.splice(i, 1)
    allWall.value = { ...allWall.value }
    persistWall()
  }

  /* ══════════ 本机 → 云端 一次性迁移 ══════════ */
  async function migrateLocalToCloud() {
    if (!auth.isLogged || localStorage.getItem(MIGRATED_KEY)) return
    const b = bucket()
    // 装备
    for (const g of b.gear) {
      await cloud.database.from('gear_items').insert({ name: g.name, cat: g.cat, weight: g.weight, count: g.count, owned: g.owned })
    }
    // 清单
    for (const l of b.lists) {
      await cloud.database.from('gear_lists').insert({ name: l.name, route_id: l.routeId || null, route_name: l.routeName, items: l.items, base: l.base, owner_name: auth.nickname })
    }
    // 走过的线
    for (const rid of b.walked) {
      await cloud.database
        .from('walked_routes')
        .upsert({ route_id: rid }, { onConflict: 'owner_id,route_id', ignoreDuplicates: true })
    }
    // 报备 + 打卡
    for (const p of b.plans) {
      const { data: plan } = await cloud.database
        .from('safety_plans')
        .insert({
          route_id: p.routeId,
          start_date: p.startDate,
          days: p.days,
          party: p.party || [],
          emergency_name: p.emergencyName || '',
          emergency_phone: p.emergencyPhone || '',
          note: p.note || '',
          status: p.status,
          owner_name: auth.nickname
        })
        .select()
        .single()
      if (plan) {
        for (const c of p.checkins || []) {
          await cloud.database.from('safety_checkins').insert({ plan_id: plan.id, type: c.type, note: c.note })
        }
      }
    }
    // 照片（base64 → 存储）
    for (const ph of wallBucket()) {
      if (!ph.src?.startsWith('data:')) continue
      try {
        await addPhoto({ src: ph.src, title: ph.title })
      } catch {
        /* 单张失败不阻塞迁移 */
      }
    }
    localStorage.setItem(MIGRATED_KEY, String(now()))
  }

  /* ══════════ 路况（登录后拉一次） ══════════ */
  async function loadReports() {
    await load()
  }

  return {
    reports,
    approvedReports,
    pendingReports,
    reportsFor,
    reportCountOf,
    worstOf,
    addReport,
    approveReport,
    rejectReport,
    confirmReport,
    load,
    loadReports,
    migrateLocalToCloud,
    myPlans,
    activePlan,
    addPlan,
    checkin,
    closePlan,
    planById,
    myGear,
    ensureGear,
    gearWeight,
    gearByCat,
    toggleOwned,
    addGear,
    removeGear,
    myLists,
    saveList,
    removeList,
    myPhotos,
    addPhoto,
    removePhoto,
    WALL_LIMIT,
    myWalked,
    isWalked,
    toggleWalked,
    walkStats
  }
})
